import logging
from apps.fyle.models import ExpenseGroup
import pytest
from unittest import mock
from django_q.models import Schedule
from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, CategoryMapping, \
     Mapping, MappingSetting, EmployeeMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import Configuration, FyleCredential, NetSuiteCredentials
from apps.mappings.tasks import *
from fyle_integrations_platform_connector import PlatformConnector
from apps.mappings.models import GeneralMapping
from tests.test_netsuite.fixtures import data as netsuite_data
from tests.test_fyle.fixtures import data as fyle_data
from .fixtures import data
from fyle.platform.exceptions import WrongParamsError

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def test_resolve_expense_attribute_errors(db):
    workspace_id = 1
    expense_group = ExpenseGroup.objects.get(id=1)

    employee_attribute = ExpenseAttribute.objects.filter(
        value=expense_group.description.get('employee_email'),
        workspace_id=expense_group.workspace_id,
        attribute_type='EMPLOYEE'
    ).first()

    error, _ = Error.objects.update_or_create(
        workspace_id=expense_group.workspace_id,
        expense_attribute=employee_attribute,
        defaults={
            'type': 'EMPLOYEE_MAPPING',
            'error_title': employee_attribute.value,
            'error_detail': 'Employee mapping is missing',
            'is_resolved': False
        }
    )

    resolve_expense_attribute_errors('EMPLOYEE', workspace_id, 'EMPLOYEE')
    assert Error.objects.get(id=error.id).is_resolved == True

    error, _ = Error.objects.update_or_create(
        workspace_id=expense_group.workspace_id,
        expense_attribute=employee_attribute,
        defaults={
            'type': 'EMPLOYEE_MAPPING',
            'error_title': employee_attribute.value,
            'error_detail': 'Employee mapping is missing',
            'is_resolved': False
        }
    )

    resolve_expense_attribute_errors('EMPLOYEE', workspace_id, 'VENDOR')
    assert Error.objects.get(id=error.id).is_resolved == True

    source_category = ExpenseAttribute.objects.filter(
        id=34,
        workspace_id=1,
        attribute_type='CATEGORY'
    ).first()

    error, _ = Error.objects.update_or_create(
        workspace_id=1,
        expense_attribute=source_category,
        defaults={
            'type': 'CATEGORY_MAPPING',
            'error_title': source_category.value,
            'error_detail': 'Category mapping is missing',
            'is_resolved': False
        }
    )

    resolve_expense_attribute_errors('CATEGORY', workspace_id, 'ACCOUNT')
    assert Error.objects.get(id=error.id).is_resolved == True


def test_remove_duplicates(db):

    attributes = DestinationAttribute.objects.filter(attribute_type='EMPLOYEE')
    assert len(attributes) == 32

    attributes = remove_duplicates(attributes)
    assert len(attributes) == 20


def test_async_auto_map_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=netsuite_data['get_all_vendors']    
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0]
    )

    async_auto_map_employees(1)

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 1 

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.employee_field_mapping = 'VENDOR'
    configuration.save()

    async_auto_map_employees(1)

    vendors = DestinationAttribute.objects.filter(workspace_id=1, attribute_type='VENDOR').count()
    assert vendors == 7


def test_schedule_auto_map_employees(mocker, db):
    mocker.patch(
        'netsuitesdk.api.vendors.Vendors.get_all_generator',
        return_value=netsuite_data['get_all_vendors']    
    )

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0] 
    )
    configuration = Configuration.objects.get(workspace_id=1)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

    schedule_auto_map_employees(employee_mapping_preference='NAME', workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_employees',
        args='{}'.format(1),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_employees'

    schedule_auto_map_employees(employee_mapping_preference='', workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_employees',
        args='{}'.format(1),
    ).first()
    assert schedule == None
    async_auto_map_employees(1)

    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 1


@pytest.mark.django_db
def test_schedule_auto_map_ccc_employees(db, mocker):
    workspace_id=2

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    schedule_auto_map_ccc_employees(workspace_id=2)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_ccc_account',
        args='{0}'.format(workspace_id),
    ).first()
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_ccc_account'

    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    async_auto_map_ccc_account(workspace_id=1)
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 42

    employee = ExpenseAttribute.objects.filter(value='included@fyleforqvd.com', workspace_id=1).first()

    assert employee != None
    assert employee.value == 'included@fyleforqvd.com'

    employee = ExpenseAttribute.objects.filter(value='excluded@fyleforqvd.com', workspace_id=1).first()

    assert employee == None

    configuration = Configuration.objects.get(workspace_id=2)
    configuration.auto_map_employees = ''
    configuration.save()

    schedule_auto_map_ccc_employees(workspace_id=1)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_ccc_account',
        args='{}'.format(1),
    ).first()

    assert schedule == None


@pytest.mark.django_db
def test_async_auto_map_ccc_account(db, mocker):
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Employees.list_all',
        return_value=fyle_data['get_all_employees']
    )

    general_mappings = GeneralMapping.objects.get(workspace_id=1)

    general_mappings.default_ccc_account_name = 'Aus Account'
    general_mappings.default_ccc_account_id = 228
    general_mappings.save()

    async_auto_map_ccc_account(workspace_id=1)
    employee_mappings = EmployeeMapping.objects.filter(workspace_id=1).count()
    assert employee_mappings == 42


def test_schedule_netsuite_employee_creation_on_fyle(db):
    workspace_id=1
    schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees=True, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
        args='{}'.format(workspace_id),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_netsuite_employees_on_fyle'

    schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees=False, workspace_id=workspace_id)

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
        args='{}'.format(workspace_id),
    ).first()

    assert schedule == None


def test_auto_create_netsuite_employees_on_fyle(db, mocker):
    workspace_id = 1

    mocker.patch(
        'netsuitesdk.api.employees.Employees.get_all_generator',
        return_value=netsuite_data['get_all_employees']    
    )
    mocker.patch(
        'netsuitesdk.api.employees.Employees.get',
        return_value=netsuite_data['get_all_employees'][0][0]
    )
    mocker.patch(
        'fyle.platform.apis.v1beta.admin.Departments.list_all',
        return_value=netsuite_data['get_departments']
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Employees.sync',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Departments.post',
        return_value=[]
    )
    mocker.patch(
      'fyle.platform.apis.v1beta.admin.Employees.invite_bulk',
      return_value=fyle_data['get_all_employees']
   )

    employees = DestinationAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    assert employees == 7
    assert expense_attribute == 30

    auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)
    
    employees = DestinationAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    expense_attribute = ExpenseAttribute.objects.filter(workspace_id=workspace_id, attribute_type='EMPLOYEE').count()
    assert employees == 13
    assert expense_attribute == 30

    with mock.patch('fyle_integrations_platform_connector.apis.Employees.sync') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='Some of the parameters are wrong', response='Some of the parameters are wrong')
        auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_credentials.delete()

    auto_create_netsuite_employees_on_fyle(workspace_id=workspace_id)
