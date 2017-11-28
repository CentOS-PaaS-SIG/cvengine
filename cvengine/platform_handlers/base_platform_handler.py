import json
import tempfile
import traceback

from cvengine.util.ansible_handler import write_ansible_config, \
        write_ansible_inventory
from cvengine.util.fetch import fetch_remote_artifact
from cvengine.util.run import run_ansible_cmd, run_cmd


class BasePlatformHandler(object):
    """Base class for running container validations on the target platform

    "Platforms" are the representation in cvengine of the hosts/systems that
    containers run on, e.g. Docker or Openshift. This base class is used
    to store common code that is shared by all platforms. Subclasses exist
    for each target platform. This base class enumerates the variables that
    should be defined for a given platform, and also contains the functions
    to run a container valiation and teardown afterwards.

    Attributes:
        EXEC_CMD_SUFFIX (str): The suffix of commands used to execute a
            command against a running container. The prefix should be set by
            a platform handler subclass.

    """

    EXEC_CMD_SUFFIX = 'exec -i {0}'

    def __init__(self, host_test, env_config_yaml,
                 artifacts, common_vars):
        """
        Args:
            host_test (dict): Dictionary containing information about the
                currently running scenario. Includes the playbooks to be
                executed, instance name, and playbook variables
            env_config_yaml (dict): Dictionary containing information about
                the target environment. Environments are the representation
                in cvengine of the hosts/systems on which a platform gets
                deployed (or already is deployed). Specific subkeys depend on
                the specific environment type that the validation is being run
                against.
            artifacts (dict): Dictionary containing sets of artifacts to be
                retrieved after running the validation.
            common_vars (dict): Dictionary containing a set of variables to be
                passed to all playbooks using the --extra-vars flag. These
                variables will be overriden by any variables defined in the
                metadata file.

        Todo:
            * Once environment handlers are implemented, the way environment
              data is passed into the platform handlers will change
            * Once the cvdata class is implemented, all of host_test should be
              encapsulated within an object that gets passed to a platform
              handler.
        """
        self.host_test = host_test
        self.env_config = env_config_yaml
        self.playbooks = self.host_test['playbooks']
        self.instance_name = self.host_test.get('instance_name',
                                                'container_instance')
        self.artifacts = artifacts
        # Generate a random directory name to store artifacts on the container
        # This directory will be passed to the playbooks, so in cases like
        # atomic host, the directory will be written to on the remote host,
        # as opposed to the local host from which the python code is running.
        # We specify the /tmp dir so that we have a valid directory. This
        # ensures that the cvengine code can run on platforms for which
        # /tmp is not the default tempfile location.
        self.host_data_out = tempfile.mkdtemp(prefix='cvartifacts_',
                                              dir='/tmp')
        self.extra_vars_file = tempfile.NamedTemporaryFile(prefix='extra_vars',
                                                           suffix='.json')
        self.ansible_config_file = write_ansible_config()

        ############################################################
        #                                                          #
        # These variables should be explicitly set in the platform #
        # handler subclasses.                                      #
        #                                                          #
        ############################################################
        self.ansible_cmd = None
        self.run_playbooks_locally = None
        self.fetch_artifact_cmd = None
        self.remote_host = None
        self.remote_host_creds = None
        self.ansible_inv = None
        ############################################################

        self.extra_vars = {
            'instance_name': self.instance_name,
            'host_data_out': self.host_data_out
        }
        self.extra_vars.update(self.host_test.get('common_vars', {}))
        self.extra_vars.update(common_vars)

    def deploy_container(self):
        """Deploy the container onto the target platform

        This function is used for simple containers that can be deployed
        without custom settings onto the target container platform. This
        functionality is not currently supported.

        Raises:
            NotImplementedError: Always. This functionality is not currently
                supported.

        """
        raise NotImplementedError()

    def dump_extra_vars(self, extra_vars):
        """Write the extra variables to a file

        Helper function to write playbook variables to a file on disk. The
        path to this file is sent to each playbook using the --extra-vars
        argument. This file is updated/overwritten for each playbook that
        gets executed.

        Args:
            extra_vars (dict): Dictionary containing variables to be written
                to the file.

        """
        with open(self.extra_vars_file.name, 'w') as f:
            json.dump(extra_vars, f)

    def setup(self):
        """Base setup function for platform handlers

        The setup function will be called before the run function. This
        is intended to be used when some level of setup/initialization
        is necessary to prepare the container platform. Not all platforms
        will make use of this.
        """
        if self.run_playbooks_locally:
            self.ansible_inv = 'localhost, '
        else:
            creds_data = self.remote_host_creds
            self.ansible_inv = write_ansible_inventory(**creds_data)

    def run(self):
        """Execute the container validation on the target platform

        This function sets up the artifacts directory for the target platform,
        either locally or on a remote machine (depending on the platform). It
        then deploys the container (if applicable), and finally executes the
        playbooks enumerated in the metadata file (passing in any applicable
        variables)

        Raises:
            Exception: A generic exception if any of the playbooks fail

        """
        run_ansible_cmd('mkdir {0}'.format(self.extra_vars['host_data_out']),
                        self.ansible_inv,
                        self.ansible_config_file,
                        local=self.run_playbooks_locally)

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
                cmd = self.ansible_cmd.format(cfg=self.ansible_config_file,
                                              inventory=self.ansible_inv,
                                              playbook_path=path,
                                              extra_vars_file=ev)
                run_cmd(cmd)
            except Exception:
                print('Playbook failed, stopping execution.')
                print(traceback.format_exc())
                raise

    def teardown(self, artifacts_directory):
        """Perform cleanup and teardown steps

        The primary role of this function is to fetch artifacts produced
        by the container validation run. Artifacts are first fetched from
        the remote container platform (if applicable), then all artifacts
        from the local machine are transferred to the target artifacts
        directory.

        Args:
            artifacts_directory (str): Location on the local machine that
                artifacts should be written to.

        """
        if self.artifacts and 'container_artifacts' in self.artifacts:
            print('Copying container artifacts to host')
            for artifact in self.artifacts['container_artifacts']:
                docker_cp = '{0} {1}:{2} {3}'.format(self.fetch_artifact_cmd,
                                                     self.instance_name,
                                                     artifact,
                                                     self.host_data_out)
                try:
                    run_ansible_cmd(docker_cp,
                                    self.ansible_inv, self.ansible_config_file)
                except Exception:
                    pass  # Not grounds for had fail if nonexistent dir

            print('Fetching container artifacts from host')
            try:
                port = self.remote_host_creds['port']
                fetch_remote_artifact(self.remote_host,
                                      self.remote_host_creds,
                                      self.host_data_out,
                                      artifacts_directory,
                                      target_port=port)
            except Exception:
                print traceback.format_exc()
                raise

        if self.artifacts and 'test_host_artifacts' in self.artifacts:
            for artifact in self.artifacts['test_host_artifacts']:
                try:
                    print('Fetching container artifacts from host')
                    if self.run_playbooks_locally:
                        cmd = 'cp -r {0} {1}'.format(artifact,
                                                     artifacts_directory)
                        run_ansible_cmd(cmd, local=True)
                    else:
                        port = self.remote_host_creds['port']
                        fetch_remote_artifact(self.remote_host,
                                              self.remote_host_creds, artifact,
                                              artifacts_directory,
                                              target_port=port)
                except Exception:
                    pass  # Not grounds for had fail if nonexistent dir
