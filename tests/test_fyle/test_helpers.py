import pytest
from apps.fyle.helpers import add_expense_id_to_expense_group_settings, update_import_card_credits_flag, \
    update_use_employee_attributes_flag, check_interval_and_sync_dimension
from apps.fyle.models import ExpenseGroupSettings
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import Workspace
from fyle_netsuite_api.tests import settings

@pytest.mark.django_db()
def test_add_expense_id_to_expense_group_settings():

    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.corporate_credit_card_expense_group_fields == ['employee_email', 'report_id', 'claim_number', 'fund_source']

    add_expense_id_to_expense_group_settings(1)
    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    
    assert sorted(expense_group_setting.corporate_credit_card_expense_group_fields)  == ['claim_number', 'employee_email', 'expense_id', 'fund_source', 'report_id']
    

@pytest.mark.django_db()
def test_update_import_card_credits_flag():

    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)
    assert expense_group_setting.import_card_credits == False

    update_import_card_credits_flag('EXPENSE REPORT', 1)
    expense_group_setting = ExpenseGroupSettings.objects.get(id=1)

    assert expense_group_setting.import_card_credits == True

@pytest.mark.django_db()
def test_update_use_employee_attributes_flag():

    general_mapping = GeneralMapping.objects.get(id=1)
    general_mapping.use_employee_department = True
    general_mapping.use_employee_location = True
    general_mapping.save()

    update_use_employee_attributes_flag(1)

    general_mapping = GeneralMapping.objects.get(id=1)
    assert general_mapping.use_employee_department == False
    assert general_mapping.use_employee_location == False

@pytest.mark.django_db
def test_check_interval_and_sync_dimension(test_connection):
    
    workspace = Workspace.objects.get(id=1)
    response = check_interval_and_sync_dimension(workspace, settings.FYLE_REFRESH_TOKEN)

    assert response == True
