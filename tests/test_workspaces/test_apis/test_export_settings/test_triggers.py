from datetime import datetime, timezone
from apps.workspaces.apis.export_settings.triggers import ExportSettingsTrigger
from apps.workspaces.models import Configuration, LastExportDetail
from apps.tasks.models import TaskLog, Error
from apps.fyle.models import ExpenseGroup


def test_post_save_configuration_trigger(mocker, db):
    workspace_id = 1
    LastExportDetail.objects.create(workspace_id=workspace_id, last_exported_at=datetime.now(tz=timezone.utc))
    configuration, _ = Configuration.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': None,
            'corporate_credit_card_expenses_object': 'JOURNAL ENTRY'
        }
    )

    expense_grp_ccc = ExpenseGroup.objects.filter(
        workspace_id=workspace_id,
        exported_at__isnull=True
    ).exclude(fund_source__in=['PERSONAL']).values_list('id', flat=True)

    export_trigger = ExportSettingsTrigger(configuration=configuration, workspace_id=workspace_id)
    export_trigger.post_save_configurations()

    after_delete_count = TaskLog.objects.filter(
        workspace_id=workspace_id,
        status__in=['FAILED', 'FATAL']
    ).count()

    after_errors_count = Error.objects.filter(
        workspace_id=workspace_id,
        expense_group_id__in=expense_grp_ccc
    ).exclude(type__contains='_MAPPING').count()

    assert after_errors_count == 0
    assert after_delete_count == 0


def test_post_save_configuration_trigger_2(mocker, db):
    workspace_id = 1
    LastExportDetail.objects.create(workspace_id=workspace_id, last_exported_at=datetime.now(tz=timezone.utc))
    configuration, _ = Configuration.objects.update_or_create(
        workspace_id=workspace_id,
        defaults={
            'reimbursable_expenses_object': 'JOURNAL ENTRY',
            'corporate_credit_card_expenses_object': None
        }
    )

    expense_grp_personal = ExpenseGroup.objects.filter(
        workspace_id=workspace_id,
        exported_at__isnull=True
    ).exclude(fund_source__in=['CCC']).values_list('id', flat=True)

    export_trigger = ExportSettingsTrigger(configuration=configuration, workspace_id=workspace_id)
    export_trigger.post_save_configurations()

    after_delete_count = TaskLog.objects.filter(
        workspace_id=workspace_id,
        status__in=['FAILED', 'FATAL']
    ).count()

    after_errors_count = Error.objects.filter(
        workspace_id=workspace_id,
        expense_group_id__in=expense_grp_personal
    ).exclude(type__contains='_MAPPING').count()

    assert after_errors_count == 0
    assert after_delete_count == 0
