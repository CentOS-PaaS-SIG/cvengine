class BaseEnvironmentHandler(object):
    """Base class for interacting with environments

    Environments in cvengine encapsulate the host(s) that a container platform
    gets deployed on. These could be a single host that is connected to via
    SSH, a cloud platform that hosts get provisioned on, etc. This base class
    provides the common interfact definition for specific environment
    implementations.

    Attributes:
        host_name (str): The name of the container platform host
        host_ip (str): The IP address to the container platform host
        username (str): The username for connecting to the container platform
            host
        password (str): The password for connecting to the container platform
            host
        ssh_key_path (str): A path to the private key to be used for connecting
            to the container platform host
        port (int): The port number to be used to ssh to the container platform
            host
    """
    def __init__(self):
        pass

    def prepare(self):
        """Function to set up the environment before the run

        Any steps required to create the environment or container platform
        hosts should be performed in the prepare function. This will be
        executed prior to instantiating and running the platform handler.

        """
        pass

    def set_required_data(self, name, ip, username, password, ssh_key_path,
                          port):
        """Function for setting the required class attributes

        This function sets up the required class attributes that will be used
        by the platform handlers to connect to the container platform host.
        Using this function to set the attributes rather than having them
        set individually in the implementing classes makes it easier to see
        what class attributes are required.

        Args:
            name (str): The name of the container platform host
            ip (str): The IP address to the container platform host
            username (str): The username for connecting to the container
                platform host
            password (str): The password for connecting to the container
                platform host
            ssh_key_path (str): A path to the private key to be used for
                connecting to the container platform host
            port (int): The port number to be used to ssh to the container
                platform host
        """
        self.host_name = name
        self.host_ip = ip
        self.username = username
        self.password = password
        self.ssh_key_path = ssh_key_path
        self.port = port

    def teardown(self):
        """Function to tear down the environment after the run

        Any environment teardown steps (deleting VMs, etc.) should be
        performed in the teardown function. This will be called after
        the container validation completes and after the platform teardown
        is called. This function will be called regardless of whether the
        container validation executes successfully.
        """
        pass
