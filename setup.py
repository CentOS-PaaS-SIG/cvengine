#! /usr/bin/env python

from setuptools import setup

setup(name='cvengine',
      version='1.1',
      description='Red Hat container validation engine',
      author='Alex Corvin',
      author_email='acorvin@redhat.com',
      packages=['cvengine'],
      install_requires=['paramiko',
                        'scp',
                        'diaper',
                        'pyyaml',
                        'ansible'])
