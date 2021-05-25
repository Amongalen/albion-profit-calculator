import json

from albion_calculator.items import ITEMS_JSON_FILE

CRAFTING_TYPES = ['WARRIOR', 'HUNTER', 'MAGE', 'TOOLMAKER']


def get_journal_for_item(item_id):
    return _journals_grouped_by_valid_item.get(item_id, None)


def load_journals():
    raw_journals_data = read_journals_from_items_file()
    raw_crafting_journals_data = filter_crafting_journals(raw_journals_data)
    journals = dict(create_journal(journal_json) for journal_json in raw_crafting_journals_data)
    return group_journals_by_item(journals)


def create_journal(journal_json):
    valid_items = journal_json['famefillingmissions']['craftitemfame']['validitem']
    item_id = journal_json['@uniquename']
    journal = {'max_fame': int(journal_json['@maxfame']),
               'cost': int(journal_json['craftingrequirements']['@silver']),
               'valid_items': [item['@id'] for item in valid_items],
               'item_id': item_id}
    return item_id, journal


def filter_crafting_journals(raw_journals_data):
    return [journal for journal in raw_journals_data
            if journal['@uniquename'].split('_')[2] in CRAFTING_TYPES]


def read_journals_from_items_file():
    with open(ITEMS_JSON_FILE) as f:
        raw_items_data = json.load(f)
    return raw_items_data['items']['journalitem']


def group_journals_by_item(journals_data):
    return {item_id: journal
            for journal_id, journal in journals_data.items()
            for item_id in journal['valid_items']}


_journals_grouped_by_valid_item = load_journals()
