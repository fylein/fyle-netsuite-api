from django_filters.rest_framework import DjangoFilterBackend
from fyle_netsuite_api.utils import LookupFieldMixin
from rest_framework import generics
from apps.tasks.models import Error
from apps.workspaces.apis.errors.serializers import ErrorSerializer


class ErrorsView(LookupFieldMixin, generics.ListAPIView):

    queryset = Error.objects.all()
    serializer_class = ErrorSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = {'type':{'exact'}, 'is_resolved':{'exact'}}


