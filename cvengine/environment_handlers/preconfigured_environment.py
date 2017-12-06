from .base_environment_handler import BaseEnvironmentHandler


class PreConfiguredEnvironment(BaseEnvironmentHandler):
    """Environment handler for hosts that have already been provisioned

    PreConfigured environments are those where the container platform already
    exists when cvengine is called. Some process (either a human manually or
    the process which calls cvengine) has already set up the container
    platform and passed in the IP address, credentials, etc for the
    environment in the environment section of the config.

    Todo:
        * This environment handler expects the config information about the
          environment host to be under a sub-key named "atomic-host" within
          the environment config section. This should be more modified to
          be more generic. Doing so will require updating implementations
          of cvengine to change the key they use to publish
    """
    def __init__(self, env_config):
        """Function to initialize the environment handler

        This parses the required configuration data and sets the necessary
        class attributes.

        Args:
            env_config (dict): The environment configuration dictionary from
                the container validation config
        """
        assert 'atomic-host' in env_config
        host = env_config['atomic-host'][0]

        keys = ['machine_name', 'ip_address', 'credentials']
        for key in keys:
            assert key in host

        server_name = host['machine_name']
        ip = host['ip_address']
        credentials = host['credentials']
        username = credentials['user']
        password = credentials.get('password', None)
        ssh_key = credentials.get('ssh_key_path', None)
        port = credentials.get('port', 22)
        self.set_required_data(server_name, ip, username,
                               password, ssh_key, port)
