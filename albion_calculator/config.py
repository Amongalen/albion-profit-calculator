from typing import Any

import yaml


def read_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def get_api_params():
    return {k: to_str_if_list(v) for k, v in CONFIG['DATA_PROJECT']['PARAMS'].items()}


def to_str_if_list(item: Any) -> str:
    return ','.join(map(str, item)) if isinstance(item, list) else item


CONFIG = read_yaml('config.yaml')
