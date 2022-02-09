"""
Mapping Signals
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_q.tasks import async_task

from fyle_accounting_mappings.models import MappingSetting

from apps.mappings.tasks import upload_attributes_to_fyle, schedule_cost_centers_creation,\
    schedule_fyle_attributes_creation, schedule_projects_creation
from apps.netsuite.helpers import schedule_payment_sync
from apps.workspaces.models import Configuration
from apps.workspaces.tasks import delete_cards_mapping_settings

from .models import GeneralMapping
from .tasks import schedule_auto_map_ccc_employees

@receiver(post_save, sender=MappingSetting)
def run_post_mapping_settings_triggers(sender, instance: MappingSetting, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    if instance.source_field == 'PROJECT':
        schedule_projects_creation(instance.import_to_fyle, int(instance.workspace_id))

    if instance.source_field == 'COST_CENTER':
        schedule_cost_centers_creation(instance.import_to_fyle, int(instance.workspace_id))

    if instance.is_custom:
        schedule_fyle_attributes_creation(int(instance.workspace_id))

    configuration = Configuration.objects.filter(workspace_id=instance.workspace_id).first()

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

    if instance.source_field not in default_attributes:
        upload_attributes_to_fyle(
            workspace_id=int(instance.workspace_id),
            netsuite_attribute_type=instance.destination_field,
            fyle_attribute_type=instance.source_field
        )

        async_task(
            'apps.mappings.tasks.auto_create_expense_fields_mappings',
            int(instance.workspace_id),
            instance.destination_field,
            instance.source_field
        )

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
