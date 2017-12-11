#! /usr/bin/env python2

import cvengine
import os
import tempfile
import requests


PLATFORM_IMAGES = {'fedora-atomic': ('https://download.fedoraproject.org'
                                     '/pub/alt/atomic/stable/Fedora-Atomic-'
                                     '27-20171110.1/CloudImages/x86_64/images/'
                                     'Fedora-Atomic-27-20171110.1.x86_64'
                                     '.qcow2')}
PLATFORM_IMAGES['atomic'] = PLATFORM_IMAGES['fedora-atomic']
PLATFORM_FAMILIES = {'atomic': ['atomic', 'fedora-atomic']}


def main():
    assert 'ANSIBLE_INVENTORY' in os.environ
    ansible_inventory = os.environ['ANSIBLE_INVENTORY']

    assert 'CV_TARGET_PLATFORM' in os.environ
    target_image = os.environ['CV_TARGET_PLATFORM']
    assert target_image in PLATFORM_IMAGES
    target_image_url = PLATFORM_IMAGES[target_image]
    target_platform = next((p for p in PLATFORM_FAMILIES if target_image
                            in PLATFORM_FAMILIES[p]),
                           None)
    assert target_platform is not None
    image_file = tempfile.NamedTemporaryFile(prefix='cvengine_image_',
                                             suffix='.qcow2',
                                             delete=False)
    image_data = requests.get(target_image_url)
    with open(image_file.name, 'w') as f:
        f.write(image_data.content)

    artifacts_dir = os.path.join(os.getcwd(), 'logs', 'cvartifacts')

    playbook_command = ('ansible-playbook -v --inventory={inv} '
                        '--extra-vars "subjects={image}" '
                        '/cvengine/ci/run_cvengine.yaml')
    playbook_command = playbook_command.format(inv=ansible_inventory,
                                               image=image_file.name)
    env_vars = {'CV_TARGET_PLATFORM': target_platform,
                'TEST_SUBJECTS': image_file.name,
                'CV_ARTIFACTS_DIRECTORY': artifacts_dir}
    cvengine.util.run.run_cmd(playbook_command,
                              env_vars=env_vars)


if __name__ == '__main__':
    main()
