from apps.tasks.models import TaskLog
from apps.workspaces.models import LastExportDetail
from django.db.models import Q

from apps.workspaces.tasks import patch_integration_settings


def update_last_export_details(workspace_id):
    last_export_detail = LastExportDetail.objects.get(workspace_id=workspace_id)

    failed_exports = TaskLog.objects.filter(
        ~Q(type__in=['CREATING_VENDOR_PAYMENT','FETCHING_EXPENSES']), workspace_id=workspace_id, status__in=['FAILED', 'FATAL']
    ).count()

    successful_exports = TaskLog.objects.filter(
        ~Q(type__in=['CREATING_VENDOR_PAYMENT', 'FETCHING_EXPENSES']),
        workspace_id=workspace_id,
        status='COMPLETE',
        updated_at__gt=last_export_detail.last_exported_at
    ).count()

    last_export_detail.failed_expense_groups_count = failed_exports
    last_export_detail.successful_expense_groups_count = successful_exports
    last_export_detail.total_expense_groups_count = failed_exports + successful_exports
    last_export_detail.save()
    patch_integration_settings(workspace_id, errors=failed_exports)

    return last_export_detail
