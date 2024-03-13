from apps.workspaces.models import Configuration, NetSuiteCredentials
from fyle_accounting_mappings.models import MappingSetting
from fyle_integrations_imports.dataclasses import TaskSetting
from fyle_integrations_imports.queues import chain_import_fields_to_fyle
from apps.mappings.helpers import is_auto_sync_allowed
from apps.mappings.constants import SYNC_METHODS


def construct_tasks_and_chain_import_fields_to_fyle(workspace_id: int):
    """
    Construct tasks and chain import fields to fyle
    :param workspace_id: Workspace Id
    """
    mapping_settings = MappingSetting.objects.filter(
        workspace_id=workspace_id,
        import_to_fyle=True
    )
    configurations = Configuration.objects.get(
        workspace_id=workspace_id
    )
    credentials = NetSuiteCredentials.objects.get(
        workspace_id=workspace_id
    )

    task_settings: TaskSetting = {
        'import_tax': None,
        'import_vendors_as_merchants': None,
        'import_suppliers_as_merchants': None,
        'import_categories': None,
        'import_items': None,
        'mapping_settings': [],
        'credentials': credentials,
        'sdk_connection_string': 'apps.netsuite.connector.NetSuiteConnector',
        'custom_properties': None
    }

    ALLOWED_SOURCE_FIELDS = [
        'PROJECT',
        'COST_CENTER'
    ]

    if mapping_settings:
        for mapping_setting in mapping_settings:
            if mapping_setting.source_field in ALLOWED_SOURCE_FIELDS:
                task_settings['mapping_settings'].append(
                    {
                        'source_field': mapping_setting.source_field,
                        'destination_field': mapping_setting.destination_field,
                        'is_custom': mapping_setting.is_custom,
                        'destination_sync_methods': [SYNC_METHODS[mapping_setting.destination_field.upper()]],
                        'is_auto_sync_enabled': is_auto_sync_allowed(configurations, mapping_setting)
                    }
                )

    chain_import_fields_to_fyle(workspace_id, task_settings)
