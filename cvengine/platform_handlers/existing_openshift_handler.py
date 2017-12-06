from base_platform_handler import BasePlatformHandler
from OpenShift import get_install_oc
from OpenShift.oc import OC


class ExistingOpenshiftHandler(BasePlatformHandler):
    """Platform subclass for existing OpenShift instances

    This class implements support for executing a container validation
    on an OpenShift instance that has already been deployed (as opposed to
    the CVEngine deploying the instance for you). For these validations,
    an OpenShift instance should already exist (the configuration for which
    will be passed to the platform handler). The local machine should have
    network access to the OpenShift instance and be able to execute "oc"
    commands against it. Playbooks are executed locally, against the local
    machine, and containers are deployed and interacted with by running
    "oc" commands.

    Todo:
        * This platform is untested and not currently supported. Add
          official support for this.

    """
    def __init__(self, host_test, environment,
                 artifacts, common_vars):

        super(ExistingOpenshiftHandler, self).__init__(host_test,
                                                       environment,
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
