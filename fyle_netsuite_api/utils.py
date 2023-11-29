from rest_framework.views import Response
from rest_framework.serializers import ValidationError
import logging

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
    

def generate_netsuite_export_url(response_logs, ns_account_id):
    if response_logs:
        try:
            export_type = response_logs['type'] if response_logs['type'] else 'chargeCard'
            internal_id = response_logs['internalId']
            redirection = EXPORT_TYPE_REDIRECTION[export_type]
            url = f'https://{ns_account_id}.app.netsuite.com/app/accounting/transactions/${redirection}.nl?id={internal_id}'
            return url
        except Exception as exception:
            logger.exception({'error': exception})
    return None
