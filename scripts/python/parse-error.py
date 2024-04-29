from apps.netsuite.errors import error_matcher, get_entity_values, replace_destination_id_with_values
from apps.tasks.models import Error
from apps.workspaces.models import Configuration

errors_count = Error.objects.filter(type='NETSUITE_ERROR', is_parsed=False).count()
print(errors_count)
page_size = 200
count = 0
for offset in range(0, errors_count, page_size):
    limit = offset + page_size
    paginated_errors = Error.objects.filter(type='NETSUITE_ERROR', is_parsed=False).order_by('id')[offset:limit]
    for error in paginated_errors:
        configuration = Configuration.object.filter(workspace_id=error.workspace_id)
        message = error.error_detail
        fund_source = error.expense_group.fund_source
        if fund_source == 'PERSONAL':
            configuration_export_type = configuration.reimbursable_expenses_object
        else:
            configuration_export_type = configuration.corporate_credit_card_expenses_object
        error_dict, article_link = error_matcher(message=message, export_type=configuration_export_type, configuration=configuration)
        entities = get_entity_values(error_dict, error.workspace_id)
        message = replace_destination_id_with_values(message, entities)

        if message:
            error.is_parsed = True
            error.error_detail = message
            error.article_link = article_link
            error.expense_group.task_log['message'] = message
            error.save()
            count += 1
