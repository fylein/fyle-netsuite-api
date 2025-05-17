"""
Mapping Signals
"""
import logging
from datetime import datetime, timedelta, timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from fyle_accounting_mappings.models import MappingSetting, EmployeeMapping, Mapping, CategoryMapping, DestinationAttribute

from apps.mappings.schedules import new_schedule_or_delete_fyle_import_tasks
from apps.netsuite.helpers import schedule_payment_sync
from apps.workspaces.models import Configuration, NetSuiteCredentials, FyleCredential
from apps.netsuite.connector import NetSuiteConnector
from apps.workspaces.tasks import delete_cards_mapping_settings
from apps.tasks.models import Error

from .models import GeneralMapping, SubsidiaryMapping
from .tasks import schedule_auto_map_ccc_employees
from fyle_integrations_imports.models import ImportLog
from fyle_integrations_imports.modules.expense_custom_fields import ExpenseCustomField
from fyle_integrations_platform_connector import PlatformConnector
from fyle.platform.exceptions import WrongParamsError
from rest_framework.exceptions import ValidationError
from apps.mappings.constants import SYNC_METHODS

logger = logging.getLogger(__name__)
logger.level = logging.INFO


@receiver(pre_save, sender=CategoryMapping)
def pre_save_category_mappings(sender, instance: CategoryMapping, **kwargs):
    """
    Create CCC mapping if reimbursable type in ER and ccc in (bill, je, ccc)
    """
    if instance.destination_expense_head:
        if instance.destination_expense_head.detail and 'account_internal_id' in instance.destination_expense_head.detail and \
            instance.destination_expense_head.detail['account_internal_id']:

            destination_attribute = DestinationAttribute.objects.filter(
                workspace_id=instance.workspace_id,
                attribute_type='ACCOUNT',
                destination_id=instance.destination_expense_head.detail['account_internal_id']
            ).first()

            instance.destination_account_id = destination_attribute.id


@receiver(post_save, sender=Mapping)
def resolve_post_mapping_errors(sender, instance: Mapping, **kwargs):
    """
    Resolve errors after mapping is created
    """
    if instance.source_type == 'TAX_GROUP':
        Error.objects.filter(expense_attribute_id=instance.source_id).update(
            is_resolved=True, updated_at=datetime.now(timezone.utc)
        )


@receiver(post_save, sender=CategoryMapping)
def resolve_post_category_mapping_errors(sender, instance: Mapping, **kwargs):
    """
    Resolve errors after mapping is created
    """
    Error.objects.filter(expense_attribute_id=instance.source_category_id).update(
        is_resolved=True, updated_at=datetime.now(timezone.utc)
    )


@receiver(post_save, sender=EmployeeMapping)
def resolve_post_employees_mapping_errors(sender, instance: Mapping, **kwargs):
    """
    Resolve errors after mapping is created 
    """
    Error.objects.filter(expense_attribute_id=instance.source_employee_id).update(
        is_resolved=True, updated_at=datetime.now(timezone.utc)
    )

@receiver(post_save, sender=SubsidiaryMapping)
def run_post_subsidiary_mappings(sender, instance: SubsidiaryMapping, **kwargs):

    workspace = instance.workspace
    workspace.onboarding_state = 'EXPORT_SETTINGS'
    workspace.save()

@receiver(post_save, sender=MappingSetting)
def run_post_mapping_settings_triggers(sender, instance: MappingSetting, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    configuration = Configuration.objects.filter(workspace_id=instance.workspace_id).first()

    ALLOWED_SOURCE_FIELDS = [
        'PROJECT',
        'COST_CENTER'
    ]

    if instance.source_field in ALLOWED_SOURCE_FIELDS or instance.is_custom:
        new_schedule_or_delete_fyle_import_tasks(
            configuration_instance=configuration,
            mapping_settings=MappingSetting.objects.filter(
                workspace_id=instance.workspace_id
            ).values()
        )

    if configuration:
        delete_cards_mapping_settings(configuration)


@receiver(pre_save, sender=MappingSetting)
def run_pre_mapping_settings_triggers(sender, instance: MappingSetting, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    default_attributes = ['EMPLOYEE', 'CATEGORY', 'PROJECT', 'COST_CENTER', 'TAX_GROUP', 'CORPORATE_CARD']

    instance.source_field = instance.source_field.upper().replace(' ', '_')

    if instance.source_field not in default_attributes and instance.import_to_fyle:
        try:
            workspace_id = int(instance.workspace_id)

            # Checking is import_log exists or not if not create one
            import_log, is_created = ImportLog.objects.get_or_create(
                workspace_id=workspace_id,
                attribute_type=instance.source_field,
                defaults={
                    'status': 'IN_PROGRESS'
                }
            )

            last_successful_run_at = None
            if import_log and not is_created:
                last_successful_run_at = import_log.last_successful_run_at or None
                time_difference = datetime.now() - timedelta(minutes=30)
                offset_aware_time_difference = time_difference.replace(tzinfo=timezone.utc)

                if (
                    last_successful_run_at and offset_aware_time_difference
                    and (offset_aware_time_difference < last_successful_run_at)
                ):
                    import_log.last_successful_run_at = offset_aware_time_difference
                    last_successful_run_at = offset_aware_time_difference
                    import_log.save()

            netsuite_credentials = NetSuiteCredentials.objects.get(workspace_id=workspace_id)
            netsuite_connection = NetSuiteConnector(
                netsuite_credentials=netsuite_credentials,
                workspace_id=workspace_id
            )

            # Creating the expense_custom_field object with the correct last_successful_run_at value
            expense_custom_field = ExpenseCustomField(
                workspace_id=workspace_id,
                source_field=instance.source_field,
                destination_field=instance.destination_field,
                sync_after=last_successful_run_at,
                sdk_connection=netsuite_connection,
                destination_sync_methods=[SYNC_METHODS.get(instance.destination_field.upper(), 'custom_segments')]
            )

            fyle_credentials = FyleCredential.objects.get(workspace_id=workspace_id)
            platform = PlatformConnector(fyle_credentials=fyle_credentials)

            import_log.status = 'IN_PROGRESS'
            import_log.save()

            expense_custom_field.sync_expense_attributes(platform=platform)
            expense_custom_field.construct_payload_and_import_to_fyle(platform=platform, import_log=import_log)
            expense_custom_field.sync_expense_attributes(platform=platform)

        except WrongParamsError as error:
            logger.error(
                'Error while creating %s workspace_id - %s in Fyle %s %s',
                instance.source_field, instance.workspace_id, error.message, {'error': error.response}
            )
            if error.response and 'message' in error.response:
                raise ValidationError({
                    'message': error.response['message'],
                    'field_name': instance.source_field
                })

        # setting the import_log.last_successful_run_at to -30mins for the post_save_trigger
        import_log = ImportLog.objects.filter(workspace_id=workspace_id, attribute_type=instance.source_field).first()
        if import_log.last_successful_run_at:
            last_successful_run_at = import_log.last_successful_run_at - timedelta(minutes=30)
            import_log.last_successful_run_at = last_successful_run_at
            import_log.save()


@receiver(post_save, sender=GeneralMapping)
def run_post_general_mapping_triggers(sender, instance: GeneralMapping, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    configuration = Configuration.objects.get(workspace_id=instance.workspace_id)
    schedule_payment_sync(configuration)

    if instance.default_ccc_account_name:
        schedule_auto_map_ccc_employees(instance.workspace_id)
