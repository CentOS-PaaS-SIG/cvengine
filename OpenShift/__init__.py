import os
from distutils.spawn import find_executable
import urllib
import logging as log


OC_DOWNLOAD = ('https://github.com/openshift/origin/releases/download/v1.4.1/'
               'openshift-origin-client-tools-v1.4.1-3f9807a-linux-64bit'
               '.tar.gz')
OC_PATH = '/tmp/oc/oc'


def get_install_oc():
    """
    Finds or installs OC, the OpenShift Origin CLI client
    """
    if os.path.isfile(OC_PATH):
        oc_path = OC_PATH
    else:
        oc_path = find_executable('oc')
    if not oc_path:
        #  install oc from github
        urllib.urlretrieve(OC_DOWNLOAD, '/tmp/oc.tar.gz')
        ret = os.system('mkdir /tmp/oc; tar -xf /tmp/oc.tar.gz'
                        ' -C /tmp/oc --strip-components=1')
        if ret != 0:
            raise Exception('Failed unpacking oc!')
        oc_path = '/tmp/oc/oc'

    log.info('OpenShift oc found: ' + oc_path)
    return oc_path
