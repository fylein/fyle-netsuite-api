from datetime import datetime
import pytest
from django.core.management import call_command
from apps.workspaces.models import Workspace
from apps.workspaces.models import Workspace, NetSuiteCredentials
from apps.netsuite.helpers import check_interval_and_sync_dimension

from fyle_accounting_mappings.models import Mapping, MappingSetting, DestinationAttribute, CategoryMapping,\
    EmployeeMapping, ExpenseAttribute


@pytest.fixture
def sync_netsuite_dimensions(test_connection):
    workspace = Workspace.objects.get(id=1)
    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=1)
    check_interval_and_sync_dimension(workspace, netsuite_credentials)


@pytest.fixture
def category_and_account_creation():
    expense_attribute = ExpenseAttribute(
        id=2,
        attribute_type='CATEGORY',
        display_name='Category',
        value='Food',
        source_id='66061',
        workspace_id=1,
        detail=None,
        auto_mapped=True,
        auto_created=False,
        created_at=datetime.now()
    )

    destination_attribtue = DestinationAttribute(
        id=2,
        attribute_type='ACCOUNT',
        display_name='Account',
        value='Advertising',
        destination_id='65',
        workspace_id=1,
        detail=None,
        auto_created=False,
        created_at=datetime.now()
    )

    expense_attribute.save()
    destination_attribtue.save()


@pytest.fixture
def employee_and_vendor_mappings():
    expense_attribute = ExpenseAttribute(
        id=1,
        attribute_type='EMPLOYEE',
        display_name='Employee',
        value='admin1@fylefornt.com',
        source_id='ouUZxBCXcNvh',
        workspace_id=1,
        detail={"user_id": "us5zYTCuN1kE", "location": None, "full_name": "Steven Strange", "department": None, "department_id": None, "employee_code": None, "department_code": None},
        auto_mapped=True,
        auto_created=False
    )

    destination_attribtue = DestinationAttribute(
        id=1,
        attribute_type='VENDOR',
        display_name='Vendor',
        value='Uber BV',
        destination_id='12106',
        workspace_id=1,
        detail={"email": "user34@fyleforjatinorg.com", "class_id": None, "location_id": None, "department_id": None},
        auto_created=False
    )

    expense_attribute.save()
    destination_attribtue.save()


@pytest.fixture
def employee_and_employee_mappings(db):
    expense_attribute = ExpenseAttribute(
        id=3,
        attribute_type='EMPLOYEE',
        display_name='Employee',
        value='admin1@fylefornt.com',
        source_id='ouUZxBCXcNvh',
        workspace_id=1,
        detail={"user_id": "us5zYTCuN1kE", "location": None, "full_name": "Steven Strange", "department": None, "department_id": None, "employee_code": None, "department_code": None},
        auto_mapped=True,
        auto_created=False
    )

    destination_attribute = DestinationAttribute(
        id=3,
        attribute_type='EMPLOYEE',
        display_name='Employee',
        value='Nillesh Pant',
        destination_id='3281',
        workspace_id=1,
        detail={"email": "user2@fyleforxyzcorp.in", "class_id": None, "location_id": None, "department_id": None},
        auto_created=False
    )

    expense_attribute.save()
    destination_attribute.save()

@pytest.fixture
def mappings_for_bill(db, test_connection, employee_and_vendor_mappings, category_and_account_creation):

    employee_mappings = EmployeeMapping(
       destination_vendor_id=1,
       source_employee_id=1,
       workspace_id=1
    )

    employee_mappings.save()

    category_mapping = CategoryMapping(
        destination_account_id=2,
        source_category_id=2,
        workspace_id=1
    )
    category_mapping.save()

@pytest.fixture
def mappings_for_expense_report(db, test_connection, employee_and_employee_mappings, category_and_account_creation):

    employee_mappings = EmployeeMapping(
       destination_employee_id=3,
       source_employee_id=3,
       workspace_id=1
    )

    employee_mappings.save()

    category_mapping = CategoryMapping(
        destination_account_id=2,
        source_category_id=2,
        workspace_id=1
    )
    category_mapping.save()