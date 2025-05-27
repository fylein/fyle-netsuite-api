from apps.workspaces.models import Configuration, NetSuiteCredentials
from fyle_accounting_mappings.models import MappingSetting
from fyle_integrations_imports.dataclasses import TaskSetting
from fyle_integrations_imports.queues import chain_import_fields_to_fyle
from apps.mappings.constants import SYNC_METHODS
from apps.mappings.models import GeneralMapping
from apps.netsuite.helpers import get_import_categories_settings, sync_override_tax_items


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
    general_mappings = GeneralMapping.objects.get(
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

    if configurations.import_tax_items and general_mappings and general_mappings.override_tax_details:
        sync_override_tax_items(credentials, workspace_id)
        task_settings['import_tax'] = {
            'destination_field': 'TAX_ITEM',
            'destination_sync_methods': [],
            'is_auto_sync_enabled': False,
            'is_3d_mapping': False
        }
    elif configurations.import_tax_items:
        task_settings['import_tax'] = {
            'destination_field': 'TAX_ITEM',
            'destination_sync_methods': [SYNC_METHODS['TAX_ITEM']],
            'is_auto_sync_enabled': False,
            'is_3d_mapping': False
        }

    if configurations.import_categories:
        is_3d_mapping_enabled, destination_field, destination_sync_methods = get_import_categories_settings(configurations)

        task_settings['import_categories'] = {
            'destination_field': destination_field,
            'destination_sync_methods': destination_sync_methods,
            'is_auto_sync_enabled': True,
            'is_3d_mapping': is_3d_mapping_enabled,
            'charts_of_accounts': [],
            'use_mapping_table': False
        }

    task_settings['import_items'] = configurations.import_items

    if configurations.import_vendors_as_merchants:
        task_settings['import_vendors_as_merchants'] = {
            'destination_field': 'VENDOR',
            'destination_sync_methods': [SYNC_METHODS['VENDOR']],
            'is_auto_sync_enabled': True,
            'is_3d_mapping': False
        }

    if mapping_settings:
        for mapping_setting in mapping_settings:
            if mapping_setting.source_field in ALLOWED_SOURCE_FIELDS or mapping_setting.is_custom:
                destination_sync_methods = [SYNC_METHODS.get(mapping_setting.destination_field.upper(), 'custom_segments')]

                if mapping_setting.destination_field == 'PROJECT':
                    destination_sync_methods.append(SYNC_METHODS['CUSTOMER'])

                task_settings['mapping_settings'].append(
                    {
                        'source_field': mapping_setting.source_field,
                        'destination_field': mapping_setting.destination_field,
                        'is_custom': mapping_setting.is_custom,
                        'destination_sync_methods': destination_sync_methods,
                        'is_auto_sync_enabled': True
                    }
                )

    chain_import_fields_to_fyle(workspace_id, task_settings)
