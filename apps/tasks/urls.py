from django.urls import path

from .views import TasksView, TasksByIdView, TasksByExpenseGroupIdView

urlpatterns = [
    path('', TasksByIdView.as_view()),
    path('expense_group/<int:expense_group_id>/', TasksByExpenseGroupIdView.as_view()),
    path('all/', TasksView.as_view())
]
