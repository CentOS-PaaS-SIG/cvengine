#! /usr/bin/env python2

from setuptools import find_packages, setup

setup(name='cvengine',
      version='1.1',
      description='Red Hat container validation engine',
      author='Alex Corvin',
      author_email='acorvin@redhat.com',
      packages=find_packages(),
      entry_points={
          'console_scripts': ['cvengine=cvengine.cvengine:main']
      },
      install_requires=['paramiko',
                        'scp',
                        'diaper',
                        'pyyaml',
                        'ansible',
                        'python-openstackclient',
                        'python-neutronclient'])
