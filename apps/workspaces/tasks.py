import email
import time
from datetime import datetime, timedelta, date
from typing import List

from django.conf import settings
from django.db.models import Q
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute
from fyle_rest_auth.helpers import get_fyle_admin

from apps.fyle.models import ExpenseGroup
from apps.mappings.models import SubsidiaryMapping
from apps.fyle.tasks import create_expense_groups
from apps.netsuite.tasks import schedule_bills_creation, schedule_journal_entry_creation, \
    schedule_expense_reports_creation, schedule_credit_card_charge_creation
from apps.tasks.models import TaskLog
from apps.workspaces.models import LastExportDetail, User, Workspace, WorkspaceSchedule, Configuration, FyleCredential


def export_to_netsuite(workspace_id, export_mode=None):
    configuration = Configuration.objects.get(workspace_id=workspace_id)
    last_export_detail = LastExportDetail.objects.get(workspace_id=workspace_id)
    workspace_schedule = WorkspaceSchedule.objects.filter(workspace_id=workspace_id).first()
    last_exported_at = datetime.now()
    is_expenses_exported = False

    if configuration.reimbursable_expenses_object:
        expense_group_ids = ExpenseGroup.objects.filter(fund_source='PERSONAL',
                                                        workspace_id=workspace_id).values_list('id', flat=True)
        
        if len(expense_group_ids):
            is_expenses_exported = True

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
        
        if len(expense_group_ids):
            is_expenses_exported = True

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
    if is_expenses_exported:
        last_export_detail.last_exported_at = last_exported_at
        last_export_detail.export_mode = export_mode or 'MANUAL'
        if workspace_schedule:
            last_export_detail.next_export = last_exported_at + timedelta(hours=workspace_schedule.interval_hours)
        last_export_detail.save()

def schedule_email_notification(workspace_id: int, schedule_enabled: bool):
    if schedule_enabled:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.workspaces.tasks.run_email_notification',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 24 * 60,
                'next_run': datetime.now() + timedelta(minutes=10)
            }
        )
    else:
        schedule: Schedule = Schedule.objects.filter(
            func='apps.workspaces.tasks.run_email_notification',
            args='{}'.format(workspace_id)
        ).first()

        if schedule:
            schedule.delete()

def schedule_sync(workspace_id: int, schedule_enabled: bool, hours: int, email_added: List, emails_selected: List):
    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )

    schedule_email_notification(workspace_id=workspace_id, schedule_enabled=schedule_enabled)

    if schedule_enabled:
        ws_schedule.enabled = schedule_enabled
        ws_schedule.start_datetime = datetime.now()
        ws_schedule.interval_hours = hours
        ws_schedule.emails_selected = emails_selected
        
        if email_added:
            ws_schedule.additional_email_options.append(email_added)


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

    elif not schedule_enabled and ws_schedule.schedule:
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
        export_to_netsuite(workspace_id, 'AUTO')
        

def run_email_notification(workspace_id):

    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )

    task_logs = TaskLog.objects.filter(
        ~Q(type__in=['CREATING_VENDOR_PAYMENT', 'FETCHING_EXPENSES']),
        workspace_id=workspace_id,
        status='FAILED'
    )

    workspace = Workspace.objects.get(id=workspace_id)
    netsuite_subsidiary = SubsidiaryMapping.objects.get(workspace_id=workspace_id).subsidiary_name
    admin_data = WorkspaceSchedule.objects.get(workspace_id=workspace_id)

    if ws_schedule.enabled and admin_data.emails_selected:
        for admin_email in admin_data.emails_selected:
            attribute = ExpenseAttribute.objects.filter(workspace_id=workspace_id, value=admin_email).first()

            admin_name = 'Admin'
            if attribute:
                admin_name = attribute.detail['full_name']
            else:
                for data in admin_data.additional_email_options:
                    if data['email'] == admin_email:
                        admin_name = data['name']
            
            if workspace.last_synced_at and workspace.ccc_last_synced_at:
                export_time = max(workspace.last_synced_at, workspace.ccc_last_synced_at)
            else:
                export_time =  workspace.last_synced_at or workspace.ccc_last_synced_at

            if task_logs and (ws_schedule.error_count is None or len(task_logs) > ws_schedule.error_count):
                context = {
                    'name': admin_name,
                    'errors': len(task_logs),
                    'fyle_company': workspace.name,
                    'netsuite_subsidiary': netsuite_subsidiary,
                    'workspace_id': workspace_id,
                    'year': date.today().year,
                    'export_time': export_time.date() if export_time else datetime.now(),
                    'app_url': "{0}/workspaces/{1}/expense_groups".format(settings.FYLE_APP_URL, workspace_id)
                    }

                message = render_to_string("mail_template.html", context)

                mail = EmailMessage(
                    subject="Export To Netsuite Failed",
                    body=message,
                    from_email=settings.EMAIL,
                    to=[admin_email],
                )

                mail.content_subtype = "html"
                mail.send()

        ws_schedule.error_count = len(task_logs)
        ws_schedule.save()


def delete_cards_mapping_settings(configuration: Configuration):

    if not configuration.map_fyle_cards_netsuite_account or not configuration.corporate_credit_card_expenses_object:
        mapping_setting = MappingSetting.objects.filter(
            workspace_id=configuration.workspace_id,
            source_field='CORPORATE_CARD',
            destination_field='CREDIT_CARD_ACCOUNT'
        ).first()

        if mapping_setting:
            mapping_setting.delete()

def async_update_fyle_credentials(fyle_org_id: str, refresh_token: str):
    fyle_credentials = FyleCredential.objects.filter(workspace__fyle_org_id=fyle_org_id).first()
    if fyle_credentials:
        fyle_credentials.refresh_token = refresh_token
        fyle_credentials.save()


def async_update_workspace_name(workspace: Workspace, access_token: str):
    fyle_user = get_fyle_admin(access_token.split(' ')[1], None)
    org_name = fyle_user['data']['org']['name']

    workspace.name = org_name
    workspace.save()
