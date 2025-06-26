"""
NetSuite Signals
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from rest_framework.exceptions import NotFound

from fyle_accounting_mappings.models import DestinationAttribute

from apps.workspaces.models import NetSuiteCredentials

from .models import CustomSegment
from .connector import NetSuiteConnector


logger = logging.getLogger(__name__)
logger.level = logging.INFO


@receiver(post_save, sender=CustomSegment)
def sync_custom_segments(sender, instance: CustomSegment, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    try:
        ns_credentials: NetSuiteCredentials = NetSuiteCredentials.get_active_netsuite_credentials(instance.workspace_id)
    except NetSuiteCredentials.DoesNotExist:
        return
        
    ns_connection = NetSuiteConnector(
        netsuite_credentials=ns_credentials,
        workspace_id=instance.workspace_id
    )

    # add -CS identifier to custom-segment name if it matches with location / class
    if instance.name.lower() == 'location' or instance.name.lower() == 'class':
        instance.name = '{}-CS'.format(instance.name)

    attribute_type = instance.name.upper().replace(' ', '_')

    if instance.segment_type == 'CUSTOM_LIST':
        custom_segment_attributes = ns_connection.get_custom_list_attributes(attribute_type, instance.internal_id)
    elif instance.segment_type == 'CUSTOM_RECORD':
        custom_segment_attributes = ns_connection.get_custom_record_attributes(attribute_type, instance.internal_id)
    else:
        custom_segment_attributes = ns_connection.get_custom_segment_attributes(attribute_type, instance.internal_id)

    if custom_segment_attributes:
        DestinationAttribute.bulk_create_or_update_destination_attributes(
            custom_segment_attributes, attribute_type, instance.workspace_id, True)


@receiver(pre_save, sender=CustomSegment)
def validate_custom_segment(sender, instance: CustomSegment, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    try:
        ns_credentials = NetSuiteCredentials.get_active_netsuite_credentials(instance.workspace_id)
    except NetSuiteCredentials.DoesNotExist:
        raise NotFound('NetSuite credentials not found')
        
    ns_connector = NetSuiteConnector(ns_credentials, workspace_id=instance.workspace_id)
  
    try:
        if instance.segment_type == 'CUSTOM_LIST':
            custom_list = ns_connector.connection.custom_lists.get(instance.internal_id)
            instance.name = custom_list['name'].upper().replace(' ', '_')
        elif instance.segment_type == 'CUSTOM_RECORD':
            custom_record = ns_connector.connection.custom_record_types.get_all_by_id(instance.internal_id)
            instance.name = custom_record[0]['recType']['name'].upper().replace(' ', '_')
        else:
            custom_segment = ns_connector.connection.custom_segments.get(instance.internal_id)
            instance.name = custom_segment['recordType']['name'].upper().replace(' ', '_')
    except Exception as e:
        logger.info(e)
        raise NotFound()
