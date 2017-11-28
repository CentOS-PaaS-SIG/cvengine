from atomic_host_handler import AtomicHostHandler
from cvengine.util.run import run_ansible_cmd


class FedoraHandler(AtomicHostHandler):
    """Platform handler for Fedora hosts

    This class is used to execute container validations against traditional
    Fedora hosts and similar. Specifically, this is used for a host that
    needs to be bootstrapped with docker installed and running. Once
    that condition is met, the container validation is the same as for an
    Atomic Host, so this class subclassed the AtomicHostHandler.
    """

    def setup(self):
        """Setup function for Fedora hosts

        This function performs the necessary steps to bootstrap the remote
        Fedora host to run containers. Specifically, we install python2
        (necessary to be able to run more ansible commands against the host,
        then install, enable, and start Docker.
        """
        super(AtomicHostHandler, self).setup()

        # Bootstrap the node to ensure python2 is installed
        run_ansible_cmd('dnf -y install python2',
                        self.ansible_inv,
                        self.ansible_config_file,
                        module='raw')

        commands = ['dnf -y install docker',
                    'systemctl enable docker',
                    'systemctl start docker']
        for command in commands:
            run_ansible_cmd(command,
                            self.ansible_inv,
                            self.ansible_config_file)
