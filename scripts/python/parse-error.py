from apps.netsuite.errors import (
    error_matcher,
    get_entity_values,
    replace_destination_id_with_values,
)
from apps.tasks.models import Error, TaskLog
from apps.workspaces.models import Configuration

errors_count = Error.objects.filter(type="NETSUITE_ERROR", is_parsed=False).count()
print(errors_count)
page_size = 200
count = 0
for offset in range(0, errors_count, page_size):
    limit = offset + page_size
    paginated_errors = Error.objects.filter(
        type="NETSUITE_ERROR", is_parsed=False
    ).order_by("id")[offset:limit]
    for error in paginated_errors:
        configuration = Configuration.objects.filter(
            workspace_id=error.workspace_id
        ).first()
        message = error.error_detail
        fund_source = error.expense_group.fund_source
        task_log = TaskLog.objects.filter(
            expense_group_id=error.expense_group.id
        ).first()
        export_types = {
            "EXPENSE REPORT": "expense_report",
            "JOURNAL ENTRY": "journal_entry",
            "BILL": "bills",
            "CREDIT CARD CHARGE": "credit_card_charge",
        }

        if fund_source == "PERSONAL":
            configuration_export_type = configuration.reimbursable_expenses_object
        else:
            configuration_export_type = (
                configuration.corporate_credit_card_expenses_object
            )

        export_type = export_types[configuration_export_type]

        error_dict, article_link = error_matcher(
            message=message,
            export_type=export_type,
            configuration=configuration,
        )
        entities = get_entity_values(error_dict, error.workspace_id)
        message = replace_destination_id_with_values(message, entities)
        if message:
            error.is_parsed = True
            error.error_detail = message
            error.article_link = article_link
            error.save()
            if isinstance(task_log.detail, list):
                task_log.detail[0]["message"] = message
                task_log.save()
            count += 1

print(count)
