#! /usr/bin/env python

import json
import tempfile
import traceback

from cvengine.util.fetch import fetch_remote_artifact
from cvengine.util.run import run_ansible_cmd, run_cmd


class BasePlatformHandler(object):

    EXEC_CMD_SUFFIX = 'exec -i {0}'
    CONTAINER_ARTIFACTS_FOLDER = '/tmp/cvartifacts'

    def __init__(self, host_test, env_config_yaml,
                 artifacts, common_vars):
        self.host_test = host_test
        self.env_config = env_config_yaml
        self.playbooks = self.host_test['playbooks']
        self.instance_name = self.host_test.get('instance_name',
                                                'container_instance')
        self.artifacts = artifacts
        self.host_data_out = self.CONTAINER_ARTIFACTS_FOLDER
        self.extra_vars_file = tempfile.NamedTemporaryFile(prefix='extra_vars',
                                                           suffix='.json')

        ############################################################
        #                                                          #
        # These variables should be explicitly set in the platform #
        # handler subclasses.                                      #
        #                                                          #
        ############################################################
        self.ansible_cmd = None
        self.ansible_data = None
        self.run_playbooks_locally = None
        self.fetch_artifact_cmd = None
        ############################################################

        self.extra_vars = {
            'instance_name': self.instance_name,
            'host_data_out': self.host_data_out
        }
        self.extra_vars.update(self.host_test.get('common_vars', {}))
        self.extra_vars.update(common_vars)

    def deploy_container(self):
        raise NotImplementedError()

    def dump_extra_vars(self, extra_vars):
        with open(self.extra_vars_file.name, 'w') as f:
            json.dump(extra_vars, f)

    def run(self):
        run_ansible_cmd('mkdir {0}'.format(self.extra_vars['host_data_out']),
                        self.ansible_data, local=self.run_playbooks_locally)

        do_container_deploy = self.host_test.get('do_container_deploy', False)
        if do_container_deploy:
            self.deploy_container()

        for playbook in self.playbooks:
            print('Running playbook: ' + playbook['url'])

            playbook_extra_vars = self.extra_vars.copy()
            playbook_extra_vars.update(playbook.get('vars', {}))
            self.dump_extra_vars(playbook_extra_vars)

            try:
                path = playbook['local_path']
                ev = '@{0}'.format(self.extra_vars_file.name)
                cmd = self.ansible_cmd.format(playbook_path=path,
                                              extra_vars_file=ev,
                                              **self.ansible_data)
                run_cmd(cmd)
            except Exception:
                print('Playbook failed, stopping execution.')
                print(traceback.format_exc())
                raise

    def teardown(self, artifacts_directory):
        if self.artifacts and 'container_artifacts' in self.artifacts:
            print('Copying container artifacts to host')
            for artifact in self.artifacts['container_artifacts']:
                docker_cp = '{0} {1}:{2} {3}'.format(self.fetch_artifact_cmd,
                                                     self.instance_name,
                                                     artifact,
                                                     self.host_data_out)
                try:
                    run_ansible_cmd(docker_cp, self.ansible_data)
                except Exception:
                    pass  # Not grounds for had fail if nonexistent dir

        if not self.run_playbooks_locally:
            key = self.test_host['credentials']['ssh_key_path']
            test_host_creds = {
                'user': self.test_host['credentials']['user'],
                'private_key_path': key,
                'password': self.test_host['credentials'].get('password', None)
            }

            print('Fetching container artifacts from host')
            fetch_remote_artifact(self.test_host['ip_address'],
                                  test_host_creds,
                                  self.host_data_out,
                                  artifacts_directory)

        if self.artifacts and 'test_host_artifacts' in self.artifacts:
            for artifact in self.artifacts['test_host_artifacts']:
                try:
                    print('Fetching container artifacts from host')
                    if self.run_playbooks_locally:
                        cmd = 'cp -r {0} {1}'.format(artifact,
                                                     artifacts_directory)
                        run_ansible_cmd(cmd, self.ansible_data, local=True)
                    else:
                        fetch_remote_artifact(self.test_host['ip_address'],
                                              test_host_creds, artifact,
                                              artifacts_directory)
                except Exception:
                    pass  # Not grounds for had fail if nonexistent dir
