from subprocess import Popen, PIPE


def run_cmd(cmd, virtualenv=None, working_directory=None, env_vars={}):
    """Helper function for running a local bash command

    Execute the speficied command locally in a shell. Supports setting
    environment variables, a working directory, and a python virtual
    environment for the command to be run within.

    Args:
        cmd (str): The command to be executed
        virtualenv (str, optional): Path to a python virtual environment.
            If specified, the virtual environment will be activated prior
            to running the command.
        working_directory (str, optional): Path to a directory within which
            the command fill be executed.
        env_vars (dict, optional): A set of environment variables to be set
            prior to executing the command.

    Raises:
        Exception: Raises a generic exception if the command fails.

    """
    if virtualenv:
        cmd = ('source %s/bin/activate; ' % virtualenv) + cmd
    if len(env_vars) > 0:
        for key, val in env_vars.iteritems():
            cmd = '{0}={1} '.format(key, val) + cmd
    print 'Running: {}'.format(cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, cwd=working_directory)
    res = []
    while True:
        output = p.stdout.readline()
        if output == '' and p.poll() is not None:
            break
        if output:
            print output.strip()
            res.append(output.strip())
    rc = p.poll()
    if rc != 0:
        print('Non-success return code: ' + str(rc))
        raise Exception()
    return res


def run_ansible_cmd(cmd, inventory, ansible_config,
                    module='command', local=False, sudo=True):
    """Helper function to run an ansible command

    Execute the specified command in a local shell via ansible. This is used
    primarily to execute a command on a remote host, using the ssh mechanisms
    provided by Ansible.

    Args:
        cmd (str): The command to be executed
        inventory (str): A representation of the ansible inventory. This is
            any string that can be passed as the value of the --inventory
            argument to the ansible command. In practice, this will usually
            be a path to an ansible inventory file. Additionally, it could be
            the string "localhost", or an IP address
        ansible_config (str): A path to an ansible config file
        module (str, optional): The ansible module to use. This is passed to
            the ansible command as the value of the '-m' argument. Defaults
            to 'command'.
        local (bool, optional): Whether the command should be executed against
            the local machine. If false, we assume that the target of the
            ansible command is a remote host. Defaults to False.
        sudo (bool, optional): Whether to execute a command against the host
            with escalated privileges. Defaults to True.

    """
    if local:
        ans = ('ANSIBLE_CONFIG={cfg} '
               'ansible all '
               '-v -i "{inventory}" -c local -m {mod} -a "{cmd}"')
        ans = ans.format(cfg=ansible_config, inventory=inventory,
                         cmd=cmd, mod=module)
    else:
        ans = ('ANSIBLE_CONFIG={cfg} '
               'ansible all '
               '-v -i "{inventory}" {become} -m {mod} -a "{cmd}"')
        ans = ans.format(cfg=ansible_config, cmd=cmd,
                         mod=module,
                         inventory=inventory,
                         become=('--become' if sudo else ''))

    return run_cmd(ans)
