from subprocess import Popen, PIPE


def run_cmd(cmd, virtualenv=None, working_directory=None, env_vars={}):
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


def run_ansible_cmd(cmd, data, local=False, sudo=True):
    if local:
        ans = ('export ANSIBLE_HOST_KEY_CHECKING=False; '
               '/usr/bin/ansible all '
               '-v -i "{host}," -c local -m shell -a "{cmd}"')
        ans = ans.format(cmd=cmd, **data)
    else:
        ans = ('export ANSIBLE_HOST_KEY_CHECKING=False; '
               '/usr/bin/ansible all '
               '--private-key={ssh_key_path} --key-file={ssh_key_path} '
               '-v -u {user} -i "{host}," -a "{cmd}" {become}')
        ans = ans.format(cmd=cmd, become=('--become' if sudo else ''), **data)

    return run_cmd(ans)
