# -*- mode: python; coding: utf-8 -*-

import os
import yaml

_config_dir = os.path.expanduser('~/.coincharts')
_api_key_file = os.path.join(_config_dir, 'API_KEY')
_config_file = os.path.join(_config_dir, 'config.yaml')

def get_config():
    with open(_config_file) as f:
        config = yaml.load(f)
    with open(_api_key_file) as f:
        config['api_key'] = f.read().strip()
    return config
