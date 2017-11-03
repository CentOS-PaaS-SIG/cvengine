#! /usr/bin/env python

import os
import ssl
import urllib
import urllib2
import urlparse
import yaml

from util.run import run_cmd
from platform_handlers.atomic_host_handler import AtomicHostHandler


host_type_handlers = {
    'dashost': AtomicHostHandler,
    'atomic': AtomicHostHandler
}


def run_container_validation(image_url, chidata_url, config,
                             artifacts_directory, extra_variables):
    print('Downloading {0}'.format(chidata_url))
    context = ssl._create_unverified_context()
    chidata = urllib2.urlopen(chidata_url, context=context).read()
    chidata = yaml.load(chidata)

    print("CHIData Contents:")
    print(chidata)

    target_host_platform = config['target_host_platform']
    host_test = None
    for host in chidata['Test']:
        if (host['host_type'] == target_host_platform) or (not target_host_platform and host['default']):
            host_test = host
            break

    if not host_test:
        raise ValueError('Given host_type matched none in CHIData or no default provided.')

    # pre-download playbook files
    playbooks = host_test['playbooks']
    for pb in playbooks:
        url = pb['url']
        base_name = os.path.basename(urlparse.urlsplit(url).path)
        new_path = os.path.join('/tmp', base_name)
        urllib.urlretrieve(url, new_path)
        pb['local_path'] = new_path

    if host_test['host_type'] not in host_type_handlers:
        raise ValueError('{} is not a valid host_type'.format(host_test['host_type']))

    run_cmd('ansible-playbook --version')
    run_cmd('ansible --version')

    artifacts = chidata.get('Artifacts')
    extra_variables['image_url'] = image_url

    environment_config = config['environment']

    handler_class = host_type_handlers[host_test['host_type']]
    handler = handler_class(host_test, environment_config,
                            artifacts, extra_variables)
    try:
        handler.run()
    finally:
        handler.teardown(artifacts_directory)
