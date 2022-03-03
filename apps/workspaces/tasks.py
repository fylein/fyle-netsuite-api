import email
from datetime import datetime
from typing import List

from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting

from apps.fyle.models import ExpenseGroup
from apps.fyle.tasks import create_expense_groups
from apps.netsuite.tasks import schedule_bills_creation, schedule_journal_entry_creation, \
    schedule_expense_reports_creation, schedule_credit_card_charge_creation
from apps.tasks.models import TaskLog
from apps.workspaces.models import User, Workspace, WorkspaceSchedule, Configuration


def schedule_sync(workspace_id: int, schedule_enabled: bool, hours: int, added_email: List, selected_email: List):
    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )

    if schedule_enabled:
        ws_schedule.enabled = schedule_enabled
        ws_schedule.start_datetime = datetime.now()
        ws_schedule.interval_hours = hours
        ws_schedule.selected_email = selected_email
        
        if added_email:
            ws_schedule.added_emails.append(added_email)


        schedule, _ = Schedule.objects.update_or_create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': hours * 60,
                'next_run': datetime.now()
            }
        )

        ws_schedule.schedule = schedule

        ws_schedule.save()

    elif not schedule_enabled:
        schedule = ws_schedule.schedule
        ws_schedule.enabled = schedule_enabled
        ws_schedule.schedule = None
        ws_schedule.save()
        schedule.delete()

    return ws_schedule


def run_sync_schedule(workspace_id):
    """
    Run schedule
    :param workspace_id: workspace id
    :return: None
    """
    task_log, _ = TaskLog.objects.update_or_create(
        workspace_id=workspace_id,
        type='FETCHING_EXPENSES',
        defaults={
            'status': 'IN_PROGRESS'
        }
    )

    configuration = Configuration.objects.get(workspace_id=workspace_id)
    fund_source = ['PERSONAL']
    if configuration.corporate_credit_card_expenses_object:
        fund_source.append('CCC')
    if configuration.reimbursable_expenses_object:
        create_expense_groups(
            workspace_id=workspace_id, configuration=configuration, fund_source=fund_source, task_log=task_log
        )

    if task_log.status == 'COMPLETE':
        if configuration.reimbursable_expenses_object:
            expense_group_ids = ExpenseGroup.objects.filter(fund_source='PERSONAL',
                                                            workspace_id=workspace_id).values_list('id', flat=True)

            if configuration.reimbursable_expenses_object == 'BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif configuration.reimbursable_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif configuration.reimbursable_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

        if configuration.corporate_credit_card_expenses_object:
            expense_group_ids = ExpenseGroup.objects.filter(fund_source='CCC',
                                                            workspace_id=workspace_id).values_list('id', flat=True)

            if configuration.corporate_credit_card_expenses_object == 'JOURNAL ENTRY':
                schedule_journal_entry_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif configuration.corporate_credit_card_expenses_object == 'BILL':
                schedule_bills_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

            elif configuration.corporate_credit_card_expenses_object == 'EXPENSE REPORT':
                schedule_expense_reports_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )
            elif configuration.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
                schedule_credit_card_charge_creation(
                    workspace_id=workspace_id, expense_group_ids=expense_group_ids
                )

def run_schedule_email_notification(workspace_id):

    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )

    admin_emails = []
    if ws_schedule.enabled:
        task_logs = TaskLog.objects.filter(workspace_id=workspace_id, status='FAILED')
        workspace_admins = Workspace.objects.filter(pk=workspace_id).values_list('user', flat=True)

        for admin_id in workspace_admins:
            user_email = User.objects.get(id=admin_id).email
            admin_emails.append(user_email)

        if ws_schedule.total_errors is None or len(task_logs) > ws_schedule.total_errors:
            context = {
                'name': 'Elon Musk',
                'errors': len(task_logs),
                'task_log': task_logs[0].detail
            }

            ws_schedule.total_errors = len(task_logs)
            ws_schedule.save()

            message = render_to_string("mail_template.html", context)

            mail = EmailMessage(
                subject="Export To Netsuite Failed",
                body=message,
                from_email='nilesh.p@fyle.in',
                to=['nileshpant112@gmail.com'],
            )

            mail.content_subtype = "html"
            mail.send()

def delete_cards_mapping_settings(configuration: Configuration):

    if not configuration.map_fyle_cards_netsuite_account or not configuration.corporate_credit_card_expenses_object:
        mapping_setting = MappingSetting.objects.filter(
            workspace_id=configuration.workspace_id,
            source_field='CORPORATE_CARD',
            destination_field='CREDIT_CARD_ACCOUNT'
        ).first()

        if mapping_setting:
            mapping_setting.delete()
