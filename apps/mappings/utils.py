from typing import Dict

from django.db.models import Q
from fyle_accounting_mappings.models import MappingSetting

from apps.workspaces.models import WorkspaceGeneralSettings
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

        general_settings = WorkspaceGeneralSettings.objects.get(workspace_id=self.__workspace_id)

        assert_valid('location_id' in general_mapping, 'location id field in blank')
        assert_valid('location_name' in general_mapping, 'location name field in blank')

        params = {
            'location_name': general_mapping['location_name'],
            'location_id': general_mapping['location_id'],
            'accounts_payable_name': None,
            'accounts_payable_id': None,
            'reimbursable_account_name': None,
            'reimbursable_account_id': None,
            'default_ccc_account_name': None,
            'default_ccc_account_id': None
        }

        mapping_setting = MappingSetting.objects.filter(
            Q(destination_field='VENDOR') | Q(destination_field='EMPLOYEE'),
            source_field='EMPLOYEE', workspace_id=self.__workspace_id
        ).first()

        if mapping_setting.destination_field == 'VENDOR':
            assert_valid('accounts_payable_name' in general_mapping and general_mapping['accounts_payable_name'],
                         'account payable account name field is blank')
            assert_valid('accounts_payable_id' in general_mapping and general_mapping['accounts_payable_id'],
                         'account payable account id field is blank')

            params['accounts_payable_name'] = general_mapping.get('accounts_payable_name')
            params['accounts_payable_id'] = general_mapping.get('accounts_payable_id')

        if mapping_setting.destination_field == 'EMPLOYEE':
            assert_valid('reimbursable_account_name' in general_mapping and general_mapping['reimbursable_account_name'],
                         'reimbursable account name field is blank')
            assert_valid('reimbursable_account_id' in general_mapping and general_mapping['reimbursable_account_id'],
                         'reimbursable account id field is blank')

            params['reimbursable_account_name'] = general_mapping.get('reimbursable_account_name')
            params['reimbursable_account_id'] = general_mapping.get('reimbursable_account_id')

        if general_settings.corporate_credit_card_expenses_object:
            assert_valid('default_ccc_account_name' in general_mapping and general_mapping['default_ccc_account_name'],
                         'default ccc account name field is blank')
            assert_valid('default_ccc_account_id' in general_mapping and general_mapping['default_ccc_account_id'],
                         'default ccc account id field is blank')

            params['default_ccc_account_name'] = general_mapping.get('default_ccc_account_name')
            params['default_ccc_account_id'] = general_mapping.get('default_ccc_account_id')

        general_mapping_object, _ = GeneralMapping.objects.update_or_create(
            workspace_id=self.__workspace_id,
            defaults=params
        )

        return general_mapping_object
