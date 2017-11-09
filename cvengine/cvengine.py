#! /usr/bin/env python2


import os
import ssl
import traceback
import urllib
import urllib2
import urlparse
import yaml

from .util import run
from .platform_handlers.atomic_host_handler import AtomicHostHandler


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
        if ((host['host_type'] == target_host_platform) or
                (not target_host_platform and host['default'])):
            host_test = host
            break

    if not host_test:
        msg = 'Given host_type matched none in CHIData or no default provided.'
        raise ValueError(msg)

    # pre-download playbook files
    playbooks = host_test['playbooks']
    for pb in playbooks:
        url = pb['url']
        base_name = os.path.basename(urlparse.urlsplit(url).path)
        new_path = os.path.join('/tmp', base_name)
        try:
            urllib.urlretrieve(url, new_path)
        except Exception:
            msg = 'Error when downloading playbook {0}: {1}'
            msg = msg.format(url, traceback.format_exc())
            raise Exception(msg)
        pb['local_path'] = new_path

    if host_test['host_type'] not in host_type_handlers:
        msg = '{} is not a valid host_type'.format(host_test['host_type'])
        raise ValueError(msg)

    run.run_cmd('ansible-playbook --version')
    run.run_cmd('ansible --version')

    artifacts = chidata.get('Artifacts')
    extra_variables['image_url'] = image_url

    environment_config = config['environment']

    handler_class = host_type_handlers[host_test['host_type']]
    handler = handler_class(host_test, environment_config,
                            artifacts, extra_variables)
    try:
        handler.run()
    except Exception:
        msg = 'Error encountered while running handler: {0}'
        print(msg.format(traceback.format_exc()))
        raise
    finally:
        handler.teardown(artifacts_directory)


def main():
    image_url = os.environ['CV_IMAGE_URL']
    cvdata_url = os.environ['CV_CVDATA_URL']
    cv_config = yaml.load(os.environ['CV_CONFIG'])
    artifacts_directory = os.environ['CV_ARTIFACTS_DIRECTORY']
    extra_vars = yaml.load(os.environ.get('CV_EXTRA_VARS', '{}'))

    run_container_validation(image_url, cvdata_url, cv_config,
                             artifacts_directory, extra_vars)


if __name__ == '__main__':
    main()
