from django.urls import path

from .views import TasksView, TasksByExpenseGroupIdView, NewTaskView

urlpatterns = [
    path('expense_group/<int:expense_group_id>/', TasksByExpenseGroupIdView.as_view(), name='task-by-expense-group-id'),
    path('all/', TasksView.as_view(), name='all-tasks'),
    path('v2/all,', NewTaskView.as_view(), name='new-all-tasks')
]
