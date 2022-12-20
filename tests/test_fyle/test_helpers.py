import pytest
from rest_framework.response import Response
from rest_framework.views import status
from datetime import datetime, timezone
from apps.fyle.helpers import *
from apps.fyle.models import ExpenseGroupSettings, ExpenseFilter
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, Workspace
from fyle_netsuite_api.tests import settings
from .fixtures import data


@pytest.mark.django_db()
def test_add_expense_id_to_expense_group_settings():

    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.corporate_credit_card_expense_group_fields == [
        'employee_email', 'report_id', 'claim_number', 'fund_source']

    add_expense_id_to_expense_group_settings(1)
    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)

    assert sorted(expense_group_setting.corporate_credit_card_expense_group_fields) == [
                  'claim_number', 'employee_email', 'expense_id', 'fund_source', 'report_id']


@pytest.mark.django_db()
def test_update_import_card_credits_flag():

    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.import_card_credits == False

    update_import_card_credits_flag('EXPENSE REPORT', 'EXPENSE REPORT', 1)
    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.import_card_credits == True

    update_import_card_credits_flag('BILL', 'EXPENSE_REPORT', 1)
    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.import_card_credits == False


@pytest.mark.django_db()
def test_update_use_employee_attributes_flag():

    general_mapping = GeneralMapping.objects.get(id=1)
    general_mapping.use_employee_department = True
    general_mapping.use_employee_location = True
    general_mapping.use_employee_class = True
    general_mapping.save()

    update_use_employee_attributes_flag(1)

    general_mapping = GeneralMapping.objects.get(id=1)
    assert general_mapping.use_employee_department == False
    assert general_mapping.use_employee_location == False


@pytest.mark.django_db
def test_check_interval_and_sync_dimension(access_token, mocker, db):
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=data['get_all_employees']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Categories.list_all',
        return_value=data['get_all_categories']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Projects.list_all',
        return_value=data['get_all_projects']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.CostCenters.list_all',
        return_value=data['get_all_cost_centers']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.ExpenseFields.list_all',
        return_value=data['get_all_expense_fields']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.CorporateCards.list_all',
        return_value=data['get_all_corporate_cards']
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.TaxGroups.list_all',
        return_value=data['get_all_tax_groups']
    )
    workspace = Workspace.objects.get(id=1)
    fyle_credentials = FyleCredential.objects.get(workspace_id=1)
    response = check_interval_and_sync_dimension(workspace, fyle_credentials)

    assert response == True

    workspace.source_synced_at = datetime.now(timezone.utc)
    response = check_interval_and_sync_dimension(workspace, settings.FYLE_REFRESH_TOKEN)
    assert response == False


def test_post_request(mocker):
    mocker.patch(
        'apps.fyle.helpers.requests.post',
        return_value=Response(
            {
                'message': 'Post request'
            },
            status=status.HTTP_200_OK
        )
    )
    try:
        post_request(url='sdfghjk', body={}, refresh_token='srtyu')
    except:
        logger.info('Error in post request')
    
    mocker.patch(
        'apps.fyle.helpers.requests.post',
        return_value=Response(
            {
                'message': 'Post request'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    )
    try:
        post_request(url='sdfghjk', body={}, refresh_token='srtyu')
    except:
        logger.info('Error in post request')


def test_get_request(mocker):
    mocker.patch(
        'apps.fyle.helpers.requests.get',
        return_value=Response(
            {
                'message': 'Get request'
            },
            status=status.HTTP_200_OK
        )
    )
    try:
        get_request(url='sdfghjk', params={'sample': True}, refresh_token='srtyu')
    except:
        logger.info('Error in post request')

    mocker.patch(
        'apps.fyle.helpers.requests.get',
        return_value=Response(
            {
                'message': 'Get request'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    )
    try:
        get_request(url='sdfghjk', params={'sample': True}, refresh_token='srtyu')
    except:
        logger.info('Error in post request')


def test_get_fyle_orgs(mocker):
    mocker.patch(
        'apps.fyle.helpers.requests.get',
        return_value=Response(
            {
                'message': 'Get request'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    )
    try:
        get_fyle_orgs(refresh_token='srtyu', cluster_domain='erty')
    except:
        logger.info('Error in post request')


def test_get_cluster_domain(mocker):
    mocker.patch(
        'apps.fyle.helpers.requests.post',
        return_value=Response(
            {
                'message': 'Post request'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    )
    try:
        get_cluster_domain(refresh_token='srtyu')
    except:
        logger.info('Error in post request')

@pytest.mark.django_db()
def test_construct_expense_filter(mocker, add_fyle_credentials):
    #employee-email-is-equal
    expense_filter = ExpenseFilter(
        condition = 'employee_email',
        operator = 'in',
        values = ['killua.z@fyle.in', 'naruto.u@fyle.in'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'employee_email__in':['killua.z@fyle.in', 'naruto.u@fyle.in']}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #report-id-is-equal
    expense_filter = ExpenseFilter(
        condition = 'report_id',
        operator = 'in',
        values = ['ajdnwjnadw', 'ajdnwjnlol'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'report_id__in':['ajdnwjnadw', 'ajdnwjnlol']}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #report-name-is-equal
    expense_filter = ExpenseFilter(
        condition = 'report_title',
        operator = 'iexact',
        values = ['#17:  Dec 2022'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'report_title__iexact':'#17:  Dec 2022'}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #report-name-contains
    expense_filter = ExpenseFilter(
        condition = 'report_title',
        operator = 'icontains',
        values = ['Dec 2022'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'report_title__icontains':'Dec 2022'}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #spent-at-is-before
    expense_filter = ExpenseFilter(
        condition = 'spent_at',
        operator = 'lt',
        values = ['2020-04-20 23:59:59+00'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'spent_at__lt':'2020-04-20 23:59:59+00'}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #spent-at-is-on-or-before
    expense_filter = ExpenseFilter(
        condition = 'spent_at',
        operator = 'lte',
        values = ['2020-04-20 23:59:59+00'],
        rank = '1'
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'spent_at__lte':'2020-04-20 23:59:59+00'}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-number-is-equal
    expense_filter = ExpenseFilter(
        condition = 'Gon Number',
        operator = 'in',
        values = [102,108],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Gon Number__in':[102, 108]}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-number-is-not-empty
    expense_filter = ExpenseFilter(
        condition = 'Gon Number',
        operator = 'isnull',
        values = ['False'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Gon Number__exact': None}
    respone = ~Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-number-is--empty
    expense_filter = ExpenseFilter(
        condition = 'Gon Number',
        operator = 'isnull',
        values = ['True'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Gon Number__isnull': True}
    filter2 = {'custom_properties__Gon Number__exact': None}
    respone = Q(**filter1) | Q(**filter2)

    assert constructed_expense_filter == respone

    #custom-properties-text-is-equal
    expense_filter = ExpenseFilter(
        condition = 'Killua Text',
        operator = 'in',
        values = ['hunter', 'naruto', 'sasuske'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Killua Text__in':['hunter', 'naruto', 'sasuske']}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-text-is-not-empty
    expense_filter = ExpenseFilter(
        condition = 'Killua Text',
        operator = 'isnull',
        values = ['False'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Killua Text__exact': None}
    respone = ~Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-text-is--empty
    expense_filter = ExpenseFilter(
        condition = 'Killua Text',
        operator = 'isnull',
        values = ['True'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Killua Text__isnull': True}
    filter2 = {'custom_properties__Killua Text__exact': None}
    respone = Q(**filter1) | Q(**filter2)

    assert constructed_expense_filter == respone

    #custom-properties-select-is-equal
    expense_filter = ExpenseFilter(
        condition = 'Kratos',
        operator = 'in',
        values = ['BOOK', 'Dev-D'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Kratos__in':['BOOK', 'Dev-D']}
    respone = Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-select-is-not-empty
    expense_filter = ExpenseFilter(
        condition = 'Kratos',
        operator = 'isnull',
        values = ['False'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Kratos__exact': None}
    respone = ~Q(**filter1)

    assert constructed_expense_filter == respone

    #custom-properties-select-is--empty
    expense_filter = ExpenseFilter(
        condition = 'Kratos',
        operator = 'isnull',
        values = ['True'],
        rank = '1',
        is_custom = True
    )
    constructed_expense_filter = construct_expense_filter(expense_filter)

    filter1 = {'custom_properties__Kratos__isnull': True}
    filter2 = {'custom_properties__Kratos__exact': None}
    respone = Q(**filter1) | Q(**filter2)

    assert constructed_expense_filter == respone

    # #multiple cases
    # expense_filter1 = ExpenseFilter(
    #     condition = 'employee_email',
    #     operator = 'in',
    #     values = ['killua.z@fyle.in', 'naruto.u@fyle.in'],
    #     rank = '1'
    # )
    # constructed_expense_filter1 = construct_expense_filter(expense_filter1)

    # expense_filter2 = ExpenseFilter(
    #     condition = 'report_id',
    #     operator = 'in',
    #     values = ['ajdnwjnadw', 'ajdnwjnlol'],
    #     rank = '1'
    # )

    # constructed_expense_filter2 = construct_expense_filter(expense_filter2)

    # filter1 = {'employee_email__in':['killua.z@fyle.in', 'naruto.u@fyle.in']}
    # respone = Q(**filter1)

    # assert constructed_expense_filter == respone

    

    # filter1 = {'report_id__in':['ajdnwjnadw', 'ajdnwjnlol']}
    # respone = Q(**filter1)

    # assert constructed_expense_filter == respone

    