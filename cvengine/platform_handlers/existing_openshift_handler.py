from base_platform_handler import BasePlatformHandler
from OpenShift import get_install_oc
from OpenShift.oc import OC


class ExistingOpenshiftHandler(BasePlatformHandler):
    def __init__(self, host_test, env_config_yaml,
                 artifacts, common_vars):

        super(ExistingOpenshiftHandler, self).__init__(host_test,
                                                       env_config_yaml,
                                                       artifacts, common_vars)

        oc_path = get_install_oc()
        oc = None
        if 'openshift_instance' in host_test:
            ocp = host_test['openshift_instance']
            ocp.update({
                'oc_path': oc_path
            })
            oc = OC(**ocp)
            oc.login()
            oc.clear_resources()

        self.extra_vars['exec_cmd'] = '{0} {1}'.format(oc_path,
                                                       self.EXEC_CMD_SUFFIX)
        self.fetch_artifact_cmd = '{0} rsync'.format(oc_path)

        self.ansible_data = {
            'host': 'localhost'
        }
        self.run_playbooks_locally = True
        self.ansible_cmd = ('export ANSIBLE_HOST_KEY_CHECKING=False; '
                            'ansible-playbook '
                            '-v -i "{host}," -c local {playbook_path} '
                            '--extra-vars "{extra_vars_file}"')
