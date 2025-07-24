import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_q.tasks import async_task

from rest_framework.exceptions import ValidationError

from fyle_accounting_library.fyle_platform.enums import FundSourceEnum, ExpenseImportSourceEnum, ExpenseStateEnum

from apps.fyle.models import ExpenseFilter, ExpenseGroupSettings
from apps.fyle.tasks import re_run_skip_export_rule
from apps.workspaces.models import Configuration, Workspace
from fyle_accounting_mappings.models import ExpenseAttribute

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


@receiver(pre_save, sender=ExpenseGroupSettings)
def run_pre_save_expense_group_setting_triggers(sender, instance: ExpenseGroupSettings, **kwargs):
    """
    Run pre save expense group setting triggers
    """
    existing_expense_group_setting = ExpenseGroupSettings.objects.filter(
        workspace_id=instance.workspace_id
    ).first()

    if existing_expense_group_setting:
        configuration = Configuration.objects.filter(workspace_id=instance.workspace_id).first()
        if configuration:
            # TODO: move these async_tasks to maintenance worker later
            if configuration.reimbursable_expenses_object and existing_expense_group_setting.expense_state != instance.expense_state and existing_expense_group_setting.expense_state == ExpenseStateEnum.PAID and instance.expense_state == ExpenseStateEnum.PAYMENT_PROCESSING:
                logger.info(f'Reimbursable expense state changed from {existing_expense_group_setting.expense_state} to {instance.expense_state} for workspace {instance.workspace_id}, so pulling the data from Fyle')
                async_task('apps.fyle.tasks.create_expense_groups', workspace_id=instance.workspace_id, fund_source=[FundSourceEnum.PERSONAL], task_log=None, imported_from=ExpenseImportSourceEnum.CONFIGURATION_UPDATE)

            if configuration.corporate_credit_card_expenses_object and existing_expense_group_setting.ccc_expense_state != instance.ccc_expense_state and existing_expense_group_setting.ccc_expense_state == ExpenseStateEnum.PAID and instance.ccc_expense_state == ExpenseStateEnum.APPROVED:
                logger.info(f'Corporate credit card expense state changed from {existing_expense_group_setting.ccc_expense_state} to {instance.ccc_expense_state} for workspace {instance.workspace_id}, so pulling the data from Fyle')
                async_task('apps.fyle.tasks.create_expense_groups', workspace_id=instance.workspace_id, fund_source=[FundSourceEnum.CCC], task_log=None, imported_from=ExpenseImportSourceEnum.CONFIGURATION_UPDATE)
