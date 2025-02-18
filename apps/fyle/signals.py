"""
Fyle Signals
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.exceptions import ValidationError
import logging
from apps.fyle.models import ExpenseFilter
from apps.fyle.tasks import re_run_skip_export_rule

logger = logging.getLogger(__name__)
logger.level = logging.INFO


@receiver(post_save, sender=ExpenseFilter)
def run_post_save_expense_filters(sender, instance: ExpenseFilter, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    if instance.join_by is None:
        try:
            re_run_skip_export_rule(instance.workspace)
        except Exception as e:
            logger.error(f'Error while processing expense filter for workspace: {instance.workspace.id} - {str(e)}')
            raise ValidationError('Failed to process expense filter')