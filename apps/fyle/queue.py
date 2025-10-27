import logging
from django_q.tasks import async_task

from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum, RoutingKeyEnum, WebhookAttributeActionEnum
from fyle_accounting_library.rabbitmq.connector import RabbitMQConnection
from fyle_accounting_library.rabbitmq.data_class import RabbitMQData
from fyle_integrations_imports.modules.webhook_attributes import WebhookAttributeProcessor

from apps.fyle.helpers import assert_valid_request
from apps.workspaces.models import FeatureConfig

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def handle_webhook_callback(body: dict, workspace_id: int) -> None:
    """
    Handle webhook callback from Fyle
    :param body: webhook body
    :param workspace_id: workspace id
    :return: None
    """
    action = body.get('action')
    resource = body.get('resource')
    data = body.get('data')
    
    if data and data.get('org_id'):
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=data['org_id'])
    
    rabbitmq = RabbitMQConnection.get_instance('netsuite_exchange')
    if action in ('ADMIN_APPROVED', 'APPROVED', 'STATE_CHANGE_PAYMENT_PROCESSING', 'PAID') and data:
        report_id = data['id']
        org_id = data['org_id']
        state = data['state']
        payload = {
            'data': {
                'report_id': report_id,
                'org_id': org_id,
                'is_state_change_event': True,
                'report_state': state,
                'imported_from': ExpenseImportSourceEnum.WEBHOOK
            },
            'workspace_id': workspace_id
        }
        data = RabbitMQData(
            new=payload
        )
        rabbitmq.publish(RoutingKeyEnum.EXPORT, data)

    elif action == 'ACCOUNTING_EXPORT_INITIATED' and data:
        report_id = data['id']
        org_id = data['org_id']
        async_task('apps.fyle.tasks.import_and_export_expenses', report_id, org_id, False, None, ExpenseImportSourceEnum.DIRECT_EXPORT)

    elif action == 'UPDATED_AFTER_APPROVAL' and data and resource == 'EXPENSE':
        org_id = data['org_id']
        logger.info("| Updating non-exported expenses through webhook | Content: {{WORKSPACE_ID: {} Payload: {}}}".format(workspace_id, data))
        async_task('apps.fyle.tasks.update_non_exported_expenses', data)

    elif action in ('EJECTED_FROM_REPORT', 'ADDED_TO_REPORT') and data and resource == 'EXPENSE':
        org_id = data['org_id']
        expense_id = data['id']
        logger.info("| Handling expense %s | Content: {WORKSPACE_ID: %s EXPENSE_ID: %s Payload: %s}", action.lower().replace('_', ' '), workspace_id, expense_id, data)
        async_task('apps.fyle.tasks.handle_expense_report_change', data, action)

    elif action in (WebhookAttributeActionEnum.CREATED, WebhookAttributeActionEnum.UPDATED, WebhookAttributeActionEnum.DELETED):
        try:
            fyle_webhook_sync_enabled = FeatureConfig.get_feature_config(workspace_id=workspace_id, key='fyle_webhook_sync_enabled')
            if fyle_webhook_sync_enabled:
                logger.info("| Processing attribute webhook | Content: {{WORKSPACE_ID: {} Payload: {}}}".format(workspace_id, body))
                processor = WebhookAttributeProcessor(workspace_id)
                processor.process_webhook(body)
        except Exception as e:
            logger.error(f"Error processing attribute webhook for workspace {workspace_id}: {str(e)}")
