from typing import Dict

from apps.mappings.tasks import schedule_projects_creation, schedule_categories_creation, schedule_auto_map_employees, \
    schedule_auto_map_ccc_employees

from apps.netsuite.tasks import schedule_vendor_payment_creation, schedule_reimbursements_sync, \
    schedule_netsuite_objects_status_sync
from fyle_netsuite_api.utils import assert_valid
from .models import WorkspaceGeneralSettings


def create_or_update_general_settings(general_settings_payload: Dict, workspace_id):
    """
    Create or update general settings
    :param workspace_id:
    :param general_settings_payload: general settings payload
    :return:
    """
    assert_valid(
        'reimbursable_expenses_object' in general_settings_payload and general_settings_payload[
            'reimbursable_expenses_object'], 'reimbursable_expenses_object field is blank')

    assert_valid('auto_map_employees' in general_settings_payload, 'auto_map_employees field is missing')

    if general_settings_payload['auto_map_employees']:
        assert_valid(general_settings_payload['auto_map_employees'] in ['EMAIL', 'NAME', 'EMPLOYEE_CODE'],
                     'auto_map_employees can have only EMAIL / NAME / EMPLOYEE_CODE')

    general_settings, _ = WorkspaceGeneralSettings.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': general_settings_payload['reimbursable_expenses_object'],
            'corporate_credit_card_expenses_object':
                general_settings_payload['corporate_credit_card_expenses_object']
                if 'corporate_credit_card_expenses_object' in general_settings_payload
                   and general_settings_payload['corporate_credit_card_expenses_object'] else None,
            'sync_fyle_to_netsuite_payments': general_settings_payload['sync_fyle_to_netsuite_payments'],
            'sync_netsuite_to_fyle_payments': general_settings_payload['sync_netsuite_to_fyle_payments'],
            'import_projects': general_settings_payload['import_projects'],
            'import_categories': general_settings_payload['import_categories'],
            'auto_map_employees': general_settings_payload['auto_map_employees'],
            'auto_create_destination_entity': general_settings_payload['auto_create_destination_entity']
        }
    )

    schedule_projects_creation(import_projects=general_settings.import_projects, workspace_id=workspace_id)
    schedule_categories_creation(import_categories=general_settings.import_categories, workspace_id=workspace_id)

    schedule_vendor_payment_creation(
        sync_fyle_to_netsuite_payments=general_settings.sync_fyle_to_netsuite_payments,
        workspace_id=workspace_id
    )

    schedule_netsuite_objects_status_sync(
        sync_netsuite_to_fyle_payments=general_settings.sync_netsuite_to_fyle_payments,
        workspace_id=workspace_id
    )

    schedule_reimbursements_sync(
        sync_netsuite_to_fyle_payments=general_settings.sync_netsuite_to_fyle_payments,
        workspace_id=workspace_id
    )

    schedule_auto_map_employees(general_settings_payload['auto_map_employees'], workspace_id)

    if general_settings_payload['auto_map_employees'] is None:
        schedule_auto_map_ccc_employees(workspace_id=workspace_id)

    return general_settings
