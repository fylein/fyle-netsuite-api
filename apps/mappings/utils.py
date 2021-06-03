from typing import Dict

from django.db.models import Q

from fyle_accounting_mappings.models import MappingSetting

from apps.netsuite.tasks import schedule_vendor_payment_creation
from apps.workspaces.models import WorkspaceGeneralSettings
from fyle_netsuite_api.utils import assert_valid

from .models import GeneralMapping, SubsidiaryMapping
from .tasks import schedule_auto_map_ccc_employees


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

        assert_valid('location_id' in general_mapping, 'location id field is blank')
        assert_valid('location_name' in general_mapping, 'location name field is blank')
        assert_valid('location_level' in general_mapping, 'location level field is blank')

        if general_mapping['location_id'] and general_mapping['location_name']:
            assert_valid(general_mapping['location_level'] is not None, 'location level field is blank')

        params = {
            'location_name': general_mapping['location_name'],
            'location_id': general_mapping['location_id'],
            'location_level': general_mapping['location_level'],
            'department_id': None,
            'department_name': None,
            'accounts_payable_name': None,
            'accounts_payable_id': None,
            'reimbursable_account_name': None,
            'reimbursable_account_id': None,
            'default_ccc_account_name': None,
            'default_ccc_account_id': None,
            'default_ccc_vendor_name': None,
            'default_ccc_vendor_id': None
        }

        mapping_setting = MappingSetting.objects.filter(
            Q(destination_field='VENDOR') | Q(destination_field='EMPLOYEE'),
            source_field='EMPLOYEE', workspace_id=self.__workspace_id
        ).first()

        if general_settings.corporate_credit_card_expenses_object == 'BILL':
            assert_valid(
                'department_name' in general_mapping and general_mapping['department_name'],
                'department name field is blank'
            )
            assert_valid('department_id' in general_mapping and general_mapping['department_id'],
                         'department id field is blank')

            params['department_id'] = general_mapping.get('department_id')
            params['department_name'] = general_mapping.get('department_name')


        if mapping_setting.destination_field == 'VENDOR' or\
                general_settings.corporate_credit_card_expenses_object == 'BILL':
            assert_valid('accounts_payable_name' in general_mapping and general_mapping['accounts_payable_name'],
                         'account payable account name field is blank')
            assert_valid('accounts_payable_id' in general_mapping and general_mapping['accounts_payable_id'],
                         'account payable account id field is blank')

            params['accounts_payable_name'] = general_mapping.get('accounts_payable_name')
            params['accounts_payable_id'] = general_mapping.get('accounts_payable_id')

        if mapping_setting.destination_field == 'EMPLOYEE':
            assert_valid(
                'reimbursable_account_name' in general_mapping and general_mapping['reimbursable_account_name'],
                'reimbursable account name field is blank'
            )
            assert_valid('reimbursable_account_id' in general_mapping and general_mapping['reimbursable_account_id'],
                         'reimbursable account id field is blank')

            params['reimbursable_account_name'] = general_mapping.get('reimbursable_account_name')
            params['reimbursable_account_id'] = general_mapping.get('reimbursable_account_id')

        if general_settings.corporate_credit_card_expenses_object and\
                general_settings.corporate_credit_card_expenses_object != 'BILL':
            assert_valid('default_ccc_account_name' in general_mapping and general_mapping['default_ccc_account_name'],
                         'default ccc account name field is blank')
            assert_valid('default_ccc_account_id' in general_mapping and general_mapping['default_ccc_account_id'],
                         'default ccc account id field is blank')

            params['default_ccc_account_name'] = general_mapping.get('default_ccc_account_name')
            params['default_ccc_account_id'] = general_mapping.get('default_ccc_account_id')

        if general_settings.corporate_credit_card_expenses_object == 'BILL' or \
                general_settings.corporate_credit_card_expenses_object == 'CREDIT CARD CHARGE':
            assert_valid('default_ccc_vendor_name' in general_mapping and general_mapping['default_ccc_vendor_name'],
                         'default ccc vendor name field is blank')
            assert_valid('default_ccc_vendor_id' in general_mapping and general_mapping['default_ccc_vendor_id'],
                         'default ccc vendor id field is blank')

            params['default_ccc_vendor_name'] = general_mapping.get('default_ccc_vendor_name')
            params['default_ccc_vendor_id'] = general_mapping.get('default_ccc_vendor_id')

        if general_settings.sync_fyle_to_netsuite_payments:
            assert_valid(
                'vendor_payment_account_name' in general_mapping and general_mapping['vendor_payment_account_name'],
                'vendor payment account name field is blank')
            assert_valid(
                'vendor_payment_account_id' in general_mapping and general_mapping['vendor_payment_account_id'],
                'vendor payment account id field is blank')

            params['vendor_payment_account_name'] = general_mapping.get('vendor_payment_account_name')
            params['vendor_payment_account_id'] = general_mapping.get('vendor_payment_account_id')

        general_mapping_object, _ = GeneralMapping.objects.update_or_create(
            workspace_id=self.__workspace_id,
            defaults=params
        )

        schedule_vendor_payment_creation(
            sync_fyle_to_netsuite_payments=general_settings.sync_fyle_to_netsuite_payments,
            workspace_id=self.__workspace_id
        )

        if general_mapping_object.default_ccc_account_name:
            schedule_auto_map_ccc_employees(self.__workspace_id)

        return general_mapping_object
