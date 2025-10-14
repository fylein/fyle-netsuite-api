import email
import logging
import time
import json
from datetime import datetime, timedelta, date
from typing import List

from django.conf import settings
from django.db.models import Q
from apps.fyle.helpers import post_request, patch_request
from django.template.loader import render_to_string
from apps.fyle.models import ExpenseGroup
from django_q.models import Schedule
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute
from fyle_accounting_library.fyle_platform.enums import ExpenseImportSourceEnum
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


def schedule_email_notification(workspace_id: int, schedule_enabled: bool, hours: int):
    if schedule_enabled and hours:
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

def schedule_sync(workspace_id: int, schedule_enabled: bool, hours: int, email_added: List, emails_selected: List, is_real_time_export_enabled: bool):
    ws_schedule, _ = WorkspaceSchedule.objects.get_or_create(
        workspace_id=workspace_id
    )
    ws_schedule.is_real_time_export_enabled = is_real_time_export_enabled
    ws_schedule.enabled = schedule_enabled

    schedule_email_notification(workspace_id=workspace_id, schedule_enabled=schedule_enabled, hours=hours)

    if schedule_enabled:
        ws_schedule.enabled = schedule_enabled
        ws_schedule.start_datetime = datetime.now()
        ws_schedule.interval_hours = hours
        ws_schedule.emails_selected = emails_selected
        ws_schedule.is_real_time_export_enabled = is_real_time_export_enabled

        if email_added:
            ws_schedule.additional_email_options.append(email_added)

        if is_real_time_export_enabled:
            # Delete existing schedule since user changed the setting to real time export
            schedule = ws_schedule.schedule
            if schedule:
                ws_schedule.schedule = None
                ws_schedule.save()
                schedule.delete()
        else:
            schedule, _ = Schedule.objects.update_or_create(
                func='apps.workspaces.tasks.run_sync_schedule',
                args='{}'.format(workspace_id),
                defaults={
                    'schedule_type': Schedule.MINUTES,
                    'minutes': hours * 60,
                    'next_run': datetime.now() + timedelta(hours=hours),
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

    else:
        ws_schedule.save()

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
            workspace_id=workspace_id, fund_source=fund_source, task_log=task_log, imported_from=ExpenseImportSourceEnum.BACKGROUND_SCHEDULE
        )

    if task_log.status == 'COMPLETE':
        eligible_expense_group_ids = ExpenseGroup.objects.filter(
            workspace_id=workspace_id,
            exported_at__isnull=True
        ).filter(
            Q(tasklog__isnull=True)
            | Q(tasklog__type__in=['CREATING_BILL', 'CREATING_EXPENSE_REPORT', 'CREATING_JOURNAL_ENTRY', 'CREATING_CREDIT_CARD_CHARGE', 'CREATING_CREDIT_CARD_REFUND'])
        ).exclude(
            tasklog__status='FAILED',
            tasklog__re_attempt_export=False
        ).values_list('id', flat=True).distinct()

        if eligible_expense_group_ids.exists():
            export_to_netsuite(workspace_id=workspace_id, expense_group_ids=list(eligible_expense_group_ids), triggered_by=ExpenseImportSourceEnum.BACKGROUND_SCHEDULE)

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
                        'brand_name': 'Sage Expense Management' if settings.IS_REBRANDED == 'True' else 'Fyle',
                        'is_rebranded': settings.IS_REBRANDED == 'True',
                        'errors': len(task_logs),
                        'fyle_company': workspace.name,
                        'netsuite_subsidiary': netsuite_subsidiary,
                        'workspace_id': workspace_id,
                        'year': date.today().year,
                        'export_time': export_time.date() if export_time else datetime.now(),
                        'app_url': "{0}/app/admin/#/integrations?integrationIframeTarget=integrations/netsuite".format(settings.FYLE_APP_URL),
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


def async_create_admin_subscriptions(workspace_id: int) -> None:
    """
    Create admin subscriptions
    :param workspace_id: workspace id
    :return: None
    """
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    platform = PlatformConnector(fyle_credentials)
    payload = {
        'is_enabled': True,
        'webhook_url': '{}/workspaces/{}/fyle/exports/'.format(settings.API_URL, workspace_id),
        'subscribed_resources': [
            'EXPENSE',
            'REPORT',
            'CATEGORY',
            'PROJECT',
            'COST_CENTER',
            'EXPENSE_FIELD',
            'DEPENDENT_EXPENSE_FIELD',
            'CORPORATE_CARD',
            'EMPLOYEE',
            'TAX_GROUP',
            'ORG_SETTING'
        ]
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
        post_request(url, payload, refresh_token)
    except Exception as error:
        logger.error(error)


def patch_integration_settings(workspace_id: int, errors: int = None, is_token_expired = None, unmapped_card_count: int = None):
    """
    Patch integration settings
    """
    fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
    refresh_token = fyle_credentials.refresh_token
    url = '{}/integrations/'.format(settings.INTEGRATIONS_SETTINGS_API)
    payload = {
        'tpa_name': 'Fyle Netsuite Integration'
    }

    if errors is not None:
        payload['errors_count'] = errors

    if unmapped_card_count is not None:
        payload['unmapped_card_count'] = unmapped_card_count

    if is_token_expired is not None:
        payload['is_token_expired'] = is_token_expired
        
    try:
        if fyle_credentials.workspace.onboarding_state == 'COMPLETE':
            patch_request(url, payload, refresh_token)
            return True
    except Exception as error:
        logger.error(error, exc_info=True)
        return False


def patch_integration_settings_for_unmapped_cards(workspace_id: int, unmapped_card_count: int) -> None:
    """
    Patch integration settings for unmapped cards
    :param workspace_id: Workspace id
    :param unmapped_card_count: Unmapped card count
    return: None
    """
    last_export_detail = LastExportDetail.objects.get(workspace_id=workspace_id)
    if unmapped_card_count != last_export_detail.unmapped_card_count:
        is_patched = patch_integration_settings(workspace_id=workspace_id, unmapped_card_count=unmapped_card_count)
        if is_patched:
            last_export_detail.unmapped_card_count = unmapped_card_count
            last_export_detail.save(update_fields=['unmapped_card_count', 'updated_at'])


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
