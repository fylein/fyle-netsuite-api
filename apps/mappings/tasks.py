import logging
from datetime import datetime, timezone

from typing import List, Dict
from django_q.models import Schedule

from fyle_accounting_mappings.models import Mapping, ExpenseAttribute, DestinationAttribute,\
    CategoryMapping, EmployeeMapping
from fyle_accounting_mappings.helpers import EmployeesAutoMappingHelper

from fyle_integrations_platform_connector import PlatformConnector
from workers.helpers import RoutingKeyEnum, WorkerActionEnum, publish_to_rabbitmq
from apps.mappings.models import GeneralMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Configuration, Workspace
from apps.tasks.models import Error

from .exceptions import handle_exceptions
from fyle.platform.exceptions import (
    InternalServerError,
    InvalidTokenError as FyleInvalidTokenError
)

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def get_mapped_attributes_ids(source_attribute_type: str, destination_attribute_type: str, errored_attribute_ids: List[int]):

    mapped_attribute_ids = []

    if source_attribute_type == "TAX_GROUP":
        mapped_attribute_ids: List[int] = Mapping.objects.filter(
            source_id__in=errored_attribute_ids
        ).values_list('source_id', flat=True)

    elif source_attribute_type == "EMPLOYEE":
        params = {
            'source_employee_id__in': errored_attribute_ids,
        }

        if destination_attribute_type == "EMPLOYEE":
            params['destination_employee_id__isnull'] = False
        else:
            params['destination_vendor_id__isnull'] = False
        mapped_attribute_ids: List[int] = EmployeeMapping.objects.filter(
            **params
        ).values_list('source_employee_id', flat=True)

    elif source_attribute_type == "CATEGORY":
        params = {
            'source_category_id__in': errored_attribute_ids,
        }

        if destination_attribute_type == 'EXPENSE_TYPE':
            params['destination_expense_head_id__isnull'] = False
        else:
            params['destination_account_id__isnull'] =  False

        mapped_attribute_ids: List[int] = CategoryMapping.objects.filter(
            **params
        ).values_list('source_category_id', flat=True)

    return mapped_attribute_ids


def resolve_expense_attribute_errors(
    source_attribute_type: str, workspace_id: int, destination_attribute_type: str = None):
    """
    Resolve Expense Attribute Errors
    :return: None
    """
    errored_attribute_ids: List[int] = Error.objects.filter(
        is_resolved=False,
        workspace_id=workspace_id,
        type='{}_MAPPING'.format(source_attribute_type)
    ).values_list('expense_attribute_id', flat=True)

    if errored_attribute_ids:
        mapped_attribute_ids = get_mapped_attributes_ids(source_attribute_type, destination_attribute_type, errored_attribute_ids)

        if mapped_attribute_ids:
            Error.objects.filter(expense_attribute_id__in=mapped_attribute_ids).update(is_resolved=True, updated_at=datetime.now(timezone.utc))


def remove_duplicates(ns_attributes: List[DestinationAttribute]):
    unique_attributes = []

    attribute_values = []

    for attribute in ns_attributes:
        if attribute.value.lower() not in attribute_values:
            unique_attributes.append(attribute)
            attribute_values.append(attribute.value.lower())

    return unique_attributes


def async_auto_map_employees(workspace_id: int):
    """
    Trigger run_async_auto_map_employees via RabbitMQ
    :param workspace_id: Workspace Id
    :return: None
    """
    payload = {
        'workspace_id': workspace_id,
        'action': WorkerActionEnum.AUTO_MAP_EMPLOYEES.value,
        'data': {
            'workspace_id': workspace_id
        }
    }
    publish_to_rabbitmq(payload=payload, routing_key=RoutingKeyEnum.IMPORT.value)


@handle_exceptions(task_name='Auto Map Employees')
def run_async_auto_map_employees(workspace_id: int):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    employee_mapping_preference = configuration.auto_map_employees
    destination_type = configuration.employee_field_mapping

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    try:
        netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id)
    except NetSuiteCredentials.DoesNotExist:
        return
        
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    platform.employees.sync()
    if destination_type == 'EMPLOYEE':
        netsuite_connection.sync_employees()
    else:
        netsuite_connection.sync_vendors()

    EmployeesAutoMappingHelper(workspace_id, destination_type, employee_mapping_preference).reimburse_mapping()
    resolve_expense_attribute_errors(
        source_attribute_type="EMPLOYEE",
        workspace_id=workspace_id,
        destination_attribute_type=destination_type,
        )


def schedule_auto_map_employees(employee_mapping_preference: str, workspace_id: int):
    if employee_mapping_preference:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.async_auto_map_employees',
            cluster='import',
            args='{0}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.async_auto_map_employees',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def async_auto_map_ccc_account(workspace_id: int):
    """
    Trigger run_async_auto_map_ccc_account via RabbitMQ
    :param workspace_id: Workspace Id
    :return: None
    """
    payload = {
        'workspace_id': workspace_id,
        'action': WorkerActionEnum.AUTO_MAP_CCC_ACCOUNT.value,
        'data': {
            'workspace_id': workspace_id
        }
    }
    publish_to_rabbitmq(payload=payload, routing_key=RoutingKeyEnum.IMPORT.value)


@handle_exceptions(task_name='Auto Map CCC Account')
def run_async_auto_map_ccc_account(workspace_id: int):
    general_mappings = GeneralMapping.objects.get(workspace_id=workspace_id)
    default_ccc_account_id = general_mappings.default_ccc_account_id

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    try:
        platform = PlatformConnector(fyle_credentials=fyle_credentials)
        platform.employees.sync()
        EmployeesAutoMappingHelper(workspace_id, 'CREDIT_CARD_ACCOUNT').ccc_mapping(default_ccc_account_id)
    except FyleInvalidTokenError:
        logger.info('Invalid Token for fyle in workspace - %s', workspace_id)
    except InternalServerError:
        logger.info('Fyle Internal Server Error in workspace - %s', workspace_id)


def schedule_auto_map_ccc_employees(workspace_id: int):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    if configuration.auto_map_employees and configuration.corporate_credit_card_expenses_object:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.async_auto_map_ccc_account',
            cluster='import',
            args='{0}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.async_auto_map_ccc_account',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def sync_netsuite_attribute(netsuite_attribute_type: str, workspace_id: int):
    try:
        ns_credentials: NetSuiteCredentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id)
    except NetSuiteCredentials.DoesNotExist:
        return

    ns_connection = NetSuiteConnector(
        netsuite_credentials=ns_credentials,
        workspace_id=workspace_id
    )

    if netsuite_attribute_type == 'EMPLOYEE':
        ns_connection.sync_employees()

    else:
        ns_connection.sync_custom_segments()


def create_fyle_department_payload(department_name: str, parent_department: str, existing_departments: Dict):
    """
    Search and create Fyle Departments Payload from NetSuite Objects if not already present or disabled on Fyle
    :param department_name: Department name
    :param parent_department: Parent Department
    :param existing_departments: Existing Fyle Departments
    :return: Fyle Departments Payload
    """
    departments_payload = []

    department = department_name
    if parent_department:
        department = '{} / {}'.format(parent_department, department_name)

    if department in existing_departments.keys():
        if not existing_departments[department]['is_enabled']:
            if parent_department:
                departments_payload.append({
                    'name': parent_department,
                    'id': existing_departments[department]['id'],
                    'sub_department': department_name,
                    'is_enabled': True,
                    'display_name': department
                })
            else:
                departments_payload.append({
                    'name': department_name,
                    'id': existing_departments[department]['id'],
                    'is_enabled': True,
                    'display_name': department
                })
    else:
        if parent_department:
            departments_payload.append({
                'name': parent_department,
                'sub_department': department_name,
                'display_name': department
            })
        else:
            departments_payload.append({
                'name': department_name,
                'display_name': department
            })

    logger.info("| Importing Departments to Fyle | Content: {{Fyle Payload count: {}}}".format(len(departments_payload)))
    return departments_payload


def create_fyle_employee_payload(platform_connection: PlatformConnector, employees: List[DestinationAttribute], workspace_id: int):
    """
    Create Fyle Employee, Approver, Departments Payload from NetSuite Objects
    :param platform_connection: Platform Connector
    :param employees: NetSuite Employees Objects
    :return: Fyle Employee, Approver, Departments Payload
    """
    employee_payload: List[Dict] = []
    employee_emails: List[str] = []
    approver_emails: List[str] = []
    employee_approver_payload: List[Dict] = []
    department_payload: List[Dict] = []

    """
    Get all departments and create department mapping dictionary
    """
    existing_departments: Dict = {}
    departments_generator = platform_connection.connection.v1.admin.departments.list_all(query_params={
        'order': 'id.desc'
    })
    for response in departments_generator:
        if response.get('data'):
            for department in response['data']:
                existing_departments[department['display_name']] = {
                    'id': department['id'],
                    'is_enabled': department['is_enabled']
                }

    for employee in employees:
        if employee.detail['department_name']:
            department = create_fyle_department_payload(employee.detail['department_name'], employee.detail['parent_department'], existing_departments)
            if department:
                if not list(filter(
                    lambda dept: dept['display_name'] == department[0]['display_name'], department_payload)):   #check if department is already added to department_payload
                    department_payload.extend(department)

        if employee.detail['email']:
            update_create_employee = {
                'user_email': employee.detail['email'],
                'user_full_name': employee.detail['full_name'],
                'code': employee.destination_id,
                'department_name': employee.detail['department_name'] if employee.detail['department_name'] else '',
                'is_enabled': employee.active,
                'joined_at': employee.detail['joined_at'],
                'location': employee.detail['location_name'] if employee.detail['location_name'] else '',
                'title': employee.detail['title'] if employee.detail['title'] else '',
                'mobile': employee.detail['mobile'] if employee.detail['mobile'] else None
            }

            if employee.detail['parent_department']:
                update_create_employee['department_name'] = employee.detail['parent_department']
                update_create_employee['sub_department'] = employee.detail['department_name'] if employee.detail['department_name'] else ''

            employee_payload.append(update_create_employee)
            employee_emails.append(employee.detail['email'])

            if employee.detail['approver_emails']:
                employee_approver_payload.append({
                    'user_email': employee.detail['email'],
                    'approver_emails': employee.detail['approver_emails']
                })
                approver_emails.extend(employee.detail['approver_emails'])

    existing_approver_emails = ExpenseAttribute.objects.filter(
        workspace_id=workspace_id, attribute_type='EMPLOYEE', value__in=approver_emails
    ).values_list('value', flat=True)

    # Remove from approvers who are not a part of the employee create list or already existing employees
    employee_approver_payload = list(filter(
        lambda employee_approver: set(
            employee_approver['approver_emails']
        ).issubset(employee_emails) or set(
            employee_approver['approver_emails']
        ).issubset(existing_approver_emails),
        employee_approver_payload
    ))

    logger.info("| Importing Employees to Fyle | Content: {{Fyle Employee Payload count: {} Employee Approver Payload count: {} Department Payload count: {}}}".format(len(employee_payload), len(employee_approver_payload), len(department_payload)))
    return employee_payload, employee_approver_payload, department_payload


def post_employees(platform_connection: PlatformConnector, workspace_id: int):
    """
    Post Employees and Departments to Fyle
    :param platform_connection: Platform Connector
    :param workspace_id: Workspace ID
    """

    workspace = Workspace.objects.get(id=workspace_id)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='EMPLOYEE',
        workspace_id=workspace_id,
        updated_at__gte=workspace.employee_exported_at,
        detail__allow_access_to_fyle=True
    ).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_employee_payload, employee_approver_payload, fyle_department_payload = create_fyle_employee_payload(
        platform_connection, netsuite_attributes, workspace_id
    )

    if fyle_department_payload:
        for department in fyle_department_payload:
            platform_connection.departments.post(department)

    if fyle_employee_payload:
        platform_connection.connection.v1.admin.employees.invite_bulk({'data': fyle_employee_payload})

        workspace.employee_exported_at = datetime.now()
        workspace.save()

    if employee_approver_payload:
        platform_connection.connection.v1.admin.employees.invite_bulk({'data': employee_approver_payload})

        workspace.employee_exported_at = datetime.now()
        workspace.save()

    platform_connection.employees.sync()


def auto_create_netsuite_employees_on_fyle(workspace_id):
    """
    Trigger run_auto_create_netsuite_employees_on_fyle via RabbitMQ
    :param workspace_id: Workspace Id
    :return: None
    """
    payload = {
        'workspace_id': workspace_id,
        'action': WorkerActionEnum.AUTO_CREATE_NETSUITE_EMPLOYEES_ON_FYLE.value,
        'data': {
            'workspace_id': workspace_id
        }
    }
    publish_to_rabbitmq(payload=payload, routing_key=RoutingKeyEnum.IMPORT.value)


@handle_exceptions(task_name='Import NetSuite Employees to Fyle')
def run_auto_create_netsuite_employees_on_fyle(workspace_id):
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

    platform_connection = PlatformConnector(fyle_credentials)

    platform_connection.employees.sync()

    sync_netsuite_attribute('EMPLOYEE', workspace_id)
    post_employees(platform_connection, workspace_id)


def schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees, workspace_id):
    if import_netsuite_employees:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
            cluster='import',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
            args='{}'.format(workspace_id),
        ).first()

        if schedule:
            schedule.delete()


def check_and_create_ccc_mappings(workspace_id: int) -> None:
    """
    Check and Create CCC Mappings
    :param workspace_id: Workspace Id
    :return: None
    """
    configuration = Configuration.objects.filter(workspace_id=workspace_id).first()
    if configuration and (
        configuration.reimbursable_expenses_object == 'EXPENSE REPORT'
        and configuration.corporate_credit_card_expenses_object in ('BILL', 'CREDIT CARD CHARGE', 'JOURNAL ENTRY')
    ):
        logger.info('Creating CCC Mappings for workspace_id - %s', workspace_id)
        CategoryMapping.bulk_create_ccc_category_mappings(workspace_id)
