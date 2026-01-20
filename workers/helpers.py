from enum import Enum

from fyle_accounting_library.rabbitmq.data_class import RabbitMQData
from fyle_accounting_library.rabbitmq.enums import RabbitMQExchangeEnum
from fyle_accounting_library.rabbitmq.connector import RabbitMQConnection


class RoutingKeyEnum(str, Enum):
    """
    Routing key enum
    """
    IMPORT = 'IMPORT.*'
    UTILITY = 'UTILITY.*'
    EXPORT_P0 = 'EXPORT.P0.*'
    EXPORT_P1 = 'EXPORT.P1.*'


class WorkerActionEnum(str, Enum):
    """
    Worker action enum
    """
    DIRECT_EXPORT = 'EXPORT.P0.DIRECT_EXPORT'
    DASHBOARD_SYNC = 'EXPORT.P0.DASHBOARD_SYNC'
    DISABLE_ITEMS = 'IMPORT.DISABLE_ITEMS'
    AUTO_MAP_EMPLOYEES = 'IMPORT.AUTO_MAP_EMPLOYEES'
    AUTO_MAP_CCC_ACCOUNT = 'IMPORT.AUTO_MAP_CCC_ACCOUNT'
    CREATE_EXPENSE_GROUP = 'EXPORT.P1.CREATE_EXPENSE_GROUP'
    UPDATE_WORKSPACE_NAME = 'UTILITY.UPDATE_WORKSPACE_NAME'
    EXPENSE_STATE_CHANGE = 'EXPORT.P1.EXPENSE_STATE_CHANGE'
    CREATE_VENDOR_PAYMENT = 'EXPORT.P1.CREATE_VENDOR_PAYMENT'
    PROCESS_REIMBURSEMENTS = 'EXPORT.P1.PROCESS_REIMBURSEMENTS'
    UPLOAD_ATTACHMENTS = 'UTILITY.UPLOAD_ATTACHMENTS'
    SYNC_NETSUITE_DIMENSION = 'IMPORT.SYNC_NETSUITE_DIMENSION'
    IMPORT_DIMENSIONS_TO_FYLE = 'IMPORT.IMPORT_DIMENSIONS_TO_FYLE'
    CREATE_ADMIN_SUBSCRIPTION = 'UTILITY.CREATE_ADMIN_SUBSCRIPTION'
    BACKGROUND_SCHEDULE_EXPORT = 'EXPORT.P1.BACKGROUND_SCHEDULE_EXPORT'
    CHECK_NETSUITE_OBJECT_STATUS = 'EXPORT.P1.CHECK_NETSUITE_OBJECT_STATUS'
    CHECK_AND_CREATE_CCC_MAPPINGS = 'IMPORT.CHECK_AND_CREATE_CCC_MAPPINGS'
    HANDLE_FYLE_REFRESH_DIMENSION = 'IMPORT.HANDLE_FYLE_REFRESH_DIMENSION'
    HANDLE_NETSUITE_REFRESH_DIMENSION = 'IMPORT.HANDLE_NETSUITE_REFRESH_DIMENSION'
    EXPENSE_UPDATED_AFTER_APPROVAL = 'UTILITY.EXPENSE_UPDATED_AFTER_APPROVAL'
    EXPENSE_ADDED_EJECTED_FROM_REPORT = 'UTILITY.EXPENSE_ADDED_EJECTED_FROM_REPORT'
    CHECK_INTERVAL_AND_SYNC_FYLE_DIMENSION = 'IMPORT.CHECK_INTERVAL_AND_SYNC_FYLE_DIMENSION'
    CHECK_INTERVAL_AND_SYNC_NETSUITE_DIMENSION = 'IMPORT.CHECK_INTERVAL_AND_SYNC_NETSUITE_DIMENSION'


QUEUE_BINDKEY_MAP = {
    'netsuite_import': RoutingKeyEnum.IMPORT,
    'netsuite_utility': RoutingKeyEnum.UTILITY,
    'netsuite_export.p0': RoutingKeyEnum.EXPORT_P0,
    'netsuite_export.p1': RoutingKeyEnum.EXPORT_P1
}


ACTION_METHOD_MAP = {
    WorkerActionEnum.DIRECT_EXPORT: 'apps.fyle.tasks.import_and_export_expenses',
    WorkerActionEnum.DASHBOARD_SYNC: 'apps.workspaces.actions.export_to_netsuite',
    WorkerActionEnum.DISABLE_ITEMS: 'fyle_integrations_imports.tasks.disable_items',
    WorkerActionEnum.AUTO_MAP_EMPLOYEES: 'apps.mappings.tasks.async_auto_map_employees',
    WorkerActionEnum.AUTO_MAP_CCC_ACCOUNT: 'apps.mappings.tasks.async_auto_map_ccc_account',
    WorkerActionEnum.CREATE_EXPENSE_GROUP: 'apps.fyle.tasks.create_expense_groups',
    WorkerActionEnum.EXPENSE_STATE_CHANGE: 'apps.fyle.tasks.import_and_export_expenses',
    WorkerActionEnum.CREATE_VENDOR_PAYMENT: 'apps.netsuite.tasks.create_vendor_payment',
    WorkerActionEnum.PROCESS_REIMBURSEMENTS: 'apps.netsuite.tasks.process_reimbursements',
    WorkerActionEnum.UPLOAD_ATTACHMENTS: 'apps.netsuite.tasks.upload_attachments_and_update_export',
    WorkerActionEnum.UPDATE_WORKSPACE_NAME: 'apps.workspaces.tasks.update_workspace_name',
    WorkerActionEnum.SYNC_NETSUITE_DIMENSION: 'apps.netsuite.helpers.sync_dimensions',
    WorkerActionEnum.CREATE_ADMIN_SUBSCRIPTION: 'apps.workspaces.tasks.async_create_admin_subscriptions',
    WorkerActionEnum.BACKGROUND_SCHEDULE_EXPORT: 'apps.workspaces.tasks.run_sync_schedule',
    WorkerActionEnum.CHECK_NETSUITE_OBJECT_STATUS: 'apps.netsuite.tasks.check_netsuite_object_status',
    WorkerActionEnum.CHECK_AND_CREATE_CCC_MAPPINGS: 'apps.mappings.tasks.check_and_create_ccc_mappings',
    WorkerActionEnum.HANDLE_FYLE_REFRESH_DIMENSION: 'apps.fyle.helpers.sync_dimensions',
    WorkerActionEnum.HANDLE_NETSUITE_REFRESH_DIMENSION: 'apps.netsuite.helpers.handle_refresh_dimensions',
    WorkerActionEnum.IMPORT_DIMENSIONS_TO_FYLE: 'apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
    WorkerActionEnum.EXPENSE_UPDATED_AFTER_APPROVAL: 'apps.fyle.tasks.update_non_exported_expenses',
    WorkerActionEnum.EXPENSE_ADDED_EJECTED_FROM_REPORT: 'apps.fyle.tasks.handle_expense_report_change',
    WorkerActionEnum.CHECK_INTERVAL_AND_SYNC_FYLE_DIMENSION: 'apps.fyle.helpers.check_interval_and_sync_dimension',
    WorkerActionEnum.CHECK_INTERVAL_AND_SYNC_NETSUITE_DIMENSION: 'apps.netsuite.helpers.check_interval_and_sync_dimension',
}


def get_routing_key(queue_name: str) -> str:
    """
    Get the routing key for a given queue name
    :param queue_name: str
    :return: str
    :raises ValueError: if queue_name is not found in QUEUE_BINDKEY_MAP
    """
    routing_key = QUEUE_BINDKEY_MAP.get(queue_name)
    if routing_key is None:
        raise ValueError(f'Unknown queue name: {queue_name}. Valid queue names are: {list(QUEUE_BINDKEY_MAP.keys())}')
    return routing_key


def publish_to_rabbitmq(payload: dict, routing_key: RoutingKeyEnum) -> None:
    """
    Publish messages to RabbitMQ
    :param: payload: dict
    :param: routing_key: RoutingKeyEnum
    :return: None
    """
    rabbitmq = RabbitMQConnection.get_instance(RabbitMQExchangeEnum.NETSUITE_EXCHANGE)
    data = RabbitMQData(new=payload)
    rabbitmq.publish(routing_key, data)

