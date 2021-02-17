from django.urls import path

from .views import ExpenseGroupView, ExpenseGroupByIdView, ExpenseGroupScheduleView, ExpenseView, EmployeeView, \
    CategoryView, CostCenterView, ProjectView, ExpenseFieldsView, ExpenseCustomFieldsView, \
    ExpenseGroupSettingsView
urlpatterns = [
    path('expense_groups/', ExpenseGroupView.as_view(), name='expense-groups'),
    path('expense_groups/trigger/', ExpenseGroupScheduleView.as_view(), name='expense-groups-trigger'),
    path('expense_groups/<int:expense_group_id>/', ExpenseGroupByIdView.as_view(), name='expense-group-by-id'),
    path('expense_groups/<int:expense_group_id>/expenses/', ExpenseView.as_view(), name='expense-group-expenses'),
    path('employees/', EmployeeView.as_view(), name='employees'),
    path('categories/', CategoryView.as_view(), name='categories'),
    path('cost_centers/', CostCenterView.as_view(), name='cost-centers'),
    path('projects/', ProjectView.as_view(), name='projects'),
    path('expense_custom_fields/', ExpenseCustomFieldsView.as_view(), name='expense-custom-fields'),
    path('expense_fields/', ExpenseFieldsView.as_view(), name='expense-fields'),
    path('expense_group_settings/', ExpenseGroupSettingsView.as_view(), name='expense-group-settings')
]
