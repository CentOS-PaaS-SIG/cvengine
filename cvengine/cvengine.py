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
    """Runs a container validation against the target container image

    This is the main worker function of the cvengine. It takes the parameters
    for the container validation scenario, fetches the metadata file
    and playbooks, parses all config, orchestrates setup of the target
    environment, and finally executes the validation against the target
    container platform.

    Args:
        image_url (str): Location of the container image. In most cases,
            this should be a string that can be passed to the "docker pull"
            command. Alternatively, this could be a full URL to a file that
            gets fetched by the test playbooks and then loaded in docker.
            The latter method is not handled by the cvengine and is left to
            the playbooks to implement.
        chidata_url (str): Location of the metadata file. This file will be
            fetched and parsed to get information about the current scenario
            (target platform, playbook locations, platform customizations,
            etc.)
        config (dict): Configuration info for the target platform and
            environment. At a minimum, keys must exist for
            "target_host_platform" and "environment". Further keys and subkeys
            depend on the chosen environment.
        artifacts_directory (str): The path to a directory where test
            artifacts will be written to. The cvengine will copy all artifacts
            to this location on the machine where the function is executed.
        extra_variables (dict): Any extra variables that should be passed to
            the playbooks. These will be passed to ALL playbooks using the
            --extra-vars argument. NOTE: These variables will be overriden by
            any variables defined in the metadata file.

    """
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
    """Main entry point into container validation

    This function is created as a script entry point in the $PATH when
    installing the package. It expects the required parameters to be set
    as environment variables. This function parses the environment variables
    and passes them as arguments to the run_container_validation function.
    """
    image_url = os.environ['CV_IMAGE_URL']
    cvdata_url = os.environ['CV_CVDATA_URL']
    cv_config = yaml.load(os.environ['CV_CONFIG'])
    artifacts_directory = os.environ['CV_ARTIFACTS_DIRECTORY']
    extra_vars = yaml.load(os.environ.get('CV_EXTRA_VARS', '{}'))

    run_container_validation(image_url, cvdata_url, cv_config,
                             artifacts_directory, extra_vars)


if __name__ == '__main__':
    main()
