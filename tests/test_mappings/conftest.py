"""
Contains various tests Payloads
"""

import pytest
from apps.workspaces.models import Configuration, Workspace
from apps.mappings.models import GeneralMapping
from apps.fyle.models import ExpenseGroupSettings


@pytest.fixture
def create_general_mapping(django_db_setup):
    
    workspace = Workspace.objects.filter(id=1).first()

    expense_group_settings = ExpenseGroupSettings.objects.update_or_create(
        workspace_id=workspace.id,
        defaults={
            'reimbursable_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
            'corporate_credit_card_expense_group_fields': ['employee_email','report_id','claim_number','fund_source'],
            'expense_state':'PAYMENT_PROCESSING',
            'export_date_type': 'current_date'
        }
    )

    configuration = Configuration(
        id=1,
        workspace=workspace,
        employee_field_mapping='EMPLOYEE',
        reimbursable_expenses_object='EXPENSE_REPORT',
        corporate_credit_card_expenses_object='EXPENSE_REPORT',
        import_categories=True,
        import_tax_items=False,
        import_projects=True,
        auto_map_employees='NAME',
        auto_create_destination_entity=False,
    )

    configuration.save()


    general_mapping = GeneralMapping(
        id=1,
        location_name='01: San Francisco',
        location_level='ALL',
        location_id=2,
        accounts_payable_name='Accounts Payable',
        accounts_payable_id=25,
        reimbursable_account_id=25,
        reimbursable_account_name='Accounts Payable',
        use_employee_department=False,
        use_employee_location=False,
        use_employee_class=False,
        default_ccc_vendor_id=3381,
        default_ccc_vendor_name='Allison Hill',
        workspace=workspace
    )

    general_mapping.save()



    


