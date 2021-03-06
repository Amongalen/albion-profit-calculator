import json
from typing import Optional

from albion_calculator_backend.items_parser import ITEMS_JSON_FILE

_CRAFTING_TYPES = ['WARRIOR', 'HUNTER', 'MAGE', 'TOOLMAKER']


def get_journal_for_item(item_id: str) -> Optional[dict]:
    stripped_item_id = item_id.split('@')[0]
    return _journals_grouped_by_valid_item.get(stripped_item_id, None)


def _load_journals() -> dict[str, dict]:
    raw_journals_data = _read_journals_from_items_file()
    raw_crafting_journals_data = _filter_crafting_journals(raw_journals_data)
    journals = dict(_create_journal(journal_json) for journal_json in raw_crafting_journals_data)
    return _group_journals_by_item(journals)


def _create_journal(journal_json: dict) -> tuple[str, dict]:
    valid_items = journal_json['famefillingmissions']['craftitemfame']['validitem']
    item_id = journal_json['@uniquename']
    journal = {'max_fame': int(journal_json['@maxfame']),
               'cost': int(journal_json['craftingrequirements']['@silver']),
               'valid_items': [item['@id'] for item in valid_items],
               'item_id': item_id}
    return item_id, journal


def _filter_crafting_journals(raw_journals_data: dict) -> list[dict]:
    return [journal for journal in raw_journals_data
            if journal['@uniquename'].split('_')[2] in _CRAFTING_TYPES]


def _read_journals_from_items_file() -> dict:
    with open(ITEMS_JSON_FILE) as f:
        raw_items_data = json.load(f)
    return raw_items_data['items']['journalitem']


def _group_journals_by_item(journals_data: dict[str, dict]) -> dict[str, dict]:
    return {item_id: journal
            for journal_id, journal in journals_data.items()
            for item_id in journal['valid_items']}


_journals_grouped_by_valid_item = _load_journals()
