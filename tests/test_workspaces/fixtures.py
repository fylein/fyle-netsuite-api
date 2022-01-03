"""
Contains various tests Payloads
"""
import pytest
import random
from datetime import datetime

from fyle_netsuite_api.tests import settings
from fyle_rest_auth.utils import AuthUtils
from fyle_rest_auth.models import AuthToken

from apps.workspaces.models import Workspace

auth_utils = AuthUtils()

def create_netsuite_credential_object_payload(workspace_id):
    netsuite_credentials = {
        'workspace': workspace_id,
        'ns_account_id': settings.NS_ACCOUNT_ID,
        'ns_token_id': settings.NS_TOKEN_ID,
        'ns_token_secret': settings.NS_TOKEN_SECRET
    }
    return netsuite_credentials

def create_workspace():
    auth_tokens = AuthToken.objects.get(user__user_id='usezCopk4qdF')
    fyle_user = auth_utils.get_fyle_user(auth_tokens.refresh_token, origin_address=None)
    org_name = fyle_user['org_name']
    org_id = fyle_user['org_id']
    Workspace.objects.create(name=org_name, fyle_org_id=org_id)

def create_configurations_object_payload(workspace_id):
    reimbursable_expenses_objects = ['JOURNAL ENTRY', 'BILL']
    corporate_credit_card_expenses_object = ['BILL', 'CREDIT CARD CHARGE', 'JOURNAL ENTRY']

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
        'employee_field_mapping': 'VENDOR'
    }

    return workspace_general_settings_payload
