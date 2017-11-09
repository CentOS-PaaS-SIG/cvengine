#! /usr/bin/env python2

import os
import unittest
import yaml

from .context import cvengine


TEST_CONFIG_FILE = 'test_config.yml'
ARTIFACTS_DIR_NAME = 'test_artifacts'


def parse_config():
    file_path = os.path.realpath(__file__)
    directory = os.path.dirname(file_path)
    config_file = os.path.join(directory, TEST_CONFIG_FILE)
    with open(config_file) as f:
        config = yaml.safe_load(f)

    artifacts_dir = os.path.join(directory, ARTIFACTS_DIR_NAME)
    print(config)
    print(config['test'])
    config['test']['artifacts_dir'] = artifacts_dir

    return config


class SmokeTest(unittest.TestCase):
    def test_basic(self):
        config = parse_config()
        test_config = config['test']
        image_url = test_config['image_url'].strip()
        cvdata_url = test_config['cvdata_url'].strip()
        artifacts_dir = test_config['artifacts_dir']
        extra_vars = {}

        cv_config = {}
        cv_config['target_host_platform'] = test_config['target_host_platform']
        cv_config['environment'] = config['environment']

        cvengine.run_container_validation(image_url, cvdata_url, cv_config,
                                          artifacts_dir, extra_vars)
        assert True


if __name__ == '__main__':
    unittest.main()
