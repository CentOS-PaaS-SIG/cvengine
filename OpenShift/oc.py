import subprocess
import json
import logging as log


class OC(object):
    """
    A wrapper around 'oc' the OpenShift Origin CLI client
    """
    def __init__(self, server, token, namespace=None, oc_path='oc'):
        self.server = server
        self.token = token
        self.namespace = namespace
        self.oc_path = oc_path

        print self.login()

    def login(self):
        """
        Logs into the OpenShift server
        Should only be called by __init__
        """
        opts = [self.server, self.token]
        cmd = 'login --server {} --token={} --insecure-skip-tls-verify'
        if self.namespace:
            cmd += ' -n={}'
            opts.append(self.namespace)

        try:
            self._run_oc(cmd, opts, True)
            self._login = True
        except Exception:
            raise Exception('Login failed.')

    def _run_oc(self, cmd, opts=None, is_auth=False, output_json=False):
        """
        Wrapper for running the oc tool and returning valid dict if needed
        """
        if not is_auth and not self._login:
            raise Exception('Not currently authenticated! Please call login()')

        if opts:
            cmd = cmd.format(*opts)

        if output_json:
            cmd += " --output=json"

        cmd = self.oc_path + ' ' + cmd
        if not is_auth:
            log.info(cmd)
        proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out, err = proc.communicate()
        if proc.returncode != 0:
            msg = 'oc command failed! Please see console output for details.'
            raise Exception(msg)

        if output_json:
            return json.loads(out)

        return {}

    def project(self, name):
        """
        Sets the current OpenShift project context if not done in __init__
        """
        return self._run_oc('project ' + name)

    def add_template(self, template_name, template_path):
        """
        Add a template to your project
        """
        template = {}
        try:
            template = self._run_oc('get templates ' + template_name,
                                    output_json=True)
        except Exception:
            # exception means not found, so just create
            pass
        if 'kind' in template:
            msg = '{} exists already, deleting before recreating.'
            log.info(msg.format(template_name))
            self._run_oc('delete templates ' + template_name)

        return self._run_oc('create -f ' + template_path)

    def create_from_template(self, name, template_name):
        """
        Create a container instance from pre-existing template
        or from a template added with add_template
        """
        return self._run_oc("new-app {} --name={}".format(template_name, name),
                            output_json=False)

    def get_route(self, name):
        """
        Used by get_route_address
        """
        return self._run_oc('get routes {}'.format(name), output_json=True)

    def get_route_address(self, route_name):
        """
        Retrieve the host address for created container
        """
        route = self.get_route(route_name)
        if route:
            return route['spec']['host']
        return None

    def clear_resources(self, res_list=None):
        """
        The nuclear option. Clear out everything in the project.
        """
        all_resources = [
            'buildconfigs',
            'deploymentconfigs',
            'services',
            'routes',
            'templates',
            'imagestreams'
        ]
        if res_list is None:
            res_list = all_resources

        for res in res_list:
            self._run_oc('delete {} --all'.format(res))
