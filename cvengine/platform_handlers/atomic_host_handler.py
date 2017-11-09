from base_platform_handler import BasePlatformHandler


class AtomicHostHandler(BasePlatformHandler):
    def __init__(self, host_test, env_config_yaml,
                 artifacts, common_vars):

        super(AtomicHostHandler, self).__init__(host_test, env_config_yaml,
                                                artifacts, common_vars)

        self.extra_vars['exec_cmd'] = 'docker {0}'.format(self.EXEC_CMD_SUFFIX)
        self.fetch_artifact_cmd = 'docker cp'

        self.test_host = self.env_config['atomic-host'][0]
        host_user = self.test_host['credentials']['user']
        ssh_key_path = self.test_host['credentials']['ssh_key_path']
        self.ansible_data = {
            'host': self.test_host['ip_address'],
            'user': host_user,
            'ssh_key_path': ssh_key_path
        }
        self.extra_vars['current_host_ip'] = self.test_host['ip_address']
        self.extra_vars['host_machine_name'] = self.test_host['machine_name']
        self.run_playbooks_locally = False
        self.ansible_cmd = ('export ANSIBLE_HOST_KEY_CHECKING=False; '
                            'ansible-playbook '
                            '--private-key={ssh_key_path}, '
                            '--key-file={ssh_key_path} '
                            '-v -u {user} -i "{host}," {playbook_path} '
                            '--extra-vars "{extra_vars_file}"')
