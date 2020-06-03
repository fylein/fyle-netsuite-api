from django.urls import path

from .views import ExpenseGroupView, ExpenseGroupByIdView, ExpenseGroupScheduleView, ExpenseView, EmployeeView, \
    CategoryView, CostCenterView, ProjectView, UserProfileView

urlpatterns = [
    path('user/', UserProfileView.as_view()),
    path('expense_groups/', ExpenseGroupView.as_view()),
    path('expense_groups/trigger/', ExpenseGroupScheduleView.as_view()),
    path('expense_groups/<int:expense_group_id>/', ExpenseGroupByIdView.as_view()),
    path('expense_groups/<int:expense_group_id>/expenses/', ExpenseView.as_view()),
    path('employees/', EmployeeView.as_view({'get': 'get_employees'})),
    path('categories/', CategoryView.as_view({'get': 'get_categories'})),
    path('cost_centers/', CostCenterView.as_view({'get': 'get_cost_centers'})),
    path('projects/', ProjectView.as_view({'get': 'get_projects'}))
]
