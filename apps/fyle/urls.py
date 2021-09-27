import itertools

from django.urls import path

from .views import ExpenseGroupView, ExpenseGroupByIdView, ExpenseGroupScheduleView, FyleFieldsView, ExpenseView,\
    ExpenseAttributesView, ExpenseGroupSettingsView, SyncFyleDimensionView, RefreshFyleDimensionView,\
    ExpenseGroupCountView

expense_groups_paths = [
    path('expense_groups/', ExpenseGroupView.as_view(), name='expense-groups'),
    path('expense_groups/count/', ExpenseGroupCountView.as_view(), name='expense-groups-count'),
    path('expense_groups/trigger/', ExpenseGroupScheduleView.as_view(), name='expense-groups-trigger'),
    path('expense_groups/<int:pk>/', ExpenseGroupByIdView.as_view(), name='expense-group-by-id'),
    path('expense_groups/<int:expense_group_id>/expenses/', ExpenseView.as_view(), name='expense-group-expenses'),
    path('expense_group_settings/', ExpenseGroupSettingsView.as_view(), name='expense-group-settings')
]

fyle_dimension_paths = [
    path('sync_dimensions/', SyncFyleDimensionView.as_view(), name='sync-fyle-dimensions'),
    path('refresh_dimensions/', RefreshFyleDimensionView.as_view(), name='sync-netsuite-dimensions')
]

other_paths = [
    path('expense_attributes/', ExpenseAttributesView.as_view(), name='expense-attributes'),
    path('fyle_fields/', FyleFieldsView.as_view(), name='fyle-fields'),
]

urlpatterns = list(itertools.chain(expense_groups_paths, fyle_dimension_paths, other_paths))
