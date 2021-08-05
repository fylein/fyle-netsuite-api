from rest_framework import generics

from .helpers import filter_tasks_by_params
from .models import TaskLog
from .serializers import TaskLogSerializer


class TasksView(generics.ListAPIView):
    """
    Tasks view
    """
    serializer_class = TaskLogSerializer

    def get_queryset(self):
        """
        Return task logs based on params
        """
        return filter_tasks_by_params(self.request.query_params, self.kwargs['workspace_id'])


class TasksByExpenseGroupIdView(generics.RetrieveAPIView):
    """
    Get Task by Expense Group ID
    """
    serializer_class = TaskLogSerializer
    lookup_field = 'expense_group_id'
    queryset = TaskLog.objects.all()
