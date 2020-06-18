from typing import Dict

from fyle_netsuite_api.utils import assert_valid

from .models import SubsidiaryMapping, LocationMapping


class MappingUtils:
    def __init__(self, workspace_id):
        self.__workspace_id = workspace_id

    def create_or_update_subsidiary_mapping(self, subsidiary_mapping: Dict):
        """
        Create or update Subsidiary mappings
        :param subsidiary_mapping: project mapping payload
        :return: subsidiary mappings objects
        """

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

    def create_or_update_location_mapping(self, location_mapping: Dict):
        """
        Create or update Location mappings
        :param location_mapping: project mapping payload
        :return: location mappings objects
        """

        assert_valid('location_name' in location_mapping and location_mapping['location_name'],
                     'location name field is blank')
        assert_valid('internal_id' in location_mapping and location_mapping['internal_id'],
                     'internal id field is blank')

        location_mapping_object, _ = LocationMapping.objects.update_or_create(
            workspace_id=self.__workspace_id,
            defaults={
                'location_name': location_mapping['location_name'],
                'internal_id': location_mapping['internal_id']
            }
        )

        return location_mapping_object
