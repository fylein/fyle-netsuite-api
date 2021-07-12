"""
NetSuite Signals
"""
import traceback

from rest_framework.response import Response
from rest_framework.views import status

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.workspaces.models import NetSuiteCredentials

from .models import CustomSegment
from .connector import NetSuiteConnector


@receiver(post_save, sender=CustomSegment)
def sync_custom_segments(sender, instance: CustomSegment, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    ns_credentials: NetSuiteCredentials = NetSuiteCredentials.objects.get(workspace_id=instance.workspace_id)
    ns_connection = NetSuiteConnector(
        netsuite_credentials=ns_credentials,
        workspace_id=instance.workspace_id
    )
    ns_connection.sync_custom_segments()


@receiver(pre_save, sender=CustomSegment)
def validate_custom_segment(sender, instance: CustomSegment, **kwargs):
    """
    :param sender: Sender Class
    :param instance: Row Instance of Sender Class
    :return: None
    """
    try:
        ns_credentials = NetSuiteCredentials.objects.get(workspace_id=instance.workspace_id)
        ns_connector = NetSuiteConnector(ns_credentials, workspace_id=instance.workspace_id)

        if instance.segment_type == 'CUSTOM_LIST':
            custom_list = ns_connector.connection.custom_lists.get(instance.internal_id)
            instance.name = custom_list['name'].upper().replace(' ', '_')
        elif instance.segment_type == 'CUSTOM_RECORD':
            custom_record = ns_connector.connection.custom_records.get_all_by_id(instance.internal_id)
            instance.name = custom_record[0]['recType']['name'].upper().replace(' ', '_')
    except Exception as error:
        raise Exception from error
