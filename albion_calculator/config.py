from typing import Any

import yaml


def _read_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def get_api_params():
    return {k: _to_str_if_list(v) for k, v in CONFIG['DATA_PROJECT']['PARAMS'].items()}


def _to_str_if_list(item: Any) -> str:
    return ','.join(map(str, item)) if isinstance(item, list) else item


CONFIG = _read_yaml('config.yaml')
