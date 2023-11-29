from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import NetSuiteCredentials, Workspace
from fyle_netsuite_api.utils import generate_netsuite_export_url


prod_workspaces = Workspace.objects.exclude(
    name__iregex=r'(fyle|test)',
)

for workspace in prod_workspaces:
    page_size = 200
    expense_group_counts = ExpenseGroup.objects.filter(workspace_id=workspace.id, response_logs__isnull=False).count()
    for offset in range(0, expense_group_counts, page_size):
        expense_to_be_updated = []
        limit = offset + page_size
        paginated_expense_groups = ExpenseGroup.objects.filter(workspace_id=workspace.id, response_logs__isnull=False)[offset:limit]
        for expense_group in paginated_expense_groups:
            netsuite_cred = NetSuiteCredentials.objects.get(workspace_id=workspace.id)
            expense_group.export_url = generate_netsuite_export_url(response_logs=expense_group.response_logs, ns_account_id=netsuite_cred.ns_account_id)
            expense_group.save()
