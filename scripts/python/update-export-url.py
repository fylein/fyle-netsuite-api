from apps.fyle.models import ExpenseGroup
from apps.workspaces.models import NetSuiteCredentials
from fyle_netsuite_api.utils import generate_netsuite_export_url


expense_groups = ExpenseGroup.objects.all()

for expense_group in expense_groups:
    try:
        netsuite_cred = NetSuiteCredentials.objects.get(workspace_id=expense_group.workspace_id)
        url = generate_netsuite_export_url(response_logs=expense_group.response_logs, ns_account_id=netsuite_cred.ns_account_id)
        expense_group.export_url = url
        expense_group.save()
        print('Export URl updated for expense group id {}'.format(expense_group.id))
    except Exception as exception:
        print('Something went wrong during updating export_url for workspace_id {}'.format(expense_group.workspace_id))
