"""
Contains various tests Payloads
"""
import random
from fyle_netsuite_api.tests import settings
from fyle_rest_auth.utils import AuthUtils
from fyle_rest_auth.models import AuthToken
from apps.workspaces.models import Workspace, Configuration

auth_utils = AuthUtils()


def create_netsuite_credential_object_payload(workspace_id):
    netsuite_credentials = {
        'workspace': workspace_id,
        'ns_account_id': 'TSTDRV2089588',
        'ns_token_id': 'sdfghjkl',
        'ns_token_secret': 'sdfghjkl;'
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
        'import_vendors_as_merchants': True,
        'auto_map_employees': '',
        'auto_create_destination_entity': False,
        'auto_create_merchants': False,
        'employee_field_mapping': 'VENDOR',
        'memo_structure': memo_structure
    }

    return workspace_general_settings_payload

def create_fyle_credential_object_payload(workspace_id):
    fyle_credentials = {
        'code': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjbGllbnRfaWQiOiJ0cGFWVVhtd2FZWGVRIiwicmVzcG9uc2VfdHlwZSI6ImNvZGUiLCJjbHVzdGVyX2RvbWFpbiI6Imh0dHBzOi8vc3RhZ2luZy5meWxlLnRlY2giLCJvcmdfdXNlcl9pZCI6Im91NDV2ekhFWUJGUyIsImV4cCI6MTY1MjI2MzMwMH0.D6WdXnkUcKMU98VjZEMz6OH1kGtRXVj1uLGsTeIo0IQ'
    }
    return fyle_credentials
