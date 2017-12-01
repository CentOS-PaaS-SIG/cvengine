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
    def __init__(self, host_test, environment,
                 artifacts, common_vars):

        super(AtomicHostHandler, self).__init__(host_test, environment,
                                                artifacts, common_vars)

        self.extra_vars['exec_cmd'] = 'docker {0}'.format(self.EXEC_CMD_SUFFIX)
        self.fetch_artifact_cmd = 'docker cp'

        self.remote_host = environment.host_ip
        user = environment.username
        key_path = environment.ssh_key_path
        password = environment.password
        port = environment.port
        if not key_path and not password:
            msg = 'Either a private key path or password must be given'
            raise ValueError(msg)
        self.remote_host_creds = {
            'host': self.remote_host,
            'user': user,
            'ssh_key_path': key_path,
            'password': password,
            'port': port
        }

        self.extra_vars['current_host_ip'] = self.remote_host
        self.extra_vars['host_machine_name'] = environment.host_name
        self.run_playbooks_locally = False
        self.ansible_cmd = ('ANSIBLE_CONFIG={cfg} '
                            'ansible-playbook '
                            '-i "{inventory}" {playbook_path} '
                            '--extra-vars "{extra_vars_file}"')
