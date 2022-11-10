import pytest
from rest_framework.response import Response
from rest_framework.views import status
from datetime import datetime, timezone
from apps.fyle.helpers import *
from apps.fyle.models import ExpenseGroupSettings
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