from apps.internal.actions import get_accounting_fields, get_exported_entry
from tests.test_netsuite.fixtures import data

def test_get_accounting_fields(db, mocker):
    query_params = {
        'org_id': 'or79Cob97KSh',
        'resource_type': 'employees',
    }
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=data['get_all_employees']    
    )

    mocker.patch('netsuitesdk.api.currencies.Currencies.get_all')

    mocker.patch(
        'netsuitesdk.api.custom_lists.CustomLists.get',
        return_value=data['get_custom_list']
    )

    fields = get_accounting_fields(query_params)
    assert fields is not None

    query_params['resource_type'] = 'custom_lists'
    query_params['internal_id'] = '1'
    fields = get_accounting_fields(query_params)
    assert fields is not None


def test_get_exported_entry(db, mocker):
    query_params = {
        'org_id': 'or79Cob97KSh',
        'resource_type': 'vendor_bills',
        'internal_id': '1'
    }
    mocker.patch(
        'netsuitesdk.api.vendor_bills.VendorBills.get',
        return_value={'summa': 'hehe'}
    )

    entry = get_exported_entry(query_params)
    assert entry is not None
