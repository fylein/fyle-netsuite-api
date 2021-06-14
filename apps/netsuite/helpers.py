from apps.netsuite.tasks import schedule_vendor_payment_creation, schedule_netsuite_objects_status_sync, \
    schedule_reimbursements_sync
from apps.workspaces.models import Configuration


def schedule_payment_sync(configuration: Configuration):
    """
    :param configuration: Workspace Configuration Intance
    :return: None
    """
    schedule_vendor_payment_creation(
        sync_fyle_to_netsuite_payments=configuration.sync_fyle_to_netsuite_payments,
        workspace_id=configuration.workspace_id
    )

    schedule_netsuite_objects_status_sync(
        sync_netsuite_to_fyle_payments=configuration.sync_netsuite_to_fyle_payments,
        workspace_id=configuration.workspace_id
    )

    schedule_reimbursements_sync(
        sync_netsuite_to_fyle_payments=configuration.sync_netsuite_to_fyle_payments,
        workspace_id=configuration.workspace_id
    )
