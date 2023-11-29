from fyle_netsuite_api.utils import LookupFieldMixin
from rest_framework import generics

from .helpers import filter_tasks_by_params
from .models import TaskLog
from .serializers import TaskLogSerializer
from django_filters.rest_framework import DjangoFilterBackend


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


class NewTaskView(LookupFieldMixin, generics.ListAPIView):

    serializer_class = TaskLogSerializer
    queryset = TaskLog.objects.all()
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = {'task':{'in','exact'}, 'expense_group_ids':{'in', 'exact'}, 'status': {'in', 'exact'}}
    ordering = ['-updated_at']
