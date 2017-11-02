import logging
import os

from ssh import SSHClient
from scp import SCPClient


def get_file_type(ssh_connection, file_path):
    cmd = 'file {0}'.format(file_path)
    ssh_connection.connect()
    stdin, stdout, stderr = ssh_connection.exec_command(cmd)
    # Stdout will be in the following formats:
    # No such file:
    #    foo: cannot open `foo' (No such file or directory)
    #
    # File:
    #    foo: ASCII text
    #
    # Directory:
    #    foo: directory
    result = stdout.read().strip().split(':')[1].strip()
    if 'No such file or directory' in result:
        return 'DoesNotExist'
    elif result == 'directory':
        return 'Directory'
    else:
        return 'File'


def setup_ssh_connection(target_machine, target_credentials):
    tunnel = None
    ssh_creds = {'username': target_credentials['user'],
                 'password': target_credentials['password'],
                 'key_filename': target_credentials.get('private_key_path', None),
                 'look_for_keys': True,
                 'allow_agent': True,
                 'port': 22}

    ssh_connection = SSHClient(hostname=target_machine, **ssh_creds)

    return (tunnel, ssh_connection)


def fetch_remote_artifact(target_machine, target_credentials,
                          remote_file_path, artifacts_directory,
                          connect_from_host={'host': 'localhost'}):

    if not os.path.isdir(artifacts_directory):
        os.makedirs(artifacts_directory)
    target_basename = os.path.basename(remote_file_path)
    destination_path = os.path.join(artifacts_directory, target_basename)

    tunnel, ssh_connection = setup_ssh_connection(target_machine,
                                                  target_credentials)

    try:
        file_type = get_file_type(ssh_connection, remote_file_path)
        if file_type == 'DoesNotExist':
            msg = 'The specified file {0} does not exist'
            full_msg = msg.format(remote_file_path)
            logging.error(full_msg)
            raise Exception(full_msg)
        elif file_type == 'Directory':
            target_is_directory = True
        else:
            target_is_directory = False

        scp = SCPClient(ssh_connection.get_transport())
        scp.get(remote_file_path, local_path=destination_path,
                recursive=target_is_directory)
    finally:
        try:
            ssh_connection.close()
        except Exception:
            pass
        try:
            if tunnel:
                tunnel.close()
        except Exception:
            pass
