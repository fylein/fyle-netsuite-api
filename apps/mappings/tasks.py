import logging
import traceback
from datetime import datetime, timedelta
from django.db.models import Q

from typing import List, Dict
from dateutil import parser
from django_q.models import Schedule

from fyle.platform.exceptions import WrongParamsError

from fyle_accounting_mappings.models import Mapping, MappingSetting, ExpenseAttribute, DestinationAttribute,\
    CategoryMapping
from fyle_accounting_mappings.helpers import EmployeesAutoMappingHelper

from fyle_integrations_platform_connector import PlatformConnector
from apps.mappings.models import GeneralMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Configuration, Workspace


from .constants import FYLE_EXPENSE_SYSTEM_FIELDS

logger = logging.getLogger(__name__)
logger.level = logging.INFO

def remove_duplicates(ns_attributes: List[DestinationAttribute]):
    unique_attributes = []

    attribute_values = []

    for attribute in ns_attributes:
        if attribute.value.lower() not in attribute_values:
            unique_attributes.append(attribute)
            attribute_values.append(attribute.value.lower())

    return unique_attributes


def get_all_categories_from_fyle(platform: PlatformConnector):

    categories_generator = platform.connection.v1beta.admin.categories.list_all(query_params={
            'order': 'id.desc'
        })

    categories = []

    for response in categories_generator:
        if response.get('data'):
            categories.extend(response['data'])

    category_name_map = {}
    for category in categories:
        if category['sub_category'] and category['name'] != category['sub_category']:
            category['name'] = '{0} / {1}'.format(category['name'], category['sub_category'])
        category_name_map[category['name'].lower()] = category

    return category_name_map


def create_fyle_categories_payload(categories: List[DestinationAttribute], category_map: Dict):
    """
    Create Fyle Categories Payload from NetSuite Customer / Categories
    :param workspace_id: Workspace integer id
    :param categories: NetSuite Categories
    :return: Fyle Categories Payload
    """
    payload = []

    for category in categories:
        if category.value.lower() not in category_map:
            payload.append({
                'name': category.value,
                'code': category.destination_id,
                'is_enabled': True if category.active is None else category.active,
                'restricted_project_ids': None
            })
        else:
            payload.append({
                'id': category_map[category.value.lower()]['id'],
                'name': category.value,
                'code': category.destination_id,
                'is_enabled': category_map[category.value.lower()]['is_enabled'],
                'restricted_project_ids': None
            })

    return payload


def sync_expense_categories_and_accounts(reimbursable_expenses_object: str, corporate_credit_card_expenses_object: str,
    netsuite_connection: NetSuiteConnector):
    if reimbursable_expenses_object == 'EXPENSE REPORT' or corporate_credit_card_expenses_object == 'EXPENSE REPORT':
        netsuite_connection.sync_expense_categories()

    if reimbursable_expenses_object in ('BILL', 'JOURNAL ENTRY') or \
        corporate_credit_card_expenses_object in ('BILL', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE'):
        netsuite_connection.sync_accounts()


def upload_categories_to_fyle(workspace_id: int, reimbursable_expenses_object: str,
    corporate_credit_card_expenses_object: str):
    """
    Upload categories to Fyle
    """
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)
    netsuite_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    
    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    category_map = get_all_categories_from_fyle(platform=platform)

    netsuite_connection = NetSuiteConnector(
        netsuite_credentials=netsuite_credentials,
        workspace_id=workspace_id
    )

    platform.categories.sync()

    sync_expense_categories_and_accounts(
        reimbursable_expenses_object, corporate_credit_card_expenses_object, netsuite_connection)

    if reimbursable_expenses_object == 'EXPENSE REPORT':
        netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
            workspace_id=workspace_id, attribute_type='EXPENSE_CATEGORY'
        )
    else:
        netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
            workspace_id=workspace_id, attribute_type='ACCOUNT'
        )

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload: List[Dict] = create_fyle_categories_payload(netsuite_attributes, category_map)

    if fyle_payload:
        platform.categories.post_bulk(fyle_payload)
        platform.categories.sync()

    return netsuite_attributes


def bulk_create_ccc_category_mappings(workspace_id: int):
    """
    Create Category Mappings for CCC Expenses
    :param workspace_id: Workspace Id
    """
    # Filtering unmapped ccc category mappings
    category_mappings = CategoryMapping.objects.filter(
        workspace_id=workspace_id,
        destination_account__isnull=True
    ).all()

    account_internal_ids = []

    for category_mapping in category_mappings:
        if category_mapping.destination_expense_head.detail and \
            'account_internal_id' in category_mapping.destination_expense_head.detail and \
                category_mapping.destination_expense_head.detail['account_internal_id']:
            account_internal_ids.append(category_mapping.destination_expense_head.detail['account_internal_id'])

    # Retreiving accounts for creating ccc mapping
    destination_attributes = DestinationAttribute.objects.filter(
        workspace_id=workspace_id,
        attribute_type='ACCOUNT',
        destination_id__in=account_internal_ids
    ).values('id', 'destination_id')

    destination_id_pk_map = {}
    for attribute in destination_attributes:
        destination_id_pk_map[attribute['destination_id'].lower()] = attribute['id']

    mapping_updation_batch = []

    for category_mapping in category_mappings:
        ccc_account_id = destination_id_pk_map[category_mapping.destination_expense_head.detail['account_internal_id'].lower()]
        mapping_updation_batch.append(
            CategoryMapping(
                id=category_mapping.id,
                source_category_id=category_mapping.source_category.id,
                destination_account_id=ccc_account_id
            )
        )

    if mapping_updation_batch:
        CategoryMapping.objects.bulk_update(
            mapping_updation_batch, fields=['destination_account'], batch_size=50
        )


def construct_filter_based_on_destination(reimbursable_destination_type: str):
    """
    Construct Filter Based on Destination
    :param reimbursable_destination_type: Reimbusable Destination Type
    :return: Filter
    """
    filters = {}
    if reimbursable_destination_type == 'EXPENSE_CATEGORY':
        filters['destination_expense_head__isnull'] = True
    elif reimbursable_destination_type == 'ACCOUNT':
        filters['destination_account__isnull'] = True

    return filters


def filter_unmapped_destinations(reimbursable_destination_type: str,
    destination_attributes: List[DestinationAttribute]):
    """
    Filter unmapped destinations based on workspace
    :param reimbursable_destination_type: Reimbusable destination type
    :param destination_attributes: List of destination attributes
    """
    filters = construct_filter_based_on_destination(reimbursable_destination_type)

    destination_attribute_ids = [destination_attribute.id for destination_attribute in destination_attributes]

    # Filtering unmapped categories
    destination_attributes = DestinationAttribute.objects.filter(
        pk__in=destination_attribute_ids,
        **filters
    ).values('id', 'value')

    return destination_attributes


def bulk_create_update_category_mappings(mapping_creation_batch: List[CategoryMapping]):
    """
    Bulk Create and Update Category Mappings
    :param mapping_creation_batch: List of Category Mappings
    """
    expense_attributes_to_be_updated = []
    created_mappings = []

    if mapping_creation_batch:
        created_mappings = CategoryMapping.objects.bulk_create(mapping_creation_batch, batch_size=50)

    for category_mapping in created_mappings:
        expense_attributes_to_be_updated.append(
            ExpenseAttribute(
                id=category_mapping.source_category.id,
                auto_mapped=True
            )
        )

    if expense_attributes_to_be_updated:
        ExpenseAttribute.objects.bulk_update(
            expense_attributes_to_be_updated, fields=['auto_mapped'], batch_size=50)


def create_category_mappings(destination_attributes: List[DestinationAttribute],
    reimbursable_destination_type: str, workspace_id: int):
    """
    Bulk create category mappings
    :param destination_attributes: Desitination Attributes
    :param reimbursable_destination_type: Reimbursable Destination Type
    :param workspace_id: Workspace ID
    :return: None
    """
    destination_attributes = filter_unmapped_destinations(reimbursable_destination_type, destination_attributes)

    attribute_value_list = []
    attribute_value_list = [destination_attribute['value'] for destination_attribute in destination_attributes]

    # Filtering unmapped categories
    source_attributes = ExpenseAttribute.objects.filter(
        workspace_id=workspace_id,
        attribute_type='CATEGORY',
        value__in=attribute_value_list,
        categorymapping__source_category__isnull=True
    ).values('id', 'value')

    source_attributes_id_map = {source_attribute['value'].lower(): source_attribute['id'] \
        for source_attribute in source_attributes}

    mapping_creation_batch = []

    for destination_attribute in destination_attributes:
        if destination_attribute['value'].lower() in source_attributes_id_map:
            destination = {}
            if reimbursable_destination_type == 'EXPENSE_CATEGORY':
                destination['destination_expense_head_id'] = destination_attribute['id']
            elif reimbursable_destination_type == 'ACCOUNT':
                destination['destination_account_id'] = destination_attribute['id']

            mapping_creation_batch.append(
                CategoryMapping(
                    source_category_id=source_attributes_id_map[destination_attribute['value'].lower()],
                    workspace_id=workspace_id,
                    **destination
                )
            )

    bulk_create_update_category_mappings(mapping_creation_batch)


def auto_create_tax_group_mappings(workspace_id):
    """
    Create Tax Groups Mappings
    :return: None
    """
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

        fyle_connection = PlatformConnector(fyle_credentials)

        fyle_connection.tax_groups.sync()

        mapping_setting = MappingSetting.objects.get(
            source_field='TAX_GROUP', workspace_id=workspace_id
        )

        sync_netsuite_attribute(mapping_setting.destination_field, workspace_id)
        post_tax_groups(fyle_connection, workspace_id)

    except WrongParamsError as exception:
        logger.error(
            'Error while creating taxgroups workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )

    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while creating taxgroups workspace_id - %s error: %s',
            workspace_id, error
        )

def schedule_tax_groups_creation(import_tax_items, workspace_id):
    if import_tax_items:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_tax_group_mappings',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_tax_group_mappings',
            args='{}'.format(workspace_id),
        ).first()

        if schedule:
            schedule.delete()

def post_tax_groups(platform_connection: PlatformConnector, workspace_id: int):
    existing_tax_items_name = ExpenseAttribute.objects.filter(
        attribute_type='TAX_GROUP', workspace_id=workspace_id).values_list('value', flat=True)

    netsuite_attributes = DestinationAttribute.objects.filter(
        attribute_type='TAX_ITEM', workspace_id=workspace_id).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload: List[Dict] = create_fyle_tax_group_payload(
        netsuite_attributes, existing_tax_items_name)
    
    if fyle_payload:
        platform_connection.tax_groups.post_bulk(fyle_payload)

    platform_connection.tax_groups.sync()
    Mapping.bulk_create_mappings(netsuite_attributes, 'TAX_GROUP', 'TAX_ITEM', workspace_id)

def auto_create_category_mappings(workspace_id):
    """
    Create Category Mappings
    :return: mappings
    """
    configuration: Configuration = Configuration.objects.get(workspace_id=workspace_id)

    reimbursable_expenses_object = configuration.reimbursable_expenses_object
    corporate_credit_card_expenses_object = configuration.corporate_credit_card_expenses_object

    if reimbursable_expenses_object == 'EXPENSE REPORT':
        reimbursable_destination_type = 'EXPENSE_CATEGORY'
    else:
        reimbursable_destination_type = 'ACCOUNT'

    try:
        fyle_categories = upload_categories_to_fyle(
            workspace_id=workspace_id, reimbursable_expenses_object=reimbursable_expenses_object,
            corporate_credit_card_expenses_object=corporate_credit_card_expenses_object)

        create_category_mappings(fyle_categories, reimbursable_destination_type, workspace_id)

        if reimbursable_expenses_object == 'EXPENSE REPORT' and \
            corporate_credit_card_expenses_object in ('BILL', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE'):
            bulk_create_ccc_category_mappings(workspace_id)

        return []
    except WrongParamsError as exception:
        logger.error(
            'Error while creating categories workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )
    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while creating categories workspace_id - %s error: %s',
            workspace_id, error
        )


def schedule_categories_creation(import_categories, workspace_id):
    if import_categories:
        start_datetime = datetime.now()
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_category_mappings',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': start_datetime
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_category_mappings',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()

def create_fyle_tax_group_payload(netsuite_attributes: List[DestinationAttribute], existing_fyle_tax_groups: list):
    """
    Create Fyle Tax Group Payload from Netsuite Objects
    :param existing_fyle_tax_groups: Existing tax group names
    :param netsuite_attributes: Netsuite Objects Objects
    :return: Fyle Tax Group Payload
    """
    fyle_tax_group_payload = []
    for netsuite_attribute in netsuite_attributes:
        if netsuite_attribute.value not in existing_fyle_tax_groups:
            fyle_tax_group_payload.append(
                {
                    'name': netsuite_attribute.value,
                    'is_enabled': True,
                    'percentage': round((netsuite_attribute.detail['tax_rate']/100), 2)
                }
            )
    return fyle_tax_group_payload

def disable_or_enable_expense_attributes(source_field, destination_field, workspace_id):

    # Get All the inactive destination attribute ids
    destination_attribute_ids = DestinationAttribute.objects.filter(
		attribute_type=destination_field, 
		mapping__isnull=False,
		mapping__destination_type=destination_field,
		active=False,
		workspace_id=workspace_id
	).values_list('id', flat=True)

    # Get all the expense attributes that are mapped to these destination_attribute_ids
    expense_attributes_to_disable = ExpenseAttribute.objects.filter(
		attribute_type=source_field, 
		mapping__destination_id__in=destination_attribute_ids,
		active=True
	)

    expense_attributes_to_enable = ExpenseAttribute.objects.filter(
        ~Q(mapping__destination_id__in=destination_attribute_ids),
        mapping__isnull=False,
        mapping__source_type=source_field,
        attribute_type=source_field,
        active=False,
        workspace_id=workspace_id
	)

    # if there are any expense attributes present, set active to False
    if expense_attributes_to_disable or expense_attributes_to_enable:
        expense_attributes_ids = [expense_attribute.id for expense_attribute in expense_attributes_to_disable]
        expense_attributes_ids = expense_attributes_ids + [expense_attribute.id for expense_attribute in expense_attributes_to_enable]
        expense_attributes_to_disable.update(active=False)
        expense_attributes_to_enable.update(active=True)
        return expense_attributes_ids

def create_fyle_projects_payload(projects: List[DestinationAttribute], existing_project_names: list,
                                     updated_projects: List[ExpenseAttribute] = None):
    """
    Create Fyle Projects Payload from NetSuite Projects
    :param existing_project_names: Existing Projects in Fyle
    :param projects: NetSuite Projects
    :return: Fyle Projects Payload
    """
    payload = []
    if updated_projects:
        for project in updated_projects:
            destination_id_of_project = project.mapping.first().destination.destination_id
            payload.append({
                'id': project.source_id,
                'name': project.value,
                'code': destination_id_of_project,
                'description': 'Project - {0}, Id - {1}'.format(
                    project.value,
                    destination_id_of_project
                ),
                'is_enabled': project.active
            })
    else:
        for project in projects:
            if project.value not in existing_project_names:
                payload.append({
                    'name': project.value,
                    'code': project.destination_id,
                    'description': 'Project - {0}, Id - {1}'.format(
                        project.value,
                        project.destination_id
                    ),
                    'is_enabled': True if project.active else project.active
                })

    return payload


def post_projects_in_batches(platform: PlatformConnector, workspace_id: int, destination_field: str):
    existing_project_names = ExpenseAttribute.objects.filter(
        attribute_type='PROJECT', workspace_id=workspace_id).values_list('value', flat=True)
    ns_attributes_count = DestinationAttribute.objects.filter(
        attribute_type=destination_field, workspace_id=workspace_id).count()
    page_size = 200

    for offset in range(0, ns_attributes_count, page_size):
        limit = offset + page_size
        paginated_ns_attributes = DestinationAttribute.objects.filter(
            attribute_type=destination_field, workspace_id=workspace_id).order_by('value', 'id')[offset:limit]

        paginated_ns_attributes = remove_duplicates(paginated_ns_attributes)

        fyle_payload: List[Dict] = create_fyle_projects_payload(
            paginated_ns_attributes, existing_project_names)
        if fyle_payload:
            platform.projects.post_bulk(fyle_payload)
            platform.projects.sync()

        Mapping.bulk_create_mappings(paginated_ns_attributes, 'PROJECT', destination_field, workspace_id)
    
    if destination_field == 'PROJECT':
        project_ids_to_be_changed = disable_or_enable_expense_attributes('PROJECT', 'PROJECT', workspace_id)
        if project_ids_to_be_changed:
            expense_attributes = ExpenseAttribute.objects.filter(id__in=project_ids_to_be_changed)
            fyle_payload: List[Dict] = create_fyle_projects_payload(projects=[], existing_project_names=[], updated_projects=expense_attributes)
            platform.projects.post_bulk(fyle_payload)
            platform.projects.sync()


def auto_create_project_mappings(workspace_id):
    """
    Create Project Mappings
    """
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

        platform = PlatformConnector(fyle_credentials=fyle_credentials)
        platform.projects.sync()

        mapping_setting = MappingSetting.objects.get(
            source_field='PROJECT', workspace_id=workspace_id
        )

        sync_netsuite_attribute(mapping_setting.destination_field, workspace_id)

        post_projects_in_batches(platform, workspace_id, mapping_setting.destination_field)

    except WrongParamsError as exception:
        logger.error(
            'Error while creating projects workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )

    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while creating projects workspace_id - %s error: %s',
            workspace_id, error
        )


def schedule_projects_creation(import_to_fyle, workspace_id):
    if import_to_fyle:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_project_mappings',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_project_mappings',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def async_auto_map_employees(workspace_id: int):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    employee_mapping_preference = configuration.auto_map_employees
    destination_type = configuration.employee_field_mapping

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    platform.employees.sync()
    if destination_type == 'EMPLOYEE':
        netsuite_connection.sync_employees()
    else:
        netsuite_connection.sync_vendors()

    EmployeesAutoMappingHelper(workspace_id, destination_type, employee_mapping_preference).reimburse_mapping()


def schedule_auto_map_employees(employee_mapping_preference: str, workspace_id: int):
    if employee_mapping_preference:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.async_auto_map_employees',
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
    general_mappings = GeneralMapping.objects.get(workspace_id=workspace_id)
    default_ccc_account_id = general_mappings.default_ccc_account_id

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials=fyle_credentials)
    platform.employees.sync()

    EmployeesAutoMappingHelper(workspace_id, 'CREDIT_CARD_ACCOUNT').ccc_mapping(default_ccc_account_id)


def schedule_auto_map_ccc_employees(workspace_id: int):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    if configuration.auto_map_employees and configuration.corporate_credit_card_expenses_object:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.async_auto_map_ccc_account',
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
    ns_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    ns_connection = NetSuiteConnector(
        netsuite_credentials=ns_credentials,
        workspace_id=workspace_id
    )

    if netsuite_attribute_type == 'LOCATION':
        ns_connection.sync_locations()

    elif netsuite_attribute_type == 'PROJECT':
        ns_connection.sync_projects()
        ns_connection.sync_customers()

    elif netsuite_attribute_type == 'DEPARTMENT':
        ns_connection.sync_departments()

    elif netsuite_attribute_type == 'CLASS':
        ns_connection.sync_classifications()

    elif netsuite_attribute_type == 'TAX_ITEM':
        ns_connection.sync_tax_items()

    elif netsuite_attribute_type == 'VENDOR':
        ns_connection.sync_vendors()

    elif netsuite_attribute_type == 'EMPLOYEE':
        ns_connection.sync_employees()

    else:
        ns_connection.sync_custom_segments()


def create_fyle_cost_centers_payload(netsuite_attributes: List[DestinationAttribute], existing_fyle_cost_centers: list):
    """
    Create Fyle Cost Centers Payload from NetSuite Objects
    :param existing_fyle_cost_centers: Existing cost center names
    :param netsuite_attributes: NetSuite Objects
    :return: Fyle Cost Centers Payload
    """
    fyle_cost_centers_payload = []

    for netsuite_attribute in netsuite_attributes:
        if netsuite_attribute.value not in existing_fyle_cost_centers:
            fyle_cost_centers_payload.append({
                'name': netsuite_attribute.value,
                'is_enabled': True if netsuite_attribute.active is None else netsuite_attribute.active,
                'description': 'Cost Center - {0}, Id - {1}'.format(
                    netsuite_attribute.value,
                    netsuite_attribute.destination_id
                )
            })

    return fyle_cost_centers_payload


def post_cost_centers_in_batches(platform: PlatformConnector, workspace_id: int, netsuite_attribute_type: str):
    existing_cost_center_names = ExpenseAttribute.objects.filter(
        attribute_type='COST_CENTER', workspace_id=workspace_id).values_list('value', flat=True)

    ns_attributes_count = DestinationAttribute.objects.filter(
        attribute_type=netsuite_attribute_type, workspace_id=workspace_id).count()

    page_size = 200

    for offset in range(0, ns_attributes_count, page_size):
        limit = offset + page_size
        paginated_ns_attributes = DestinationAttribute.objects.filter(
            attribute_type=netsuite_attribute_type, workspace_id=workspace_id).order_by('value', 'id')[offset:limit]

        paginated_ns_attributes = remove_duplicates(paginated_ns_attributes)

        fyle_payload: List[Dict] = create_fyle_cost_centers_payload(
            paginated_ns_attributes, existing_cost_center_names)

        if fyle_payload:
            platform.cost_centers.post_bulk(fyle_payload)
            platform.cost_centers.sync()

        Mapping.bulk_create_mappings(paginated_ns_attributes, 'COST_CENTER', netsuite_attribute_type, workspace_id)


def auto_create_cost_center_mappings(workspace_id):
    """
    Create Cost Center Mappings
    """
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

        platform = PlatformConnector(fyle_credentials=fyle_credentials)

        mapping_setting = MappingSetting.objects.get(
            source_field='COST_CENTER', import_to_fyle=True, workspace_id=workspace_id
        )

        platform.cost_centers.sync()

        sync_netsuite_attribute(mapping_setting.destination_field, workspace_id)

        post_cost_centers_in_batches(platform, workspace_id, mapping_setting.destination_field)

    except WrongParamsError as exception:
        logger.error(
            'Error while creating cost centers workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )

    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while creating cost centers workspace_id - %s error: %s',
            workspace_id, error
        )


def schedule_cost_centers_creation(import_to_fyle, workspace_id):
    if import_to_fyle:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_cost_center_mappings',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_cost_center_mappings',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()


def create_fyle_expense_custom_field_payload(netsuite_attributes: List[DestinationAttribute], workspace_id: int,
                                             fyle_attribute: str, platform: PlatformConnector):
    """
    Create Fyle Expense Custom Field Payload from NetSuite Objects
    :param workspace_id: Workspace ID
    :param netsuite_attributes: NetSuite Objects
    :param fyle_attribute: Fyle Attribute
    :return: Fyle Expense Custom Field Payload
    """
    fyle_expense_custom_field_options = []

    [fyle_expense_custom_field_options.append(netsuite_attribute.value) for netsuite_attribute in netsuite_attributes]

    if fyle_attribute.lower() not in FYLE_EXPENSE_SYSTEM_FIELDS:
        existing_attribute = ExpenseAttribute.objects.filter(
            attribute_type=fyle_attribute, workspace_id=workspace_id).values_list('detail', flat=True).first()

        custom_field_id = None
        if existing_attribute is not None:
            custom_field_id = existing_attribute['custom_field_id']

        fyle_attribute = fyle_attribute.replace('_', ' ').title()

        expense_custom_field_payload = {
            'field_name': fyle_attribute,
            'type': 'SELECT',
            'is_enabled': True,
            'is_mandatory': False,
            'placeholder': 'Select {0}'.format(fyle_attribute),
            'options': fyle_expense_custom_field_options,
            'code': None
        }

        if custom_field_id:
            expense_field = platform.expense_custom_fields.get_by_id(custom_field_id)
            expense_custom_field_payload['id'] = custom_field_id
            expense_custom_field_payload['is_mandatory'] = expense_field['is_mandatory']

        return expense_custom_field_payload


def upload_attributes_to_fyle(workspace_id: int, netsuite_attribute_type: str, fyle_attribute_type: str):
    """
    Upload attributes to Fyle
    """
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

    platform = PlatformConnector(fyle_credentials=fyle_credentials)

    netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
        workspace_id=workspace_id, attribute_type=netsuite_attribute_type
    )

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_custom_field_payload = create_fyle_expense_custom_field_payload(
        fyle_attribute=fyle_attribute_type,
        netsuite_attributes=netsuite_attributes,
        workspace_id=workspace_id,
        platform=platform
    )

    if fyle_custom_field_payload:
        platform.expense_custom_fields.post(fyle_custom_field_payload)
        platform.expense_custom_fields.sync()

    return netsuite_attributes


def auto_create_expense_fields_mappings(workspace_id: int, netsuite_attribute_type: str, fyle_attribute_type: str):
    """
    Create Fyle Attributes Mappings
    :return: mappings
    """
    try:
        fyle_attributes = upload_attributes_to_fyle(workspace_id, netsuite_attribute_type, fyle_attribute_type)
        if fyle_attributes:
            Mapping.bulk_create_mappings(fyle_attributes, fyle_attribute_type, netsuite_attribute_type, workspace_id)

    except WrongParamsError as exception:
        logger.error(
            'Error while creating %s workspace_id - %s in Fyle %s %s',
            fyle_attribute_type, workspace_id, exception.message, {'error': exception.response}
        )
    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while creating %s workspace_id - %s error: %s', fyle_attribute_type, workspace_id, error
        )


def async_auto_create_custom_field_mappings(workspace_id):
    mapping_settings = MappingSetting.objects.filter(
        is_custom=True, import_to_fyle=True, workspace_id=workspace_id
    ).all()

    for mapping_setting in mapping_settings:
        if mapping_setting.import_to_fyle:
            sync_netsuite_attribute(mapping_setting.destination_field, workspace_id)
            auto_create_expense_fields_mappings(
                workspace_id, mapping_setting.destination_field, mapping_setting.source_field
            )


def schedule_fyle_attributes_creation(workspace_id: int):
    mapping_settings = MappingSetting.objects.filter(
        is_custom=True, import_to_fyle=True, workspace_id=workspace_id
    ).all()
    if mapping_settings:
        schedule, _ = Schedule.objects.get_or_create(
            func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
            args='{0}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now() + timedelta(hours=24)
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.async_auto_create_custom_field_mappings',
            args='{0}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()

def create_fyle_merchants_payload(vendors, existing_merchants_name):
    payload: List[str] = []
    for vendor in vendors:
        if vendor.value not in existing_merchants_name:
            payload.append(vendor.value)
    return payload

def post_merchants(platform_connection: PlatformConnector, workspace_id: int, first_run: bool):
    existing_merchants_name = ExpenseAttribute.objects.filter(
        attribute_type='MERCHANT', workspace_id=workspace_id).values_list('value', flat=True)
    
    if first_run:
        netsuite_attributes = DestinationAttribute.objects.filter(
            attribute_type='VENDOR', workspace_id=workspace_id).order_by('value', 'id')
    else:
        merchant = platform_connection.merchants.get()
        merchant_updated_at = parser.isoparse(merchant['updated_at']).strftime('%Y-%m-%d %H:%M:%S.%f')
        netsuite_attributes = DestinationAttribute.objects.filter(
            attribute_type='VENDOR',
            workspace_id=workspace_id,
            updated_at__gte=merchant_updated_at
        ).order_by('value', 'id')

    netsuite_attributes = remove_duplicates(netsuite_attributes)
    fyle_payload: List[str] = create_fyle_merchants_payload(
        netsuite_attributes, existing_merchants_name)

    if fyle_payload:
        platform_connection.merchants.post(fyle_payload)

    platform_connection.merchants.sync(workspace_id)

def auto_create_vendors_as_merchants(workspace_id):
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

        fyle_connection = PlatformConnector(fyle_credentials)

        existing_merchants_name = ExpenseAttribute.objects.filter(attribute_type='MERCHANT', workspace_id=workspace_id)
        
        first_run = False if existing_merchants_name else True

        fyle_connection.merchants.sync(workspace_id)

        sync_netsuite_attribute('VENDOR', workspace_id)
        post_merchants(fyle_connection, workspace_id, first_run)

    except WrongParamsError as exception:
        logger.error(
            'Error while posting vendors as merchants to fyle for workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )

    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while posting vendors as merchants to fyle for workspace_id - %s error: %s',
            workspace_id, error)

def schedule_vendors_as_merchants_creation(import_vendors_as_merchants, workspace_id):
    if import_vendors_as_merchants:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_vendors_as_merchants',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now()
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_vendors_as_merchants',
            args='{}'.format(workspace_id),
        ).first()

        if schedule:
            schedule.delete()


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
    return departments_payload


def create_fyle_employee_payload(platform_connection: PlatformConnector, employees: List[DestinationAttribute]):
    """
    Create Fyle Employee, Approver, Departments Payload from NetSuite Objects
    :param platform_connection: Platform Connector
    :param employees: NetSuite Employees Objects
    :return: Fyle Employee, Approver, Departments Payload
    """
    employee_payload: List[Dict] = []
    employee_approver_payload: List[Dict] = []
    department_payload: List[Dict] = []

    """
    Get all departments and create department mapping dictionary
    """
    existing_departments: Dict = {}
    departments_generator = platform_connection.connection.v1beta.admin.departments.list_all(query_params={
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

            if employee.detail['approver_emails']:
                employee_approver_payload.append({
                    'user_email': employee.detail['email'],
                    'approver_emails': employee.detail['approver_emails']
                })

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
        platform_connection, netsuite_attributes
    )

    if fyle_department_payload:
        for department in fyle_department_payload:
            platform_connection.departments.post(department)

    if fyle_employee_payload:
        platform_connection.connection.v1beta.admin.employees.invite_bulk({'data': fyle_employee_payload})

        workspace.employee_exported_at = datetime.now()
        workspace.save()

    if employee_approver_payload:
        platform_connection.connection.v1beta.admin.employees.invite_bulk({'data': employee_approver_payload})

        workspace.employee_exported_at = datetime.now()
        workspace.save()

    platform_connection.employees.sync()


def auto_create_netsuite_employees_on_fyle(workspace_id):
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

        platform_connection = PlatformConnector(fyle_credentials)

        platform_connection.employees.sync()

        sync_netsuite_attribute('EMPLOYEE', workspace_id)
        post_employees(platform_connection, workspace_id)

    except WrongParamsError as exception:
        logger.error(
            'Error while posting netsuite employees to fyle for workspace_id - %s in Fyle %s %s',
            workspace_id, exception.message, {'error': exception.response}
        )

    except Exception:
        error = traceback.format_exc()
        error = {
            'error': error
        }
        logger.exception(
            'Error while posting netsuite employees to fyle for workspace_id - %s error: %s',
            workspace_id, error)


def schedule_netsuite_employee_creation_on_fyle(import_netsuite_employees, workspace_id):
    if import_netsuite_employees:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_netsuite_employees_on_fyle',
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
