from datetime import datetime
from time import sleep

from django.db.models import Q

from apps.workspaces.models import Workspace
from apps.fyle.models import Expense
from apps.fyle.tasks import post_accounting_export_summary

# PLEASE RUN scripts/python/fill-accounting-export-summary.py BEFORE RUNNING THIS SCRIPT
workspaces = Workspace.objects.filter(
    ~Q(name__icontains='fyle for') & ~Q(name__icontains='test')
)

start_time = datetime.now()
number_of_expenses_to_be_posted = Expense.objects.filter(
    accounting_export_summary__synced=False
).count()
print('Number of expenses to be posted - {}'.format(number_of_expenses_to_be_posted))
for workspace in workspaces:
    expenses_count = Expense.objects.filter(
        accounting_export_summary__synced=False,
        workspace_id=workspace.id
    ).count()
    print('Updating summary from workspace - {} with ID - {}'.format(workspace.name, workspace.id))
    print('Number of expenses_count to be posted for the current workspace - {}'.format(expenses_count))
    if expenses_count:
        try:
            sleep(1)
            post_accounting_export_summary(workspace.fyle_org_id, workspace.id)
        except Exception as e:
            print('Error while posting accounting export summary for workspace - {} with ID - {}'.format(workspace.name, workspace.id))
            print(e.__dict__)

number_of_expenses_posted = Expense.objects.filter(
    accounting_export_summary__synced=True
).count()
print('Number of expenses posted to Fyle - {}'.format(number_of_expenses_posted))
end_time = datetime.now()
print('Time taken - {}'.format(end_time - start_time))

# This query should return 0 rows
# select expense_group_id from task_logs where status not in ('ENQUEUED', 'IN_PROGRESS') and expense_group_id in (select expensegroup_id from expense_groups_expenses  where expense_id in (select id from expenses where accounting_export_summary ='{}'));
