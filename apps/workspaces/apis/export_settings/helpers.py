from typing import List
from django.db import transaction

from apps.fyle.models import ExpenseGroup
from apps.tasks.models import Error, TaskLog
from apps.workspaces.models import Configuration
import logging

logger = logging.getLogger(__name__)


def clear_workspace_errors_on_export_type_change(
    workspace_id: int,
    old_configuration: dict,
    new_configuration: Configuration
) -> None:
    """
    Clear workspace errors when export type settings change.

    Args:
        workspace_id: The workspace ID to clear errors for
        old_configuration: Previous configuration as dictionary
        new_configuration: New Configuration model instance

    Returns:
        Tuple of (deleted_errors_count, deleted_task_logs_count)
    """
    try:
        with transaction.atomic():
            old_reimburse = old_configuration.get('reimbursable_expenses_object')
            new_reimburse = new_configuration.reimbursable_expenses_object
            old_ccc = old_configuration.get('corporate_credit_card_expenses_object')
            new_ccc = new_configuration.corporate_credit_card_expenses_object

            reimburse_changed = old_reimburse != new_reimburse
            ccc_changed = old_ccc != new_ccc

            affected_fund_sources: List[str] = []
            if reimburse_changed:
                affected_fund_sources.append('PERSONAL')
            if ccc_changed:
                affected_fund_sources.append('CCC')

            total_deleted_errors = 0
            total_deleted_task_logs = 0

            if affected_fund_sources:
                logger.info("Export type changed for fund sources %s in workspace %s", affected_fund_sources, workspace_id)

                affected_expense_group_ids = list(ExpenseGroup.objects.filter(
                    workspace_id=workspace_id,
                    exported_at__isnull=True,
                    fund_source__in=affected_fund_sources
                ).values_list('id', flat=True))

                if affected_expense_group_ids:
                    logger.info("Found %s affected expense groups", len(affected_expense_group_ids))

                    expense_group_errors = Error.objects.filter(
                        workspace_id=workspace_id,
                        expense_group_id__in=affected_expense_group_ids
                    )
                    if expense_group_errors.exists():
                        deleted_direct_errors, deleted_direct_errors_count = expense_group_errors.delete()
                        total_deleted_errors += deleted_direct_errors
                        logger.info("Cleared %s direct expense group errors", deleted_direct_errors)
                        logger.info("Deleted direct errors data: %s", deleted_direct_errors_count)

                    mapping_errors = Error.objects.filter(
                        workspace_id=workspace_id,
                        type__in=['EMPLOYEE_MAPPING', 'CATEGORY_MAPPING'],
                        is_resolved=False
                    )

                    affected_ids_set = set(affected_expense_group_ids)

                    errors_to_update = []
                    mapping_errors_to_delete = []

                    for error in mapping_errors:
                        current_ids_set = set(error.mapping_error_expense_group_ids)

                        if current_ids_set & affected_ids_set:
                            remaining_ids = list(current_ids_set - affected_ids_set)

                            if remaining_ids:
                                error.mapping_error_expense_group_ids = remaining_ids
                                errors_to_update.append(error)
                            else:
                                mapping_errors_to_delete.append(error.id)

                    mapping_errors_updated = 0
                    if errors_to_update:
                        Error.objects.bulk_update(errors_to_update, ['mapping_error_expense_group_ids'])
                        mapping_errors_updated = len(errors_to_update)

                    mapping_errors_deleted = 0
                    if mapping_errors_to_delete:
                        mapping_errors_deleted, mapping_errors_data = Error.objects.filter(
                            workspace_id=workspace_id,
                            id__in=mapping_errors_to_delete,
                            is_resolved=False
                        ).delete()
                        logger.info("Deleted mapping errors data: %s", mapping_errors_data)

                    if mapping_errors_updated > 0:
                        logger.info("Updated %s mapping errors by removing affected expense group IDs", mapping_errors_updated)

                    if mapping_errors_deleted > 0:
                        total_deleted_errors += mapping_errors_deleted
                        logger.info("Cleared %s mapping errors for affected expense groups", mapping_errors_deleted)

                    failed_task_logs = TaskLog.objects.filter(
                        workspace_id=workspace_id,
                        expense_group_id__in=affected_expense_group_ids,
                        status__in=['FAILED', 'FATAL']
                    )
                    if failed_task_logs.exists():
                        deleted_failed_task_logs, _ = failed_task_logs.delete()
                        total_deleted_task_logs += deleted_failed_task_logs
                        logger.info("Cleared %s failed task logs for affected expense groups", deleted_failed_task_logs)

                    enqueued_task_ids = list(TaskLog.objects.select_for_update(skip_locked=True).filter(
                        workspace_id=workspace_id,
                        status='ENQUEUED'
                    ).exclude(type__in=['FETCHING_EXPENSES', 'CREATING_VENDOR_PAYMENT']).values_list('id', flat=True))

                    if enqueued_task_ids:
                        logger.info("Deleting %s ENQUEUED task logs for workspace %s so they can be re-queued with new settings", len(enqueued_task_ids), workspace_id)
                        deleted_enqueued_task_logs, _ = TaskLog.objects.filter(id__in=enqueued_task_ids).delete()
                        total_deleted_task_logs += deleted_enqueued_task_logs
                        logger.info("Successfully deleted %s ENQUEUED task logs", deleted_enqueued_task_logs)

            logger.info("Successfully cleared %s errors and %s task logs for workspace %s", total_deleted_errors, total_deleted_task_logs, workspace_id)

    except Exception as e:
        logger.error("Error clearing workspace errors for workspace %s: %s", workspace_id, str(e))
        raise
