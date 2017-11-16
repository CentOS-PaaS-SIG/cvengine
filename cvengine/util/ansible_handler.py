import tempfile


def write_ansible_inventory(host, user, ssh_key_path=None,
                            password=None, port=None):
    """Write an ansible inventory file

    Creates a file on disk to be used as an ansible inventory file for a
    single host. Note that at least one of the password or ssh_key_path must
    be specified.

    Args:
        host (str): The hostname or IP address of the target host
        user (str): The username that should be used to connect to the
            target host
        ssh_key_path (str, optional): A path to the private key to be used
            to connect to the target host
        password (str, optional): The password to be used to connect to the
            target host

    Raises:
        ValueError: If neither the password nor ssh_key_path arguments
            are specified

    Returns:
        str: The path to the inventory file

    """
    inventory_file = tempfile.NamedTemporaryFile(prefix='ansible_inventory_',
                                                 delete=False)
    contents = ('{host}'
                '\n\n[all:vars]'
                '\nansible_connection=ssh'
                '\nansible_ssh_user={user}')
    contents = contents.format(host=host, user=user)

    if password is None and ssh_key_path is None:
        msg = 'You must specify either the password or ssh_key_path'
        raise ValueError(msg)

    if password:
        contents += '\nansible_ssh_pass={0}'.format(password)

    if ssh_key_path:
        key_line = '\n ansible_ssh_private_key_file={0}'
        contents += key_line.format(ssh_key_path)

    if port:
        contents += '\nansible_ssh_port={0}'.format(port)

    with open(inventory_file.name, 'w') as f:
        f.write(contents)

    return inventory_file.name


def write_ansible_config(options={}):
    """Writes an ansible config file

    Creates a file on disk to be used as an ansible configuration file.
    This config disables ansible host key checking and forces ANSI color
    output on the terminal. It additionally enables any options that
    are passed in. Currently, this only supports setting additional options
    under the [defaults] section of the ansible config.

    Args:
        options (dict, optional): A set of options to be passed in

    Todo:
        * Add support for specifying ansible options under additional
          sections of the config

    Returns:
        str: The path to the config file

    """
    default_options = {'host_key_checking': 'False',
                       'force_color': '1'}
    default_options.update(options)
    config_file = tempfile.NamedTemporaryFile(prefix='ansible_config_',
                                              suffix='.cfg',
                                              delete=False)
    config_data = '[defaults]'
    for key, val in default_options.items():
        config_data += '\n{0} = {1}'.format(key, val)

    with open(config_file.name, 'w') as f:
        f.write(config_data)

    return config_file.name
