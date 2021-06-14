import itertools

from django.urls import path

from .views import ExpenseGroupView, ExpenseGroupByIdView, ExpenseGroupScheduleView, ExpenseFieldsView, ExpenseView,\
    ExpenseCustomFieldsView, ExpenseGroupSettingsView, SyncFyleDimensionView, RefreshFyleDimensionView,\
    ExpenseGroupCountView

expense_groups_paths = [
    path('expense_groups/', ExpenseGroupView.as_view()),
    path('expense_groups/count/', ExpenseGroupCountView.as_view()),
    path('expense_groups/trigger/', ExpenseGroupScheduleView.as_view()),
    path('expense_groups/<int:pk>/', ExpenseGroupByIdView.as_view()),
    path('expense_groups/<int:expense_group_id>/expenses/', ExpenseView.as_view()),
    path('expense_group_settings/', ExpenseGroupSettingsView.as_view())
]

fyle_dimension_paths = [
    path('sync_dimensions/', SyncFyleDimensionView.as_view()),
    path('refresh_dimensions/', RefreshFyleDimensionView.as_view())
]

other_paths = [
    path('expense_custom_fields/', ExpenseCustomFieldsView.as_view()),
    path('expense_fields/', ExpenseFieldsView.as_view())
]

urlpatterns = list(itertools.chain(expense_groups_paths, fyle_dimension_paths, other_paths))
