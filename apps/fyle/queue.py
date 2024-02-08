from django_q.tasks import async_task

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
