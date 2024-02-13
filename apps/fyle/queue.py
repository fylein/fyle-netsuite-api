from django_q.tasks import async_task


def async_post_accounting_export_summary(org_id: str, workspace_id: int) -> None:
    """
    Async'ly post accounting export summary to Fyle
    :param org_id: org id
    :param workspace_id: workspace id
    :return: None
    """
    # This function calls post_accounting_export_summary asynchrously
    async_task('apps.fyle.tasks.post_accounting_export_summary', org_id, workspace_id)


def async_import_and_export_expenses(body: dict) -> None:
    """
    Async'ly import and export expenses
    :param body: body
    :return: None
    """
    if body.get('action') == 'ACCOUNTING_EXPORT_INITIATED' and body.get('data'):
        report_id = body['data']['id']
        org_id = body['data']['org_id']
        async_task('apps.fyle.tasks.import_and_export_expenses', report_id, org_id)
