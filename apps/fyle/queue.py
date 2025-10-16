import logging
from django_q.tasks import async_task

from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum, RoutingKeyEnum
from fyle_accounting_library.rabbitmq.connector import RabbitMQConnection
from fyle_accounting_library.rabbitmq.data_class import RabbitMQData

from apps.fyle.helpers import assert_valid_request

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def async_import_and_export_expenses(body: dict, workspace_id: int) -> None:
    """
    Async'ly import and export expenses
    :param body: body
    :return: None
    """
    rabbitmq = RabbitMQConnection.get_instance('netsuite_exchange')
    if body.get('action') in ('ADMIN_APPROVED', 'APPROVED', 'STATE_CHANGE_PAYMENT_PROCESSING', 'PAID') and body.get('data'):
        report_id = body['data']['id']
        org_id = body['data']['org_id']
        state = body['data']['state']
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
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

    elif body.get('action') == 'ACCOUNTING_EXPORT_INITIATED' and body.get('data'):
        report_id = body['data']['id']
        org_id = body['data']['org_id']
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
        async_task('apps.fyle.tasks.import_and_export_expenses', report_id, org_id, False, None, ExpenseImportSourceEnum.DIRECT_EXPORT)

    elif body.get('action') == 'UPDATED_AFTER_APPROVAL' and body.get('data') and body.get('resource') == 'EXPENSE':
        org_id = body['data']['org_id']
        logger.info("| Updating non-exported expenses through webhook | Content: {{WORKSPACE_ID: {} Payload: {}}}".format(workspace_id, body.get('data')))
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
        async_task('apps.fyle.tasks.update_non_exported_expenses', body['data'])

    elif body.get('action') in ('EJECTED_FROM_REPORT', 'ADDED_TO_REPORT') and body.get('data') and body.get('resource') == 'EXPENSE':
        org_id = body['data']['org_id']
        expense_id = body['data']['id']
        action = body.get('action')
        logger.info("| Handling expense %s | Content: {WORKSPACE_ID: %s EXPENSE_ID: %s Payload: %s}", action.lower().replace('_', ' '), workspace_id, expense_id, body.get('data'))
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
        async_task('apps.fyle.tasks.handle_expense_report_change', body['data'], action)
