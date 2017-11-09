import logging
import os

from ssh import SSHClient
from scp import SCPClient


def get_file_type(ssh_connection, file_path):
    """Function to determine if a remote file is a flat file or directory

    Executes a "file" command in a shell against the target file path
    then parses the output to determine the file type. This is intended to
    be run against a remote machine to facilitate fetching artifacts from
    a remote host.

    Args:
        ssh_connection (:obj: `SSHClient`): Preconfigured ssh connection
            wrapper to the target machine
        file_path (str): Path to the remote file or directory

    Returns:
        str: The type of the remote file.
            The value will be "DoesNotExist" if the specified path does not
            exist, "Directory" if it is a directory, or "File" if it is a
            flat file.

    """
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
    """Helper function to instantiate a ssh connection to a remote host

    Instantiates a wrapper around an SSH connection to a remote host. A
    connection is not created at this point, but the credentials, IP, etc.
    are all defined.

    Args:
        target_machine (str): The hostname or IP address of the target host
        target_credentials (dict): Credentials (username, password, private
            key path) for the remote host

    Todo:
        * Remote the unused tunnel return item
        * Refactor to use official SSHclient class, not our custom one

    Returns:
        tuple: A tuple containing a tunnel object (unused) and an SSHClient
            object wrapping the ssh connection

    """
    tunnel = None
    ssh_creds = {'username': target_credentials['user'],
                 'password': target_credentials['password'],
                 'key_filename': target_credentials.get('private_key_path',
                                                        None),
                 'look_for_keys': True,
                 'allow_agent': True,
                 'port': 22}

    ssh_connection = SSHClient(hostname=target_machine, **ssh_creds)

    return (tunnel, ssh_connection)


def fetch_remote_artifact(target_machine, target_credentials,
                          remote_file_path, artifacts_directory,
                          connect_from_host={'host': 'localhost'}):
    """Fetch an artifact from a remote machine

    Heler function to facilitate fetching the file or directory at a
    specific path from a remote machine using scp

    Args:
        target_machine (str): The IP address or hostname of the remote machine
        target_credentials (dict): Credentials (username, password, private
            key path) for the remote host
        remote_file_path (str): The path to the file/directory to be retrieved
            from the remote machine
        artifacts_directory (str): The local path that the fetched artifact
            should be written to
        connect_from_host (dict, optional): Unused

    Todo:
        * Remote the unused connect_from_host argument

    Raises:
        Exception: A generic exception if the target artifact does not exist
            on the remote host

    """

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
