from base_platform_handler import BasePlatformHandler


class AtomicHostHandler(BasePlatformHandler):
    """Platform subclass for atomic host

    This class implements support for executing a container validation
    on an Atomic Host instance. For these validations, a flavor of
    Atomic should be deployed on a remote host instance that can be
    reached via SSH from the local machine. Playbooks are executed against
    this remote host, and containers are deployed by running docker commands
    on the Atomic host.

    """
    def __init__(self, host_test, env_config_yaml,
                 artifacts, common_vars):

        super(AtomicHostHandler, self).__init__(host_test, env_config_yaml,
                                                artifacts, common_vars)

        self.extra_vars['exec_cmd'] = 'docker {0}'.format(self.EXEC_CMD_SUFFIX)
        self.fetch_artifact_cmd = 'docker cp'

        self.test_host = self.env_config['atomic-host'][0]
        self.remote_host = self.test_host['ip_address']
        credentials = self.test_host['credentials']
        user = credentials['user']
        key_path = credentials.get('ssh_key_path', None)
        password = credentials.get('password', None)
        if not key_path and not password:
            msg = 'Either a private key path or password must be given'
            raise ValueError(msg)
        self.remote_host_creds = {
            'host': self.remote_host,
            'user': user,
            'ssh_key_path': key_path,
            'password': password
        }

        self.extra_vars['current_host_ip'] = self.test_host['ip_address']
        self.extra_vars['host_machine_name'] = self.test_host['machine_name']
        self.run_playbooks_locally = False
        self.ansible_cmd = ('ANSIBLE_CONFIG={cfg} '
                            'ansible-playbook '
                            '-v -i "{inventory}" {playbook_path} '
                            '--extra-vars "{extra_vars_file}"')
