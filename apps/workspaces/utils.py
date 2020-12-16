from typing import Dict

from apps.netsuite.tasks import schedule_vendor_payment_creation
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

    general_settings, _ = WorkspaceGeneralSettings.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': general_settings_payload['reimbursable_expenses_object'],
            'corporate_credit_card_expenses_object':
                general_settings_payload['corporate_credit_card_expenses_object']
                if 'corporate_credit_card_expenses_object' in general_settings_payload
                and general_settings_payload['corporate_credit_card_expenses_object'] else None,
            'sync_fyle_to_netsuite_payments': general_settings_payload['sync_fyle_to_netsuite_payments'],
        }
    )

    schedule_vendor_payment_creation(
        sync_fyle_to_netsuite_payments=general_settings.sync_fyle_to_netsuite_payments,
        workspace_id=workspace_id
    )

    return general_settings
