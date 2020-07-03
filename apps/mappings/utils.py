from typing import Dict

from fyle_netsuite_api.utils import assert_valid

from .models import GeneralMapping, SubsidiaryMapping


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

    def create_or_update_general_mapping(self, general_mapping: Dict):
        """
        Create or update General mappings
        :param general_mapping: project mapping payload
        :return: general mappings objects
        """

        assert_valid('accounts_payable_name' in general_mapping and general_mapping['accounts_payable_name'],
                     'accounts payable name field is blank')
        assert_valid('accounts_payable_id' in general_mapping and general_mapping['accounts_payable_id'],
                     'accounts payable id field is blank')

        general_mapping_object, _ = GeneralMapping.objects.update_or_create(
            workspace_id=self.__workspace_id,
            defaults={
                'location_name': general_mapping['location_name'],
                'location_id': general_mapping['location_id'],
                'accounts_payable_name': general_mapping['accounts_payable_name'],
                'accounts_payable_id': general_mapping['accounts_payable_id']
            }
        )

        return general_mapping_object
