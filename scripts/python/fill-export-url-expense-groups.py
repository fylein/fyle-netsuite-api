from fyle_netsuite_api.utils import generate_netsuite_export_url
from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import NetSuiteCredentials

expense_groups_ids: ExpenseGroup = ExpenseGroup.objects.filter(exported_at__isnull=False, export_url__isnull=True).values_list('id', flat=True)

try:
    count = 0
    for id in expense_groups_ids:
        expense_group: ExpenseGroup = ExpenseGroup.objects.get(id=id)
        netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)
        netsuite_export_url = generate_netsuite_export_url(expense_group.response_logs, netsuite_credentials)
        expense_group.export_url = netsuite_export_url
        expense_group.save()
        count += 1
    print(f'Updated {count} expense groups')
except Exception as e:
    print(e)
