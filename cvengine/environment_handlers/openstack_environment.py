import base64
import random
import string
import uuid

from keystoneclient.v2_0 import client as ksclient
from neutronclient.neutron import client
from openstack import connection
from .base_environment_handler import BaseEnvironmentHandler
from cvengine.util import run


RAW_USER_DATA = ('#cloud-config\n'
                 'ssh_pwauth: True\n'
                 'disable_root: False\n'
                 'chpasswd:\n'
                 '  list: |\n'
                 '    {user}:{password}\n'
                 '  expire: False')


class OpenstackEnvironment(BaseEnvironmentHandler):
    """Environment handler for provisioning container platforms on OpenStack

    The OpenStack environment handler is used to provision a target
    container platform as a VM within an OpenStack cloud. This is used
    to create a VM from a target image then assign a floating IP to that
    VM. The IP, credentials, etc. for this VM are then used by the platform
    handler to interact with the container platform.
    """
    def __init__(self, env_config):
        """Function to initialize the environment handler

        This parses the required configuration data and generates any class
        attributes that will be used later on when preparing the environment.

        Args:
            env_config (dict): The environment configuration dictionary from
                the container validation config
        """
        assert 'openstack' in env_config
        assert 'host' in env_config
        self.osp_conf = env_config['openstack']
        self.host_conf = env_config['host']
        self.server_name = 'cvhost-{id}'.format(id=uuid.uuid4())
        self.username = 'root'
        self.password = self.generate_password()
        self.userdata = self.generate_user_data(self.username, self.password)

    def prepare(self):
        """Function to create the container platform host

        This function connects to OpenStack, creates the server, assigns a
        floating IP to it, and then waits until it can be reached via SSH.

        """
        self.osp_conn, self.neutron, self.tenant = \
            self.setup_osp_conn(self.osp_conf)
        self.host = self.create_host(self.osp_conn, self.host_conf,
                                     self.server_name, self.userdata)
        self.server_id = self.host.id
        self.fip = self.assign_ip(self.neutron, self.host_conf, self.host,
                                  self.tenant)
        ip = self.fip['floatingip']['floating_ip_address']
        self.set_required_data(self.server_name, ip, self.username,
                               self.password, None, 22)
        run.wait_for_ssh(ip, self.username, self.password)

    def teardown(self):
        """Tear down the floating IP and server

        Delete the floating IP that was attached to the server then delete
        the server
        """
        fip_id = self.fip['floatingip']['id']
        self.neutron.delete_floatingip(fip_id)
        self.osp_conn.compute.delete_server(self.server_id)

    def setup_osp_conn(self, osp_conf):
        """Function to instantiate the connection to OpenStack

        This function parses the OpenStack connection information from the
        environment confi, verifying that required keys are set. It then
        instantiates connections to openstack and neutron.

        Args:
            osp_conf (dict): The openstack configuration dictionary from
                the environment config

        Returns:
            openstack.Connection: The OpenStack connection object
            neutronclient.Client: The connection to OpenStack Neutron
            str: The keystone connection token
        """
        required_keys = ['auth_url', 'project', 'username', 'password',
                         'region']
        for key in required_keys:
            assert key in osp_conf

        auth_url = osp_conf['auth_url']
        project_name = osp_conf['project']
        username = osp_conf['username']
        password = osp_conf['password']
        region = osp_conf['region']
        conn = connection.Connection(auth_url=auth_url,
                                     project_name=project_name,
                                     username=username,
                                     password=password)
        kclient = ksclient.Client(username=username,
                                  password=password,
                                  tenant_name=project_name,
                                  auth_url=auth_url,
                                  region_name=region)
        token = kclient.auth_token
        endpoint = kclient.service_catalog.url_for(service_type='network',
                                                   endpoint_type='publicURL')
        neutron = client.Client('2.0', token=token, endpoint_url=endpoint)
        return conn, neutron, token

    def generate_password(self):
        """Function to generate a random password

        Returns:
            str: The password string
        """
        characters = string.ascii_letters + string.punctuation + string.digits
        password = ''.join(random.choice(characters) for x in
                           range(random.randint(8, 18)))
        return password

    def generate_user_data(self, user, password):
        """Function to generate the cloud-init user data string

        This generates the cloud-init user data wich is used to specify the
        root user password and allow password SSH as root.

        Returns:
            str: The base 64 encoded userdata string
        """
        raw_user_data = RAW_USER_DATA.format(user=user, password=password)
        user_data = base64.b64encode(raw_user_data)
        return user_data

    def create_host(self, osp_conn, host_conf, server_name, userdata):
        """Create the OpenStack server instance

        This creates the OpenStack instance using the target image, flavor,
        network, and keypair then waits until it has been created.

        Args:
            osp_conn (openstack.Connection): The connection to OpenStack
            host_conf (dict): The environment config dictionary with keys
                for how the host should be created.
            server_name (str): The name that should be assigned to the server
            userdata (str): The base 64 encoded user data string that will be
                passed to the cloud init system when instantiating the server

        Returns:
            openstack.Server: The openstack server object
        """

        host_keys = ['image_name', 'flavor_name', 'network_name',
                     'keypair_name']
        for key in host_keys:
            assert key in host_conf

        image = osp_conn.compute.find_image(host_conf['image_name'])
        flavor = osp_conn.compute.find_flavor(host_conf['flavor_name'])
        network = osp_conn.network.find_network(host_conf['network_name'])
        keypair = osp_conn.compute.find_keypair(host_conf['keypair_name'])

        host = osp_conn.compute.create_server(name=server_name,
                                              image_id=image.id,
                                              flavor_id=flavor.id,
                                              networks=[{"uuid": network.id}],
                                              key_name=keypair.name,
                                              user_data=userdata)
        host = osp_conn.compute.wait_for_server(host)
        return host

    def assign_ip(self, neutron, host_conf, host, tenant):
        """Assign a floating IP to the server

        This creates a (or obtains an existing but unassigned) floating IP
        then assigns it to the target host.

        Args:
            neutron (neutronclient.Client): The neutron connection object
            host_conf (dict): The environment config dictionary with keys
                for how the host should be created
            host (openstack.Server): The OpenStack server object that the
                floating IP will be attached to
            tenant (str): The OpenStack tenant ID. Used to find available
                floating IPs that are not yet assigned

        Returns:
            dict: The floating IP data
        """
        assert 'floating_ip_pool_name' in host_conf
        pool_name = host_conf['floating_ip_pool_name']
        pool_id = self.get_floating_pool_id(neutron, pool_name)
        server_port = self.get_server_port(neutron, host)
        return self.get_or_create_ip(neutron, pool_id, server_port, tenant)

    def get_floating_pool_id(self, neutron, pool_name):
        """Get the network ID of the target floating IP pool

        To create a floating IP in a pool we need to know the ID of the
        target pool. This gets that ID using the name of the target pool.

        Args:
            neutron (neutronclient.Client): The neutron connection object
            pool_name (str): The name of the target floating IP pool

        Returns:
            str: The network ID of the floating IP pool
        """
        networks = neutron.list_networks(name=pool_name)
        if not networks['networks']:
            raise Exception()
        return networks['networks'][0]['id']

    def get_server_port(self, neutron, server):
        """Get the ID of the server's network port

        To attach a floating IP to a server we need to know the ID of the
        network port on the server that the IP should be attached to. This
        gets that ID using the ID of the target server.

        Args:
            neutron (neutronclient.Client): The neutron connection object
            server (openstack.Server): The OpenStack server object that the
                floating IP will be attached to

        Returns:
            str: The ID of the server network port
        """
        ports = neutron.list_ports(device_id=server.id)
        if not ports['ports']:
            raise Exception()
        return ports['ports'][0]['id']

    def get_or_create_ip(self, neutron, floating_net, server_port, tenant):
        """Create a floating IP in the target pool or get an existing one

        This function first checks if any unassigned floating IPs exist in the
        target pool. If there is one, the first available one is returned. If
        none exist, a new floating IP is created in the target pool and
        returned.

        Args:
            neutron (neutronclient.Client): The neutron connection object
            floating_net (str): The network ID of the floating IP pool to get
                a floating IP from
            server_port (str): The ID of the server network port that the
                floating IP should be attached to
            tenant (str): The OpenStack tenant ID

        Returns:
            dict: The floating IP response data
        """

        ips = neutron.list_floatingips(floating_network_id=floating_net)
        fip = next((fip for fip in ips['floatingips'] if fip['port_id'] is
                    None and fip['tenant_id'] == tenant), None)
        if fip is None:
            fip_data = {'floatingip': {'port_id': server_port,
                                       'floating_network_id': floating_net}}
            fip = neutron.create_floatingip(fip_data)
        else:
            fip_data = {'floatingip': {'port_id': server_port}}
            fip = neutron.update_floatingip(fip['id'], fip_data)
        return fip
