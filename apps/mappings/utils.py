from typing import Dict

from django.db.models import Q

from fyle_accounting_mappings.models import MappingSetting

from fyle_netsuite_api.utils import assert_valid

from .models import SubsidiaryMapping


class MappingUtils:
    def __init__(self, workspace_id):
        self.__workspace_id = workspace_id

    def create_or_update_subsidiary_mapping(self, subsidiary_mapping: Dict):
        """
        Create or update Subsidiary mappings
        :param subsidiary_mapping: project mapping payload
        :return: subsidiary mappings objects
        """

        mapping_setting = MappingSetting.objects.filter(
            Q(destination_field='SUBSIDIARY'), workspace_id=self.__workspace_id).first()

        print('Log Mapping Settings - ', mapping_setting)

        assert_valid('subsidiary_name' in subsidiary_mapping and subsidiary_mapping['subsidiary_name'],
                     'subsidiary name field is blank')
        assert_valid('internal_id' in subsidiary_mapping and subsidiary_mapping['internal_id'],
                     'internal id field is blank')

        subsidiary_mapping_object, _ = SubsidiaryMapping.objects.update_or_create(
            workspace_id=self.__workspace_id,
            defaults={
                'subsidiary_name': subsidiary_mapping['subsidiary_name'],
                'internal_id': subsidiary_mapping['internal_id']
            }
        )

        return subsidiary_mapping_object
