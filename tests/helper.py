import json
from os import path
from typing import List
from apps.fyle.models import ExpenseFilter
from apps.fyle.helpers import construct_expense_filter

def dict_compare_keys(d1, d2, key_path=''):
    """
    Compare two dicts recursively and see if dict1 has any keys that dict2 does not
    Returns: list of key paths
    """
    res = []
    if not d1:
        return res
    if not isinstance(d1, dict):
        return res
    for k in d1:
        if k not in d2:
            missing_key_path = f'{key_path}->{k}'
            res.append(missing_key_path)
        else:
            if isinstance(d1[k], dict):
                key_path1 = f'{key_path}->{k}'
                res1 = dict_compare_keys(d1[k], d2[k], key_path1)
                res = res + res1
            elif isinstance(d1[k], list):
                key_path1 = f'{key_path}->{k}[0]'
                dv1 = d1[k][0] if len(d1[k]) > 0 else None
                dv2 = d2[k][0] if len(d2[k]) > 0 else None
                res1 = dict_compare_keys(dv1, dv2, key_path1)
                res = res + res1
    return res

def get_response_dict(filename):
    basepath = path.dirname(__file__)
    filepath = path.join(basepath, filename)
    mock_json = open(filepath, 'r').read()
    mock_dict = json.loads(mock_json)
    return mock_dict

def get_multiple_expense_filter_query(expense_filters: List[ExpenseFilter]):
    final_filter = None
    for expense_filter in expense_filters:
        constructed_expense_filter = construct_expense_filter(expense_filter)
        if expense_filter.rank == '1':
            final_filter = (constructed_expense_filter)
        elif expense_filter.rank != '1' and join_by == 'AND':
            final_filter = final_filter & (constructed_expense_filter)
        elif expense_filter.rank != '1' and join_by == 'OR':
            final_filter = final_filter | (constructed_expense_filter)

        join_by = expense_filter.join_by
    
    return final_filter
