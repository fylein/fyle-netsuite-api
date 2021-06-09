from typing import Dict

from apps.mappings.tasks import schedule_projects_creation, schedule_categories_creation, schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees

from apps.netsuite.tasks import schedule_vendor_payment_creation, schedule_reimbursements_sync, \
    schedule_netsuite_objects_status_sync
from fyle_netsuite_api.utils import assert_valid
from .models import Configuration
from ..fyle.models import ExpenseGroupSettings


# This should be in the model
def create_or_update_configurations(configurations_payload: Dict, workspace_id):
    """
    Create or update general settings
    :param workspace_id:
    :param configurations_payload: general settings payload
    :return:
    """
    # Validations
    assert_valid(
        'reimbursable_expenses_object' in configurations_payload and configurations_payload[
            'reimbursable_expenses_object'], 'reimbursable_expenses_object field is blank')

    assert_valid('auto_map_employees' in configurations_payload, 'auto_map_employees field is missing')

    if configurations_payload['auto_map_employees']:
        assert_valid(configurations_payload['auto_map_employees'] in ['EMAIL', 'NAME', 'EMPLOYEE_CODE'],
                     'auto_map_employees can have only EMAIL / NAME / EMPLOYEE_CODE')

    # Actual update or create
    configurations, _ = Configuration.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': configurations_payload['reimbursable_expenses_object'],
            'corporate_credit_card_expenses_object':
                configurations_payload['corporate_credit_card_expenses_object']
                if 'corporate_credit_card_expenses_object' in configurations_payload
                   and configurations_payload['corporate_credit_card_expenses_object'] else None,
            'sync_fyle_to_netsuite_payments': configurations_payload['sync_fyle_to_netsuite_payments'],
            'sync_netsuite_to_fyle_payments': configurations_payload['sync_netsuite_to_fyle_payments'],
            'import_projects': configurations_payload['import_projects'],
            'import_categories': configurations_payload['import_categories'],
            'auto_map_employees': configurations_payload['auto_map_employees'],
            'auto_create_merchants': configurations_payload['auto_create_merchants'],
            'auto_create_destination_entity': configurations_payload['auto_create_destination_entity']
        }
    )

    # Updating expense group settings for Credit Card Charge --> Move to Fyle.utils
    if configurations.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
        expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)

        ccc_expense_group_fields = expense_group_settings.corporate_credit_card_expense_group_fields
        ccc_expense_group_fields.append('expense_id')
        expense_group_settings.corporate_credit_card_expense_group_fields = list(set(ccc_expense_group_fields))

        expense_group_settings.save()

    # Schedule Import and Mapping Jobs -> Move to mappings.utils
    schedule_projects_creation(import_projects=configurations.import_projects, workspace_id=workspace_id)
    schedule_categories_creation(import_categories=configurations.import_categories, workspace_id=workspace_id)
    schedule_auto_map_employees(configurations_payload['auto_map_employees'], workspace_id)
    if configurations_payload['auto_map_employees'] is None:
        schedule_auto_map_ccc_employees(workspace_id=workspace_id)

    # Schedule Payments --> netsuite.utils
    schedule_vendor_payment_creation(
        sync_fyle_to_netsuite_payments=configurations.sync_fyle_to_netsuite_payments,
        workspace_id=workspace_id
    )

    schedule_netsuite_objects_status_sync(
        sync_netsuite_to_fyle_payments=configurations.sync_netsuite_to_fyle_payments,
        workspace_id=workspace_id
    )

    schedule_reimbursements_sync(
        sync_netsuite_to_fyle_payments=configurations.sync_netsuite_to_fyle_payments,
        workspace_id=workspace_id
    )

    return configurations
