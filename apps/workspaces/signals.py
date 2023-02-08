"""
Workspace Signals
"""
import logging
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_q.models import Schedule

from apps.fyle.helpers import add_expense_id_to_expense_group_settings, update_import_card_credits_flag, \
    update_use_employee_attributes_flag
from apps.netsuite.helpers import schedule_payment_sync
from apps.netsuite.connector import NetSuiteConnector
from apps.mappings.helpers import schedule_or_delete_auto_mapping_tasks

from .models import Configuration, NetSuiteCredentials

logger = logging.getLogger(__name__)
logger.level = logging.INFO

@receiver(post_save, sender=Configuration)
def run_post_configration_triggers(sender, instance: Configuration, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    if instance.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
        add_expense_id_to_expense_group_settings(int(instance.workspace_id))

    if instance.employee_field_mapping != 'EMPLOYEE':
        update_use_employee_attributes_flag(instance.workspace_id)

    update_import_card_credits_flag(instance.corporate_credit_card_expenses_object, instance.reimbursable_expenses_object, int(instance.workspace_id))

    schedule_or_delete_auto_mapping_tasks(configuration=instance)

    merchant_import_schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_vendors_as_merchants',
        args=str(instance.workspace_id)
    ).first()

    if merchant_import_schedule:
        category_import_schedule = Schedule.objects.filter(
            func='apps.mappings.tasks.auto_create_category_mappings',
            args=str(instance.workspace_id)
        ).first()

        if category_import_schedule:
            category_import_schedule.next_run = merchant_import_schedule.next_run + timedelta(minutes=10)
            category_import_schedule.save()

    schedule_payment_sync(configuration=instance)


@receiver(post_save, sender=NetSuiteCredentials)
def run_post_netsuite_credential_trigger(sender, instance: NetSuiteCredentials, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    try:
        netsuite_connection = NetSuiteConnector(instance, instance.workspace_id)
        netsuite_connection.connection.folders.post({
            'externalId': instance.workspace.fyle_org_id,
            'name': 'Fyle Attachments - {0}'.format(instance.workspace.name)
        })
    except Exception:
        logger.info('Error while creating folder in NetSuite for workspace_id {}'.format(instance.workspace_id))
