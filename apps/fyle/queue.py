import logging
from typing import List
from django_q.tasks import async_task
from apps.fyle.helpers import assert_valid_request

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def async_post_accounting_export_summary(org_id: str, workspace_id: int, expense_ids: List = None, is_failed: bool = False) -> None:
    """
    Async'ly post accounting export summary to Fyle
    :param org_id: org id
    :param workspace_id: workspace id
    :return: None
    """
    # This function calls post_accounting_export_summary asynchrously
    async_task('apps.fyle.tasks.post_accounting_export_summary', org_id, workspace_id, expense_ids, is_failed = is_failed)


def async_import_and_export_expenses(body: dict, workspace_id: int) -> None:
    """
    Async'ly import and export expenses
    :param body: body
    :return: None
    """
    if body.get('action') == 'ACCOUNTING_EXPORT_INITIATED' and body.get('data'):
        report_id = body['data']['id']
        org_id = body['data']['org_id']
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
        async_task('apps.fyle.tasks.import_and_export_expenses', report_id, org_id)

    elif body.get('action') == 'UPDATED_AFTER_APPROVAL' and body.get('data') and body.get('resource') == 'EXPENSE':
        org_id = body['data']['org_id']
        logger.info("| Updating non-exported expenses through webhook | Content: {{WORKSPACE_ID: {} Payload: {}}}".format(workspace_id, body.get('data')))
        assert_valid_request(workspace_id=workspace_id, fyle_org_id=org_id)
        async_task('apps.fyle.tasks.update_non_exported_expenses', body['data'])