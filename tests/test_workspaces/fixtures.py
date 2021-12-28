"""
Contains various tests Payloads
"""
import random
from fyle_netsuite_api.tests import settings


def create_netsuite_credential_object_payload(workspace_id):
    netsuite_credentials = {
        'workspace': workspace_id,
        'ns_account_id': settings.NS_ACCOUNT_ID,
        'ns_token_id': settings.NS_TOKEN_ID,
        'ns_token_secret': settings.NS_TOKEN_SECRET
    }
    return netsuite_credentials


def create_configurations_object_payload(workspace_id):
    reimbursable_expenses_objects = ['JOURNAL ENTRY', 'BILL']
    corporate_credit_card_expenses_object = ['BILL', 'CREDIT CARD CHARGE', 'JOURNAL ENTRY']
    memo_structure = ["employee_email", "category", "report_number"]

    workspace_general_settings_payload = {
        'workspace': workspace_id,
        'reimbursable_expenses_object': random.choice(reimbursable_expenses_objects),
        'corporate_credit_card_expenses_object': random.choice(corporate_credit_card_expenses_object),
        'sync_fyle_to_netsuite_payments': False,
        'sync_netsuite_to_fyle_payments': False,
        'import_projects': True,
        'import_categories': True,
        'auto_map_employees': '',
        'auto_create_destination_entity': False,
        'auto_create_merchants': False,
        'employee_field_mapping': 'VENDOR',
        'memo_structure': memo_structure
    }

    return workspace_general_settings_payload
