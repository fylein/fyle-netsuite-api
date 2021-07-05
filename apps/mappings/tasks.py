import logging
import traceback
from datetime import datetime, timedelta

from typing import List, Dict

from django_q.models import Schedule
from django.db.models import Q, Count

from fylesdk.exceptions import WrongParamsError

from apps.netsuite.models import CustomSegment
from fyle_accounting_mappings.models import Mapping, MappingSetting, ExpenseAttribute, DestinationAttribute

from apps.fyle.connector import FyleConnector
from apps.mappings.models import GeneralMapping
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Configuration

from .constants import FYLE_EXPENSE_SYSTEM_FIELDS

logger = logging.getLogger(__name__)


def remove_duplicates(ns_attributes: List[DestinationAttribute]):
    unique_attributes = []

    attribute_values = []

    for attribute in ns_attributes:
        if attribute.value not in attribute_values:
            unique_attributes.append(attribute)
            attribute_values.append(attribute.value)

    return unique_attributes


def create_fyle_categories_payload(categories: List[DestinationAttribute], workspace_id: int):
    """
    Create Fyle Categories Payload from NetSuite Customer / Categories
    :param workspace_id: Workspace integer id
    :param categories: NetSuite Categories
    :return: Fyle Categories Payload
    """
    payload = []

    existing_category_names = ExpenseAttribute.objects.filter(
        attribute_type='CATEGORY', workspace_id=workspace_id).values_list('value', flat=True)

    for category in categories:
        if category.value not in existing_category_names:
            payload.append({
                'name': category.value,
                'code': category.destination_id,
                'enabled': category.active
            })

    return payload


def upload_categories_to_fyle(workspace_id, reimbursable_expenses_object):
    """
    Upload categories to Fyle
    """
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)
    netsuite_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

    fyle_connection = FyleConnector(
        refresh_token=fyle_credentials.refresh_token,
        workspace_id=workspace_id
    )

    netsuite_connection = NetSuiteConnector(
        netsuite_credentials=netsuite_credentials,
        workspace_id=workspace_id
    )
    fyle_connection.sync_categories()

    if reimbursable_expenses_object == 'EXPENSE REPORT':
        netsuite_connection.sync_expense_categories()
        netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
            workspace_id=workspace_id, attribute_type='EXPENSE_CATEGORY'
        )
    else:
        netsuite_connection.sync_accounts()
        netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
            workspace_id=workspace_id, attribute_type='ACCOUNT'
        )

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_payload: List[Dict] = create_fyle_categories_payload(netsuite_attributes, workspace_id)

    if fyle_payload:
        fyle_connection.connection.Categories.post(fyle_payload)
        fyle_connection.sync_categories()

    return netsuite_attributes


def create_credit_card_category_mappings(reimbursable_expenses_object,
                                         corporate_credit_card_expenses_object, workspace_id):
    """
    Create credit card mappings
    """
    mapping_batch = []
    category_mappings = Mapping.objects.filter(
        source_id__in=Mapping.objects.filter(
            workspace_id=workspace_id, source_type='CATEGORY'
        ).values('source_id').annotate(
            count=Count('source_id')
        ).filter(count=1).values_list('source_id')
    )

    if reimbursable_expenses_object == 'EXPENSE REPORT' and corporate_credit_card_expenses_object == 'EXPENSE REPORT':
        destination_type = 'CCC_EXPENSE_CATEGORY'
    else:
        destination_type = 'CCC_ACCOUNT'

    destination_values = []
    account_internal_ids = []
    for mapping in category_mappings:
        destination_values.append(mapping.destination.value)
        if mapping.destination.detail and 'account_internal_id' in mapping.destination.detail:
            account_internal_ids.append(mapping.destination.detail['account_internal_id'])

    if reimbursable_expenses_object == 'EXPENSE REPORT' and corporate_credit_card_expenses_object in (
            'BILL', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE'):
        destination_attributes = DestinationAttribute.objects.filter(
            workspace_id=workspace_id,
            attribute_type=destination_type,
            destination_id__in=account_internal_ids
        ).all()
    else:
        destination_attributes = DestinationAttribute.objects.filter(
            workspace_id=workspace_id,
            attribute_type=destination_type,
            value__in=destination_values
        ).all()

    destination_id_map = {}
    for attribute in destination_attributes:
        destination_id_map[attribute.value] = {
            'id': attribute.id,
            'destination_id': attribute.destination_id
        }

    for mapping in category_mappings:
        if reimbursable_expenses_object == 'EXPENSE REPORT':
            if corporate_credit_card_expenses_object == 'EXPENSE REPORT':
                mapping_batch.append(
                    Mapping(
                        source_type='CATEGORY',
                        destination_type=destination_type,
                        source_id=mapping.source.id,
                        destination_id=destination_id_map[mapping.destination.value]['id'],
                        workspace_id=workspace_id
                    )
                )
            elif corporate_credit_card_expenses_object in ('BILL', 'JOURNAL ENTRY', 'CREDIT CARD CHARGE'):
                for value in destination_id_map:
                    if destination_id_map[value]['destination_id'] == mapping.destination.detail['account_internal_id']:
                        mapping_batch.append(
                            Mapping(
                                source_type='CATEGORY',
                                destination_type=destination_type,
                                source_id=mapping.source.id,
                                destination_id=destination_id_map[value]['id'],
                                workspace_id=workspace_id
                            )
                        )
                        break

        elif reimbursable_expenses_object in ('BILL', 'JOURNAL ENTRY'):
            mapping_batch.append(
                Mapping(
                    source_type='CATEGORY',
                    destination_type=destination_type,
                    source_id=mapping.source.id,
                    destination_id=destination_id_map[mapping.destination.value]['id'],
                    workspace_id=workspace_id
                )
            )

    if mapping_batch:
        Mapping.objects.bulk_create(mapping_batch, batch_size=50)


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
            workspace_id=workspace_id, reimbursable_expenses_object=reimbursable_expenses_object)

        Mapping.bulk_create_mappings(fyle_categories, 'CATEGORY', reimbursable_destination_type, workspace_id)

        if corporate_credit_card_expenses_object:
            create_credit_card_category_mappings(
                reimbursable_expenses_object, corporate_credit_card_expenses_object, workspace_id)

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
        logger.error(
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


def create_fyle_projects_payload(projects: List[DestinationAttribute], existing_project_names: list):
    """
    Create Fyle Projects Payload from NetSuite Projects
    :param existing_project_names: Existing Projects in Fyle
    :param projects: NetSuite Projects
    :return: Fyle Projects Payload
    """
    payload = []

    for project in projects:
        if project.value not in existing_project_names:
            payload.append({
                'name': project.value,
                'code': project.destination_id,
                'description': 'NetSuite Customer / Project - {0}, Id - {1}'.format(
                    project.value,
                    project.destination_id
                ),
                'active': True if project.active is None else project.active
            })

    return payload


def post_projects_in_batches(fyle_connection: FyleConnector, workspace_id: int, destination_field: str):
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
            fyle_connection.connection.Projects.post(fyle_payload)
            fyle_connection.sync_projects()

        Mapping.bulk_create_mappings(paginated_ns_attributes, 'PROJECT', destination_field, workspace_id)


def auto_create_project_mappings(workspace_id):
    """
    Create Project Mappings
    """
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)
        ns_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

        fyle_connection = FyleConnector(
            refresh_token=fyle_credentials.refresh_token,
            workspace_id=workspace_id
        )

        ns_connection = NetSuiteConnector(
            netsuite_credentials=ns_credentials,
            workspace_id=workspace_id
        )

        fyle_connection.sync_projects()
        ns_connection.sync_projects()
        ns_connection.sync_customers()

        mapping_setting = MappingSetting.objects.get(
            source_field='PROJECT', workspace_id=workspace_id
        )

        post_projects_in_batches(fyle_connection, workspace_id, mapping_setting.destination_field)

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
        logger.error(
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

    mapping_setting = MappingSetting.objects.filter(
        ~Q(destination_field='CREDIT_CARD_ACCOUNT'),
        source_field='EMPLOYEE', workspace_id=workspace_id
    ).first()
    destination_type = mapping_setting.destination_field

    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    fyle_connection = FyleConnector(refresh_token=fyle_credentials.refresh_token, workspace_id=workspace_id)

    netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
    netsuite_connection = NetSuiteConnector(netsuite_credentials=netsuite_credentials, workspace_id=workspace_id)

    fyle_connection.sync_employees()
    if destination_type == 'EMPLOYEE':
        netsuite_connection.sync_employees()
    else:
        netsuite_connection.sync_vendors()

    Mapping.auto_map_employees(destination_type, employee_mapping_preference, workspace_id)


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
    fyle_connection = FyleConnector(refresh_token=fyle_credentials.refresh_token, workspace_id=workspace_id)
    fyle_connection.sync_employees()

    Mapping.auto_map_ccc_employees('CREDIT_CARD_ACCOUNT', default_ccc_account_id, workspace_id)


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
                'enabled': True if netsuite_attribute.active is None else netsuite_attribute.active,
                'description': 'Cost Center - {0}, Id - {1}'.format(
                    netsuite_attribute.value,
                    netsuite_attribute.destination_id
                )
            })

    return fyle_cost_centers_payload


def post_cost_centers_in_batches(fyle_connection: FyleConnector, workspace_id: int, netsuite_attribute_type: str):
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
            fyle_connection.connection.CostCenters.post(fyle_payload)
            fyle_connection.sync_cost_centers()

        Mapping.bulk_create_mappings(paginated_ns_attributes, 'COST_CENTER', netsuite_attribute_type, workspace_id)


def auto_create_cost_center_mappings(workspace_id):
    """
    Create Cost Center Mappings
    """
    try:
        fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)
        ns_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)

        fyle_connection = FyleConnector(
            refresh_token=fyle_credentials.refresh_token,
            workspace_id=workspace_id
        )

        ns_connection = NetSuiteConnector(
            netsuite_credentials=ns_credentials,
            workspace_id=workspace_id
        )

        mapping_setting = MappingSetting.objects.get(
            source_field='COST_CENTER', import_to_fyle=True, workspace_id=workspace_id
        )

        fyle_connection.sync_cost_centers()

        if mapping_setting.destination_field == 'LOCATION':
            ns_connection.sync_locations()

        elif mapping_setting.destination_field == 'PROJECT':
            ns_connection.sync_projects()

        elif mapping_setting.destination_field == 'DEPARTMENT':
            ns_connection.sync_departments()

        elif mapping_setting.destination_field == 'CLASS':
            ns_connection.sync_classifications()

        else:
            all_custom_list = CustomSegment.objects.filter(workspace_id=workspace_id).all()
            custom_lists = ns_connection.sync_custom_segments(all_custom_list)
            ns_connection.sync_custom_segments(custom_lists)

        post_cost_centers_in_batches(fyle_connection, workspace_id, mapping_setting.destination_field)

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
        logger.error(
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
                                             fyle_attribute: str):
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
            'id': custom_field_id,
            'name': fyle_attribute,
            'type': 'SELECT',
            'active': True,
            'mandatory': False,
            'placeholder': 'Select {0}'.format(fyle_attribute),
            'default_value': None,
            'options': fyle_expense_custom_field_options,
            'code': None
        }

        return expense_custom_field_payload


def upload_attributes_to_fyle(workspace_id: int, netsuite_attribute_type: str, fyle_attribute_type: str):
    """
    Upload attributes to Fyle
    """
    fyle_credentials: FyleCredential = FyleCredential.objects.get(workspace_id=workspace_id)

    fyle_connection = FyleConnector(refresh_token=fyle_credentials.refresh_token, workspace_id=workspace_id)

    netsuite_attributes: List[DestinationAttribute] = DestinationAttribute.objects.filter(
        workspace_id=workspace_id, attribute_type=netsuite_attribute_type
    )

    netsuite_attributes = remove_duplicates(netsuite_attributes)

    fyle_custom_field_payload = create_fyle_expense_custom_field_payload(
        fyle_attribute=fyle_attribute_type,
        netsuite_attributes=netsuite_attributes,
        workspace_id=workspace_id
    )

    if fyle_custom_field_payload:
        fyle_connection.connection.ExpensesCustomFields.post(fyle_custom_field_payload)
        fyle_connection.sync_expense_custom_fields(active_only=True)

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
        logger.error(
            'Error while creating %s workspace_id - %s error: %s', fyle_attribute_type, workspace_id, error
        )


def async_auto_create_custom_field_mappings(workspace_id):
    mapping_settings = MappingSetting.objects.filter(
        is_custom=True, import_to_fyle=True, workspace_id=workspace_id
    ).all()

    if mapping_settings:
        for mapping_setting in mapping_settings:
            if mapping_setting.import_to_fyle:
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
