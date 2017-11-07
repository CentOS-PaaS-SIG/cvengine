# -*- coding: utf-8 -*-
import re
import socket
import sys
from collections import namedtuple

import paramiko
from scp import SCPClient
import diaper

import logging as log
from net import net_check

PORT_SSH = 22
# Default blocking time before giving up on an ssh command execution,
# in seconds (float)
RUNCMD_TIMEOUT = 1200.0
SSHResult = namedtuple("SSHResult", ["rc", "output"])

_client_session = []


class SSHClient(paramiko.SSHClient):

    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """

    def __init__(self, stream_output=False, **connect_kwargs):
        super(SSHClient, self).__init__()
        self._streaming = stream_output
        # deprecated/useless karg, included for backward-compat
        self._keystate = connect_kwargs.pop('keystate', None)
        # Load credentials and destination from confs, set up sane defaults
        default_connect_kwargs = {
            'username': 'root',
            'password': 'changeme',
            'timeout': 10,
            'allow_agent': False,
            'look_for_keys': True,
            'gss_auth': False
        }

        default_connect_kwargs["port"] = PORT_SSH

        # Overlay defaults with any passed-in kwargs and store
        default_connect_kwargs.update(connect_kwargs)
        self._connect_kwargs = default_connect_kwargs
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _client_session.append(self)

    def __repr__(self):
        return "<SSHClient hostname={} port={}>".format(
            repr(self._connect_kwargs.get("hostname")),
            repr(self._connect_kwargs.get("port", 22)))

    def __call__(self, **connect_kwargs):
        # Update a copy of this instance's connect kwargs with
        # passed in kwargs, then return a new instance with
        # the updated kwargs
        new_connect_kwargs = dict(self._connect_kwargs)
        new_connect_kwargs.update(connect_kwargs)
        # pass the key state if the hostname is the same, under the
        # assumption that the same host will still have keys installed
        # if they have already been
        new_client = SSHClient(**new_connect_kwargs)
        return new_client

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args, **kwargs):
        # Noop, call close explicitly to shut down the transport
        # It will be reopened automatically on next command
        pass

    def __del__(self):
        self.close()

    def _check_port(self):
        hostname = self._connect_kwargs['hostname']
        if not net_check(PORT_SSH, hostname, force=True):
            msg = 'SSH connection to {}:{} failed, port unavailable'
            raise Exception(msg.format(hostname, PORT_SSH))

    def _progress_callback(self, filename, size, sent):
        sent_percent = (sent * 100.) / size
        if sent_percent > 0:
            log.debug('{} scp progress: {:.2f}% '.format(filename,
                                                         sent_percent))

    def close(self):
        with diaper:
            _client_session.remove(self)
        super(SSHClient, self).close()

    @property
    def connected(self):
        return self._transport and self._transport.active

    def connect(self, hostname=None, **kwargs):
        """See paramiko.SSHClient.connect"""
        if hostname and hostname != self._connect_kwargs['hostname']:
            self._connect_kwargs['hostname'] = hostname
            self.close()

        if not self.connected:
            self._connect_kwargs.update(kwargs)
            self._check_port()
            # Only install ssh keys if they aren't installed (or
            # currently being installed)
            return super(SSHClient, self).connect(**self._connect_kwargs)

    def open_sftp(self, *args, **kwargs):
        self.connect()
        return super(SSHClient, self).open_sftp(*args, **kwargs)

    def get_transport(self, *args, **kwargs):
        if self.connected:
            log.debug('reusing ssh transport')
        else:
            log.debug('connecting new ssh transport')
            self.connect()
        return super(SSHClient, self).get_transport(*args, **kwargs)

    def run_command(self, command, timeout=RUNCMD_TIMEOUT):
        log.debug("Running command `{}`".format(command))
        template = '%s\n'
        command = template % command

        output = ''
        try:
            session = self.get_transport().open_session()
            if timeout:
                session.settimeout(float(timeout))
            session.exec_command(command)
            stdout = session.makefile()
            stderr = session.makefile_stderr()
            while True:
                if session.recv_ready:
                    for line in stdout:
                        output += line
                        if self._streaming:
                            sys.stdout.write(line)

                if session.recv_stderr_ready:
                    for line in stderr:
                        output += line
                        if self._streaming:
                            sys.stderr.write(line)

                if session.exit_status_ready():
                    break
            exit_status = session.recv_exit_status()
            return SSHResult(exit_status, output)
        except paramiko.SSHException as exc:
            log.error(exc)
        except socket.timeout as e:
            log.error("Command `{}` timed out.".format(command))
            log.error(e)
            msg = 'Output of the command before it failed was:\n{}'
            log.error(msg.format(output))
            raise

        # Returning two things so tuple unpacking the return works
        # even if the ssh client fails
        return SSHResult(1, None)

    def run_rails_command(self, command, timeout=RUNCMD_TIMEOUT):
        log.info("Running rails command `{}`".format(command))
        msg = 'cd /var/www/miq/vmdb; bin/rails runner {}'
        return self.run_command(msg.format(command), timeout=timeout)

    def run_rake_command(self, command, timeout=RUNCMD_TIMEOUT):
        log.info("Running rake command `{}`".format(command))
        msg = 'cd /var/www/miq/vmdb; bin/rake {}'
        return self.run_command(msg.format(command), timeout=timeout)

    def put_file(self, local_file, remote_file='.', **kwargs):
        log.info("Transferring local file {} to remote {}".format(local_file,
                                                                  remote_file))
        client = SCPClient(self.get_transport(),
                           progress=self._progress_callback)
        return client.put(local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        msg = 'Transferring remote file {} to local {}'
        log.info(msg.format(remote_file, local_path))
        client = SCPClient(self.get_transport(),
                           progress=self._progress_callback)
        return client.get(remote_file, local_path, **kwargs)

    def get_build_date(self):
        return self.get_build_datetime().date()

    def is_appliance_downstream(self):
        return self.run_command("stat /var/www/miq/vmdb/BUILD").rc == 0

    def uptime(self):
        out = self.run_command('cat /proc/uptime')[1]
        match = re.findall('\d+\.\d+', out)

        if match:
            return float(match[0])

        return 0

    def client_address(self):
        res = self.run_command('echo $SSH_CLIENT')
        # SSH_CLIENT format is 'clientip clientport serverport',
        # we want clientip
        if not res.output:
            raise Exception('unable to get client address via SSH')
        return res.output.split()[0]

    def appliance_has_netapp(self):
        return self.run_command("stat /var/www/miq/vmdb/HAS_NETAPP").rc == 0


class SSHTail(SSHClient):

    def __init__(self, remote_filename, **connect_kwargs):
        super(SSHTail, self).__init__(stream_output=False, **connect_kwargs)
        self._remote_filename = remote_filename
        self._sftp_client = None
        self._remote_file_size = None

    def __iter__(self):
        with self as sshtail:
            fstat = sshtail._sftp_client.stat(self._remote_filename)
            if self._remote_file_size is not None:
                if self._remote_file_size < fstat.st_size:
                    remote_file = self._sftp_client.open(self._remote_filename,
                                                         'r')
                    remote_file.seek(self._remote_file_size, 0)
                    while (remote_file.tell() < fstat.st_size):
                        line = remote_file.readline().rstrip()
                        yield line
            self._remote_file_size = fstat.st_size

    def __enter__(self):
        self.connect(**self._connect_kwargs)
        self._sftp_client = self.open_sftp()
        return self

    def __exit__(self, *args, **kwargs):
        self._sftp_client.close()

    def set_initial_file_end(self):
        with self as sshtail:
            fstat = sshtail._sftp_client.stat(self._remote_filename)
            self._remote_file_size = fstat.st_size  # Seed initial size of file
