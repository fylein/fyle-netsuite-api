from rest_framework.views import Response
from rest_framework.serializers import ValidationError
import logging
from collections import OrderedDict
from apps.workspaces.models import NetSuiteCredentials
from apps.workspaces.tasks import patch_integration_settings

logger = logging.getLogger(__name__)
logger.level = logging.INFO

EXPORT_TYPE_REDIRECTION = {
    'vendorBill': 'vendbill',
    'expenseReport': 'exprept',
    'journalEntry': 'journal',
    'chargeCard': 'cardchrg',
    'chargeCardRefund': 'cardrfnd'
}

def assert_valid(condition: bool, message: str) -> Response or None:
    """
    Assert conditions
    :param condition: Boolean condition
    :param message: Bad request message
    :return: Response or None
    """
    if not condition:
        raise ValidationError(detail={
            'message': message
        })

class LookupFieldMixin:
    lookup_field = "workspace_id"

    def filter_queryset(self, queryset):
        if self.lookup_field in self.kwargs:
            lookup_value = self.kwargs[self.lookup_field]
            filter_kwargs = {self.lookup_field: lookup_value}
            queryset = queryset.filter(**filter_kwargs)
        return super().filter_queryset(queryset)
    

def generate_netsuite_export_url(response_logs : OrderedDict, netsuite_credentials: NetSuiteCredentials):

    '''Generates the export url of expenses'''

    if response_logs:
        try:
            ns_account_id = netsuite_credentials.ns_account_id.lower()
            if '_sb' in ns_account_id:
                ns_account_id = ns_account_id.replace('_sb', '-sb')

            export_type = response_logs['type'] if 'type' in response_logs and response_logs['type'] else 'chargeCard'
            internal_id = response_logs['internalId']
            redirection = EXPORT_TYPE_REDIRECTION[export_type]
            url = f'https://{ns_account_id}.app.netsuite.com/app/accounting/transactions/{redirection}.nl?id={internal_id}'
            return url
        except Exception as exception:
            logger.exception({'error': exception})
    return None
    

def invalidate_netsuite_credentials(workspace_id, netsuite_credentials=None):
    if not netsuite_credentials:
        netsuite_credentials = NetSuiteCredentials.objects.filter(workspace_id=workspace_id, is_expired=False).first()

    if netsuite_credentials:
        if not netsuite_credentials.is_expired:
            patch_integration_settings(workspace_id, is_token_expired=True)
        netsuite_credentials.is_expired = True
        netsuite_credentials.save()
