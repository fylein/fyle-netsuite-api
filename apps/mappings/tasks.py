import logging
import traceback
from datetime import datetime

from typing import List, Dict

from django_q.models import Schedule

from fylesdk import WrongParamsError
from fyle_accounting_mappings.models import MappingSetting, Mapping, ExpenseAttribute, DestinationAttribute

from apps.fyle.utils import FyleConnector
from apps.netsuite.utils import NetSuiteConnector
from apps.workspaces.models import NetSuiteCredentials, FyleCredential

logger = logging.getLogger(__name__)


def create_fyle_projects_payload(projects: List[DestinationAttribute], workspace_id: int):
    """
    Create Fyle Projects Payload from NetSuite Projects
    :param projects: NetSuite Projects
    :param workspace_id: integer id of workspace
    :return: Fyle Projects Payload
    """
    payload = []
    existing_project_names = ExpenseAttribute.objects.filter(
        attribute_type='PROJECT', workspace_id=workspace_id).values_list('value', flat=True)

    for project in projects:
        if project.value not in existing_project_names:
            payload.append({
                'name': project.value,
                'code': project.destination_id,
                'description': 'NetSuite Project - {0}, Id - {1}'.format(
                    project.value,
                    project.destination_id
                ),
                'active': True if project.active is None else project.active
            })

    return payload


def upload_projects_to_fyle(workspace_id):
    """
    Upload projects to Fyle
    """
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

    fyle_connection.sync_projects(False)

    ns_attributes: List[DestinationAttribute] = ns_connection.sync_projects()

    fyle_payload: List[Dict] = create_fyle_projects_payload(ns_attributes, workspace_id)
    if fyle_payload:
        fyle_connection.connection.Projects.post(fyle_payload)
        fyle_connection.sync_projects(False)

    return ns_attributes


def auto_create_project_mappings(workspace_id):
    """
    Create Project Mappings
    :return: mappings
    """
    MappingSetting.bulk_upsert_mapping_setting([{
        'source_field': 'PROJECT',
        'destination_field': 'PROJECT'
    }], workspace_id=workspace_id)

    ns_attributes = upload_projects_to_fyle(workspace_id=workspace_id)

    project_mappings = []

    try:
        for project in ns_attributes:
            mapping = Mapping.create_or_update_mapping(
                source_type='PROJECT',
                destination_type='PROJECT',
                source_value=project.value,
                destination_value=project.value,
                workspace_id=workspace_id
            )
            project_mappings.append(mapping)

        return project_mappings
    except WrongParamsError as exception:
        logger.exception(
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


def schedule_projects_creation(import_projects, workspace_id):
    if import_projects:
        start_datetime = datetime.now()
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.mappings.tasks.auto_create_project_mappings',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 6 * 60,
                'next_run': start_datetime
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_project_mappings',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()
