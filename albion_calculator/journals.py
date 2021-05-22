import json

from albion_calculator.items import ITEMS_JSON_FILE

CRAFTING_TYPES = ['WARRIOR', 'HUNTER', 'MAGE', 'TOOLMAKER']


def get_journal_for_item(item_id):
    return journals_grouped_by_valid_item.get(item_id, None)


def load_journals():
    raw_journals_data = read_journals_from_items_file()
    raw_crafting_journals_data = filter_crafting_journals(raw_journals_data)
    journals = {}
    for raw_journal in raw_crafting_journals_data:
        valid_items = raw_journal['famefillingmissions']['craftitemfame']['validitem']
        valid_items_ids = [item['@id'] for item in valid_items]

        item_id = raw_journal['@uniquename']
        journal = {'max_fame': int(raw_journal['@maxfame']),
                   'cost': int(raw_journal['craftingrequirements']['@silver']),
                   'valid_items': valid_items_ids,
                   'item_id': item_id}
        journals[item_id] = journal
    return journals


def filter_crafting_journals(raw_journals_data):
    result = []
    for journal in raw_journals_data:
        item_id = journal['@uniquename']
        journal_type = item_id.split('_')[2]
        if journal_type in CRAFTING_TYPES:
            result.append(journal)
    return result


def read_journals_from_items_file():
    with open(ITEMS_JSON_FILE) as f:
        raw_items_data = json.load(f)
        raw_journals_data = raw_items_data['items']['journalitem']
    return raw_journals_data


def group_journals_by_item(journals_data):
    return {item_id: journal for journal_id, journal in journals_data.items() for item_id in journal['valid_items']}


journals_data = load_journals()

journals_grouped_by_valid_item = group_journals_by_item(journals_data)
