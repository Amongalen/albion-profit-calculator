from typing import Any, Union, Hashable

import yaml


def get_api_params() -> dict[str, any]:
    return {k: _to_str_if_list(v) for k, v in CONFIG['DATA_PROJECT']['PARAMS'].items()}


def _read_yaml(file_path: str) -> Union[dict[Hashable, Any], list, None]:
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def _to_str_if_list(item: Any) -> Any:
    return ','.join(map(str, item)) if isinstance(item, list) else item


CONFIG = _read_yaml('config.yaml')
