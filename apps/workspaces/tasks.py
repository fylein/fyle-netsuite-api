import email
import logging
import time
import json
from datetime import datetime, timedelta, date
from typing import List

from django.conf import settings
from django.db.models import Q
from apps.fyle.helpers import post_request
from django.template.loader import render_to_string
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute
from fyle_integrations_platform_connector import PlatformConnector
from fyle_rest_auth.helpers import get_fyle_admin

from apps.mappings.models import SubsidiaryMapping
from apps.fyle.tasks import create_expense_groups
from apps.tasks.models import TaskLog
from apps.workspaces.models import LastExportDetail, User, Workspace, WorkspaceSchedule, Configuration, FyleCredential
from apps.workspaces.actions import export_to_netsuite
from .utils import send_email


logger = logging.getLogger(__name__)
logger.level = logging.INFO


def schedule_email_notification(workspace_id: int, schedule_enabled: bool):
    if schedule_enabled:
        schedule, _ = Schedule.objects.update_or_create(
            func='apps.workspaces.tasks.run_email_notification',
            cluster='import',
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

        next_run = datetime.now() + timedelta(hours=hours)

        schedule, _ = Schedule.objects.update_or_create(
            func='apps.workspaces.tasks.run_sync_schedule',
            args='{}'.format(workspace_id),
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': hours * 60,
                'next_run': next_run
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
    fund_source = []
    
    if configuration.reimbursable_expenses_object:
        fund_source.append('PERSONAL')
    if configuration.corporate_credit_card_expenses_object:
        fund_source.append('CCC')

    if configuration.reimbursable_expenses_object or configuration.corporate_credit_card_expenses_object:
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
    try:
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
                    export_time = workspace.last_synced_at or workspace.ccc_last_synced_at

                if task_logs and (ws_schedule.error_count is None or len(task_logs) > ws_schedule.error_count):
                    context = {
                        'name': admin_name,
                        'errors': len(task_logs),
                        'fyle_company': workspace.name,
                        'netsuite_subsidiary': netsuite_subsidiary,
                        'workspace_id': workspace_id,
                        'year': date.today().year,
                        'export_time': export_time.date() if export_time else datetime.now(),
                        'app_url': "{0}/workspaces/{1}/expense_groups".format(settings.FYLE_APP_URL, workspace_id),
                        'integrations_app_url': settings.INTEGRATIONS_APP_URL
                    }

                    message = render_to_string("mail_template.html", context)

                    send_email(
                        recipient_email=[admin_email],
                        subject='Export To Netsuite Failed',
                        message=message,
                        sender_email=settings.EMAIL,
                    )

            ws_schedule.error_count = len(task_logs)
            ws_schedule.save()

    except Exception as e:
        logger.info('Error in sending email notification: %s', str(e))


def delete_cards_mapping_settings(configuration: Configuration):

    if not configuration.map_fyle_cards_netsuite_account or not configuration.corporate_credit_card_expenses_object:
        mapping_setting = MappingSetting.objects.filter(
            workspace_id=configuration.workspace_id,
            source_field='CORPORATE_CARD',
            destination_field='CREDIT_CARD_ACCOUNT'
        ).first()

        if mapping_setting:
            mapping_setting.delete()


def async_create_admin_subcriptions(workspace_id: int) -> None:
    """
    Create admin subscriptions
    :param workspace_id: workspace id
    :return: None
    """
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials)
    payload = {
        'is_enabled': True,
        'webhook_url': '{}/workspaces/{}/fyle/exports/'.format(settings.API_URL, workspace_id)
    }
    platform.subscriptions.post(payload)


def post_to_integration_settings(workspace_id: int, active: bool):
    """
    Post to integration settings
    """
    refresh_token = FyleCredential.objects.get(workspace_id=workspace_id).refresh_token
    url = '{}/integrations/'.format(settings.INTEGRATIONS_SETTINGS_API)
    payload = {
        'tpa_id': settings.FYLE_CLIENT_ID,
        'tpa_name': 'Fyle Netsuite Integration',
        'type': 'ACCOUNTING',
        'is_active': active,
        'connected_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }

    try:
        post_request(url, json.dumps(payload), refresh_token)
    except Exception as error:
        logger.error(error)


def async_update_fyle_credentials(fyle_org_id: str, refresh_token: str):
    fyle_credentials = FyleCredential.objects.filter(workspace__fyle_org_id=fyle_org_id).first()
    if fyle_credentials and refresh_token:
        fyle_credentials.refresh_token = refresh_token
        fyle_credentials.save()


def async_update_workspace_name(workspace: Workspace, access_token: str):
    fyle_user = get_fyle_admin(access_token.split(' ')[1], None)
    org_name = fyle_user['data']['org']['name']

    workspace.name = org_name
    workspace.save()
