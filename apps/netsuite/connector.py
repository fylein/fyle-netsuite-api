import re
import json
import copy
from random import randint
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import transaction
from django_q.tasks import async_task

from typing import List, Dict, Optional
import logging

from django.conf import settings
from django.db.models import Max


from requests_oauthlib import OAuth1Session

from apps.workspaces.helpers import get_app_name
from netsuitesdk import NetSuiteConnection, NetSuiteRequestError

import unidecode

from fyle_accounting_mappings.models import DestinationAttribute, ExpenseAttribute, MappingSetting

from apps.fyle.models import Expense, ExpenseGroup
from apps.workspaces.models import Configuration

from apps.mappings.models import SubsidiaryMapping, GeneralMapping
from apps.netsuite.models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, \
    JournalEntryLineItem, CustomSegment, VendorPayment, VendorPaymentLineitem, CreditCardChargeLineItem, \
    CreditCardCharge, get_tax_info
from apps.workspaces.models import NetSuiteCredentials, FyleCredential, Workspace

logger = logging.getLogger(__name__)
logger.level = logging.INFO

SYNC_UPPER_LIMIT = {
    'projects': 10000,
    'customers': 25000,
    'classes': 2000,
    'accounts': 2000,
    'locations': 2000,
    'departments': 2000,
    'vendors': 20000,
}


AttributeDisableCallbackPath = {
    'ACCOUNT': 'fyle_integrations_imports.modules.categories.disable_categories',
    'EXPENSE_CATEGORY': 'fyle_integrations_imports.modules.categories.disable_categories',
    'ITEM': 'fyle_integrations_imports.modules.categories.disable_categories',
    'VENDOR': 'fyle_integrations_imports.modules.merchants.disable_merchants',
    'PROJECT': 'fyle_integrations_imports.modules.projects.disable_projects',
    'COST_CENTER': 'fyle_integrations_imports.modules.cost_centers.disable_cost_centers'
}


class NetSuiteConnector:
    """
    NetSuite utility functions
    """

    def __init__(self, netsuite_credentials: NetSuiteCredentials, workspace_id: int,
                 search_body_fields_only: bool = True, page_size: int = 300):
        self.connection = NetSuiteConnection(
            account=netsuite_credentials.ns_account_id,
            consumer_key=netsuite_credentials.ns_consumer_key,
            consumer_secret=netsuite_credentials.ns_consumer_secret,
            token_key=netsuite_credentials.ns_token_id,
            token_secret=netsuite_credentials.ns_token_secret,
            search_body_fields_only=search_body_fields_only,
            page_size=page_size
        )

        self.__netsuite_credentials = netsuite_credentials

        self.workspace_id = workspace_id

    @staticmethod
    def __decode_project_or_customer_name(name):
        value = name.replace(u'\xa0', ' ')
        value = value.replace('/', '-')
        return value

    @staticmethod
    def get_message_and_code(raw_response):
        logger.info('Charge Card Error - %s', raw_response.text)
        try:
            return parse_error_and_get_message(raw_response=raw_response.text, get_code=True)
        except Exception as e:
            logger.info('Error while parsing error message - %s', e)
            raise

    @staticmethod
    def get_tax_code_name(item_id, tax_type, rate):
        if tax_type:
            return '{0}: {1} @{2}%'.format(tax_type, item_id, rate)
        else:
            return '{0} @{1}%'.format(item_id, rate)

    def is_sync_allowed(self, attribute_type: str, attribute_count: int) -> bool:
        """
        Checks if the sync is allowed based on attribute type and count.

        Args:
            attribute_type (str): Type of attribute to sync (e.g., 'projects', 'customers')
            attribute_count (int): Number of attributes to sync

        Returns:
            bool: True if sync is allowed, False otherwise

        Note:
            - For 'projects' and 'customers', sync is only allowed if count is within SYNC_UPPER_LIMIT
            - For other types, workspaces created after Oct 1, 2024 have stricter limits
        """
        if attribute_count <= SYNC_UPPER_LIMIT[attribute_type]:
            return True

        # Special handling for projects and customers
        if attribute_type in ['projects', 'customers']:
            return False

        # For other types, check workspace creation date
        workspace = Workspace.objects.get(id=self.workspace_id)
        cutoff_date = timezone.make_aware(
            datetime(2024, 10, 1),
            timezone.get_current_timezone()
        )
        return workspace.created_at <= cutoff_date

    def get_generator_params(self, attribute_type: str, display_name: str) -> dict:
        """
        Get Generator Params
        """
        params = {}
        latest_attribute = DestinationAttribute.objects.filter(workspace_id=self.workspace_id, attribute_type=attribute_type, display_name=display_name).order_by('-updated_at').first()

        if latest_attribute:
            params = {
                'last_modified_date': latest_attribute.updated_at
            }
        else:
            params = {
                'active': True
            }

        return params

    def is_import_enabled(self, attribute_type: str) -> bool:
        """
        Check if import is enabled for the attribute type
        :param attribute_type: Type of the attribute
        :return: Whether import is enabled
        """
        is_import_to_fyle_enabled = False

        configuration = Configuration.objects.filter(workspace_id=self.workspace_id).first()
        if not configuration:
            return is_import_to_fyle_enabled

        if attribute_type in ['ACCOUNT', 'EXPENSE_CATEGORY'] and configuration.import_categories:
            is_import_to_fyle_enabled = True

        elif attribute_type == 'VENDOR' and configuration.import_vendors_as_merchants:
            is_import_to_fyle_enabled = True

        elif attribute_type == 'ITEM' and configuration.import_items:
            is_import_to_fyle_enabled = True

        elif attribute_type == 'EMPLOYEE' and configuration.import_netsuite_employees:
            is_import_to_fyle_enabled = True

        elif attribute_type in ['PROJECT', 'DEPARTMENT', 'LOCATION', 'CLASS', 'CUSTOMER']:
            mapping_setting = MappingSetting.objects.filter(workspace_id=self.workspace_id, destination_field=attribute_type).first()
            if mapping_setting and mapping_setting.import_to_fyle:
                is_import_to_fyle_enabled = True

        return is_import_to_fyle_enabled

    def get_attribute_disable_callback_path(self, attribute_type: str) -> Optional[str]:
        """
        Get the attribute disable callback path
        :param attribute_type: Type of the attribute
        :return: attribute disable callback path or none
        """
        if attribute_type in ['ACCOUNT', 'EXPENSE_CATEGORY', 'ITEM', 'VENDOR']:
            return AttributeDisableCallbackPath.get(attribute_type)

        mapping_setting = MappingSetting.objects.filter(
            workspace_id=self.workspace_id,
            destination_field=attribute_type
        ).first()

        if mapping_setting and not mapping_setting.is_custom:
            return AttributeDisableCallbackPath.get(mapping_setting.source_field)

    def is_duplicate_deletion_skipped(self, attribute_type: str) -> bool:
        """
        Check if duplicate deletion is skipped for the attribute type
        :param attribute_type: Type of the attribute
        :return: Whether deletion is skipped
        """
        if attribute_type in [
            'ACCOUNT', 'EXPENSE_CATEGORY',
            'VENDOR', 'PROJECT', 'ITEM', 'DEPARTMENT',
            'LOCATION', 'CLASS', 'CUSTOMER'
        ]:
            return False

        return True

    def sync_accounts(self):
        """
        Sync accounts
        """
        attribute_count = self.connection.accounts.count()
        if not self.is_sync_allowed(attribute_type = 'accounts', attribute_count=attribute_count):
            logger.info('Skipping sync of accounts for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return
        accounts_generator = self.connection.accounts.get_all_generator()
        for accounts in accounts_generator:
            attributes = {
                'bank_account': [],
                'credit_card_account': [],
                'accounts_payable': [],
                'account': [],
                'ccc_account': [],
                'vendor_payment_account': []
            }
            destination_ids = DestinationAttribute.objects.filter(workspace_id=self.workspace_id,
                attribute_type='ACCOUNT', display_name='Account').values_list('destination_id', flat=True)

            for account in list(accounts):
                if account['acctType'] != '_expense':
                    attributes['bank_account'].append({
                        'attribute_type': 'BANK_ACCOUNT',
                        'display_name': 'Bank Account',
                        'value': account['acctName'],
                        'destination_id': account['internalId'],
                        'active': not account['isInactive']
                    })

                    if account['acctType'] == '_creditCard':
                        attributes['credit_card_account'].append({
                            'attribute_type': 'CREDIT_CARD_ACCOUNT',
                            'display_name': 'Credit Card Account',
                            'value': account['acctName'],
                            'destination_id': account['internalId'],
                            'detail': {
                                'account_type': account['acctType']
                            },
                            'active': not account['isInactive']
                        })

                if account['acctType'] == '_accountsPayable':
                    attributes['accounts_payable'].append({
                        'attribute_type': 'ACCOUNTS_PAYABLE',
                        'display_name': 'Accounts Payable',
                        'value': account['acctName'],
                        'destination_id': account['internalId'],
                        'active': not account['isInactive']
                    })

                if account['acctType'] in ['_expense', '_costOfGoodsSold', '_otherCurrentAsset', '_otherExpense',
                    '_fixedAsset', '_deferredExpense', '_otherCurrentLiability', '_income', '_otherAsset']:
                    if account['internalId'] in destination_ids:
                        attributes['account'].append({
                            'attribute_type': 'ACCOUNT',
                            'display_name': 'Account',
                            'value': unidecode.unidecode(u'{0}'.format(account['acctName'])).replace('/', '-'),
                            'destination_id': account['internalId'],
                            'active': not account['isInactive']
                        })
                    elif not account['isInactive']:
                        attributes['account'].append({
                            'attribute_type': 'ACCOUNT',
                            'display_name': 'Account',
                            'value': unidecode.unidecode(u'{0}'.format(account['acctName'])).replace('/', '-'),
                            'destination_id': account['internalId'],
                            'active': True
                        })

                if account['acctType'] == '_bank' or account['acctType'] == '_creditCard':
                    attributes['vendor_payment_account'].append({
                        'attribute_type': 'VENDOR_PAYMENT_ACCOUNT',
                        'display_name': 'Vendor Payment Account',
                        'value': account['acctName'],
                        'destination_id': account['internalId'],
                        'active': not account['isInactive']
                    })

            for attribute_type, attribute in attributes.items():
                if attribute:
                    DestinationAttribute.bulk_create_or_update_destination_attributes(
                        attribute, attribute_type.upper(), self.workspace_id, True, attribute_type.title().replace('_',' '),
                        skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='ACCOUNT'),
                        app_name=get_app_name(),
                        attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='ACCOUNT'),
                        is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='ACCOUNT')
                    )

        return []

    def sync_expense_categories(self):
        """
        Sync Expense Categories
        """
        categories_generator = self.connection.expense_categories.get_all_generator()
        is_expense_category_import_enabled = self.is_import_enabled(attribute_type='EXPENSE_CATEGORY')

        for categories in categories_generator:
            attributes = {
                'expense_category': [],
                'ccc_expense_category': []
            }
            destination_ids = DestinationAttribute.objects.filter(workspace_id=self.workspace_id,
                    attribute_type='EXPENSE_CATEGORY', display_name='Expense Category').values_list('destination_id', flat=True)

            for category in categories:
                detail = {
                    'account_name': category['expenseAcct']['name'],
                    'account_internal_id': category['expenseAcct']['internalId']
                }

                if category['internalId'] in destination_ids:
                    attributes['expense_category'].append(
                        {
                            'attribute_type': 'EXPENSE_CATEGORY',
                            'display_name': 'Expense Category',
                            'value': unidecode.unidecode(u'{0}'.format(category['name'])).replace('/', '-'),
                            'destination_id': category['internalId'],
                            'detail': detail,
                            'active': not category['isInactive']
                        }
                    )
                elif not category['isInactive']:
                    attributes['expense_category'].append(
                        {
                            'attribute_type': 'EXPENSE_CATEGORY',
                            'display_name': 'Expense Category',
                            'value': unidecode.unidecode(u'{0}'.format(category['name'])).replace('/', '-'),
                            'destination_id': category['internalId'],
                            'detail': detail,
                            'active': True
                        }
                    )

            for attribute_type, attribute in attributes.items():
                DestinationAttribute.bulk_create_or_update_destination_attributes(
                    attribute, attribute_type.upper(), self.workspace_id, True,
                    skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='EXPENSE_CATEGORY'),
                    app_name=get_app_name(),
                    attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='EXPENSE_CATEGORY'),
                    is_import_to_fyle_enabled=is_expense_category_import_enabled
                )

        if not is_expense_category_import_enabled:
            async_task(
                'apps.mappings.tasks.check_and_create_ccc_mappings',
                workspace_id=self.workspace_id,
                q_options={
                    'cluster': 'import'
                }
            )

        return []

    def sync_items(self):
        """
        Sync Items
        """

        item_generator = self.connection.items.get_all_generator()
        for items in item_generator:
            attributes = []

            destination_attributes = DestinationAttribute.objects.filter(workspace_id=self.workspace_id,
                attribute_type='ACCOUNT', display_name='Item').values('destination_id', 'value')
            configuration = Configuration.objects.filter(workspace_id=self.workspace_id).first()

            disabled_fields_map = {}
            for destination_attribute in destination_attributes:
                disabled_fields_map[destination_attribute['destination_id']] = {
                    'value': destination_attribute['value']
                }

            for item in items:
                if not item['isInactive']:
                    attributes.append({
                            'attribute_type': 'ACCOUNT',
                            'display_name': 'Item',
                            'value': item['itemId'],
                            'destination_id': item['internalId'],
                            'active': configuration.import_items if configuration else False
                        })
                    # the category is active so remove it from the map
                    if item['internalId'] in disabled_fields_map:
                        disabled_fields_map.pop(item['internalId'])

            for destination_id in disabled_fields_map:
                    attributes.append({
                        'attribute_type': 'ACCOUNT',
                        'display_name': 'Item',
                        'value': disabled_fields_map[destination_id]['value'],
                        'destination_id': destination_id,
                        'active': False
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'ACCOUNT', self.workspace_id, True, 'Item',
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='ITEM'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='ITEM'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='ITEM')
            )

        return []


    def get_custom_list_attributes(self, attribute_type: str, internal_id:str):
        custom_segment_attributes = []
        custom_lists = self.connection.custom_lists.get(internal_id)

        # Get all the current destination attributes
        destination_attributes = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type= attribute_type
        ).values('destination_id', 'value')

        # Create a map of destination_id and value
        disabled_fields_map = {}

        for destination_attribute in destination_attributes:
            disabled_fields_map[destination_attribute['destination_id']] = {
                'value': destination_attribute['value']
            }

        for field in custom_lists['customValueList']['customValue']:
            custom_segment_attributes.append(
                {
                    'attribute_type': attribute_type,
                    'display_name': custom_lists['name'],
                    'value': field['value'],
                    'destination_id': str(field['valueId']),
                    'active': not field['isInactive']
                }
            )

            # Pop the value from the map if it exists
            if str(field['valueId']) in disabled_fields_map:
                disabled_fields_map.pop(str(field['valueId']))

        # Add the disabled fields to the list
        for key, value in disabled_fields_map.items():
            custom_segment_attributes.append(
                {
                    'attribute_type': attribute_type,
                    'display_name': custom_lists['name'],
                    'value': value['value'],
                    'destination_id': key,
                    'active': False
                }
            )

        return custom_segment_attributes

    def get_custom_segment_attributes(self, attribute_type: str, internal_id: str):
        custom_segment_attributes = []
        custom_segments = self.connection.custom_segments.get(internal_id)

        record_id = custom_segments['recordType']['internalId']

        custom_records = self.connection.custom_record_types.get_all_by_id(record_id)

        # Get all the current destination attributes
        destination_attributes = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type= attribute_type
        ).values('destination_id', 'value')

        # Create a map of destination_id and value
        disabled_fields_map = {}

        for destination_attribute in destination_attributes:
            disabled_fields_map[destination_attribute['destination_id']] = {
                'value': destination_attribute['value']
            }

        for field in custom_records:
            custom_segment_attributes.append(
                {
                    'attribute_type': attribute_type,
                    'display_name': custom_records[0]['recType']['name'],
                    'value': field['name'],
                    'destination_id': field['internalId'],
                    'active': not field['isInactive']
                }
            )

            # Pop the value from the map if it exists
            if field['internalId'] in disabled_fields_map:
                disabled_fields_map.pop(field['internalId'])

        # Add the disabled fields to the list
        for key, value in disabled_fields_map.items():
            custom_segment_attributes.append(
                {
                    'attribute_type': attribute_type,
                    'display_name': custom_records[0]['recType']['name'],
                    'value': value['value'],
                    'destination_id': key,
                    'active': False
                }
            )

        return custom_segment_attributes
    
    def update_destination_attributes(self, attribute_type:str, custom_records: List):
        """
            Sometime custom_attributes internal_id change due to some reason
            we update destination_attributes accordingly.
        """
        changed_destination_attributes = []
        custom_segment_attributes = []

        
        value_to_attribute_map = {}
        
        for field in custom_records:
            attribute_data = {
                'attribute_type': attribute_type,
                'display_name': custom_records[0]['recType']['name'],
                'value': field['name'],
                'destination_id': field['internalId'],
                'active': not field['isInactive']
            }
        
            value_to_attribute_map[field['name']] = attribute_data
        
        custom_segment_attributes = list(value_to_attribute_map.values())

        for custom_segment_attribute in custom_segment_attributes:
            existing = DestinationAttribute.objects.filter(
                attribute_type=custom_segment_attribute['attribute_type'],
                value=custom_segment_attribute['value'],
                workspace_id=self.workspace_id
            ).first()
            if existing and existing.destination_id != custom_segment_attribute['destination_id']:
                changed_destination_attributes.append((existing.id, existing.destination_id, custom_segment_attribute['destination_id']))

        if not changed_destination_attributes:
            return

        temp_internal_id_base = 'temp_id'
        temp_internal_ids = {}
        destination_attributes_to_be_updated = []

        for i, (record_id, old_id, new_id) in enumerate(changed_destination_attributes):
            temp_id = f"{temp_internal_id_base}_{i}"
            temp_internal_ids[record_id] = (temp_id, new_id)
            destination_attributes_to_be_updated.append(DestinationAttribute(id=record_id, destination_id=temp_id, workspace_id=self.workspace_id, updated_at=datetime.now(timezone.utc)))

        with transaction.atomic():
            DestinationAttribute.objects.bulk_update(destination_attributes_to_be_updated, ['destination_id', 'updated_at'], batch_size=100)

            updated_destination_attributes = [
                DestinationAttribute(id=record_id, destination_id=new_id, workspace_id=self.workspace_id, updated_at=datetime.now(timezone.utc))
                for record_id, (temp_id, new_id) in temp_internal_ids.items()
            ]
            
            DestinationAttribute.objects.bulk_update(updated_destination_attributes, ['destination_id', 'updated_at'], batch_size=100)

    def get_custom_record_attributes(self, attribute_type: str, internal_id: str):
        custom_segment_attributes = {}
        custom_records = self.connection.custom_record_types.get_all_by_id(internal_id)

        self.update_destination_attributes(attribute_type=attribute_type, custom_records=custom_records)

        # Get all the current destination attributes
        destination_attributes = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type= attribute_type
        ).values('destination_id', 'value')

        # Create a map of destination_id and value
        disabled_fields_map = {}

        for destination_attribute in destination_attributes:
            disabled_fields_map[destination_attribute['destination_id']] = {
                'value': destination_attribute['value']
            }

        for field in custom_records:
            custom_segment_attributes[field['name']] = {
                'attribute_type': attribute_type,
                'display_name': custom_records[0]['recType']['name'],
                'value': field['name'],
                'destination_id': field['internalId'],
                'active': not field['isInactive']
            }

            # Pop the value from the map if it exists
            if field['internalId'] in disabled_fields_map:
                disabled_fields_map.pop(field['internalId'])

        # Add the disabled fields to the list
        for key, value in disabled_fields_map.items():
            if value not in custom_segment_attributes:
                custom_segment_attributes[value['value']] = {
                    'attribute_type': attribute_type,
                    'display_name': custom_records[0]['recType']['name'],
                    'value': value['value'],
                    'destination_id': key,
                    'active': False
                }

        return list(custom_segment_attributes.values())

    def sync_custom_segments(self):
        """
        Sync Custom Segments
        """
        custom_segments: List[CustomSegment] = CustomSegment.objects.filter(workspace_id=self.workspace_id).all()

        for custom_segment in custom_segments:
            attribute_type = custom_segment.name.upper().replace(' ', '_')
            if attribute_type in ('LOCATION', 'DEPARTMENT', 'CLASS'):
                attribute_type = '{}-CS'.format(attribute_type)

            if custom_segment.segment_type == 'CUSTOM_LIST':
                custom_segment_attributes = self.get_custom_list_attributes(attribute_type, custom_segment.internal_id)

            if custom_segment.segment_type == 'CUSTOM_SEGMENT':
                custom_segment_attributes = self.get_custom_segment_attributes(attribute_type, custom_segment.internal_id)

            elif custom_segment.segment_type == 'CUSTOM_RECORD':
                custom_segment_attributes = self.get_custom_record_attributes(
                    attribute_type, custom_segment.internal_id)

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                custom_segment_attributes, attribute_type, self.workspace_id, True)

        return []

    def sync_currencies(self):
        """
        Sync Currencies
        """
        currencies_generator = self.connection.currencies.get_all_generator()

        currency_attributes = []

        for currency in currencies_generator:
                currency_attributes.append(
                    {
                        'attribute_type': 'CURRENCY',
                        'display_name': 'Currency',
                        'value': currency['symbol'],
                        'destination_id': currency['internalId'],
                        'active': True
                    }
                )

        DestinationAttribute.bulk_create_or_update_destination_attributes(
            currency_attributes, 'CURRENCY', self.workspace_id, True)

        return []

    def sync_locations(self):
        """
        Sync locations
        """
        attribute_count = self.connection.locations.count()
        if not self.is_sync_allowed(attribute_type = 'locations', attribute_count = attribute_count):
            logger.info('Skipping sync of locations for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return

        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        location_generator = self.connection.locations.get_all_generator()

        location_attributes = []

        destination_ids = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type='LOCATION',
            display_name='Location'
        ).values_list('destination_id', flat=True)

        for locations in location_generator:
            for location in locations:
                if location['isInactive'] and location['internalId'] not in destination_ids:
                    continue

                if 'subsidiaryList' in location and location['subsidiaryList']:
                    subsidiaries = location['subsidiaryList']['recordRef']
                    counter = 0
                    if subsidiaries[counter]['internalId'] == subsidiary_mapping.internal_id:
                        counter += 1
                        location_attributes.append({
                            'attribute_type': 'LOCATION',
                            'display_name': 'Location',
                            'value': location['name'],
                            'destination_id': location['internalId'],
                            'active': not location['isInactive']
                        })
                else:
                    location_attributes.append({
                        'attribute_type': 'LOCATION',
                        'display_name': 'Location',
                        'value': location['name'],
                        'destination_id': location['internalId'],
                        'active': not location['isInactive']
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                location_attributes, 'LOCATION', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='LOCATION'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='LOCATION'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='LOCATION')
            )

        return []

    def sync_classifications(self):
        """
        Sync classification
        """
        configuration = Configuration.objects.filter(workspace_id=self.workspace_id).first()
        attribute_count = self.connection.classifications.count()
        if not self.is_sync_allowed(attribute_type = 'classes', attribute_count = attribute_count):
            logger.info('Skipping sync of classes for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return

        classification_generator = self.connection.classifications.get_all_generator()

        classification_attributes = []

        destination_ids = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type='CLASS',
            display_name='Class'
        ).values_list('destination_id', flat=True)

        for classifications in classification_generator:
            for classification in classifications:
                if classification['isInactive'] and classification['internalId'] not in destination_ids:
                    continue

                value = classification['name']
                if configuration and configuration.import_classes_with_parent and classification['parent']:
                    value = f"{classification['parent']['name']} : {classification['name']}"

                classification_attributes.append({
                    'attribute_type': 'CLASS',
                    'display_name': 'Class',
                    'value': value,
                    'destination_id': classification['internalId'],
                    'active': not classification['isInactive']
                })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                classification_attributes, 'CLASS', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='CLASS'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='CLASS'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='CLASS')
            )

        return []

    def sync_departments(self):
        """
        Sync departments
        """
        attribute_count = self.connection.departments.count()
        if not self.is_sync_allowed(attribute_type = 'departments', attribute_count = attribute_count):
            logger.info('Skipping sync of department for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return
        department_generator = self.connection.departments.get_all_generator()

        department_attributes = []

        destination_ids = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type='DEPARTMENT',
            display_name='Department'
        ).values_list('destination_id', flat=True)

        for departments in department_generator:
            for department in departments:
                if department['isInactive'] and department['internalId'] not in destination_ids:
                    continue

                department_attributes.append({
                    'attribute_type': 'DEPARTMENT',
                    'display_name': 'Department',
                    'value': department['name'],
                    'destination_id': department['internalId'],
                    'active': not department['isInactive']
                })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                department_attributes, 'DEPARTMENT', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='DEPARTMENT'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='DEPARTMENT'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='DEPARTMENT')
            )

        return []

    def sync_vendors(self):
        """
        Sync vendors
        """
        attribute_count = self.connection.vendors.count()
        if not self.is_sync_allowed(attribute_type = 'vendors', attribute_count=attribute_count):
            logger.info('Skipping sync of vendors for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return

        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)
        configuration = Configuration.objects.filter(workspace_id=self.workspace_id).first()
        if not configuration:
            configuration = Configuration(
                workspace_id=self.workspace_id,
                allow_intercompany_vendors=False
            )

        params = self.get_generator_params(attribute_type='VENDOR', display_name='Vendor')

        vendors_generator = self.connection.vendors.get_records_generator(**params)

        for vendors in vendors_generator:
            attributes = []
            for vendor in vendors:
                detail = {
                    'email': vendor['email'] if vendor['email'] else None
                }
                if 'subsidiary' in vendor and vendor['subsidiary']:
                    if vendor['subsidiary']['internalId'] == subsidiary_mapping.internal_id or configuration.allow_intercompany_vendors:
                        attributes.append({
                            'attribute_type': 'VENDOR',
                            'display_name': 'Vendor',
                            'value': unidecode.unidecode(u'{0}'.format(vendor['entityId'])),
                            'destination_id': vendor['internalId'],
                            'detail': detail,
                            'active': not vendor['isInactive']
                        })
                else:
                    attributes.append({
                        'attribute_type': 'VENDOR',
                        'display_name': 'Vendor',
                        'value': unidecode.unidecode(u'{0}'.format(vendor['entityId'])),
                        'destination_id': vendor['internalId'],
                        'detail': detail,
                        'active': not vendor['isInactive']
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'VENDOR', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='VENDOR'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='VENDOR'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='VENDOR')
            )

        return []

    def post_vendor(self, expense_group: ExpenseGroup, vendor: ExpenseAttribute = None, merchant: str = None):
        """
        Create an Vendor on NetSuite
        :param expense_group: expense group
        :param vendor: vendor attribute to be created
        :param merchant: merchant to be created
        :return: Vendor Destination Attribute
        """
        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        expense = expense_group.expenses.first()

        currency = DestinationAttribute.objects.filter(value=expense.currency,
                                                    workspace_id=expense_group.workspace_id,
                                                    attribute_type='CURRENCY').first()

        netsuite_entity_id = vendor.detail['full_name'] if vendor else merchant

        last_name = None
        if vendor:
            last_name = netsuite_entity_id.split(' ')[-1] if len(netsuite_entity_id.split(' ')) > 1 \
                else netsuite_entity_id

        vendor = {
            'firstName': netsuite_entity_id.split(' ')[0] if vendor else None,
            'lastName': last_name,
            'isPerson': True if vendor else False,
            'entityId': netsuite_entity_id,
            'email': vendor.value if vendor else None,
            'companyName': merchant if merchant else None,
            'currency': {
                "name": None,
                "internalId": currency.destination_id if currency else '1',
                "externalId": None,
                "type": "currency"
            },
            'representingSubsidiary': {
                "name": None,
                "internalId": subsidiary_mapping.internal_id,
                "externalId": None,
                "type": None
            },
            'subsidiary': {
                'name': None,
                'internalId': subsidiary_mapping.internal_id,
                'externalId': None,
                'type': None
            },
            'workCalendar': {
                "name": None,
                "internalId": None,
                "externalId": None,
                "type": None
            },
            'externalId': vendor.detail['user_id'] if vendor else merchant
        }

        attempted_modifications = {
            'representingSubsidiary': False,
            'isPerson': False,
            'entityId': False,
            'updateExternalId': False
        }
        
        max_retries = 4
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info('Vendor Post Payload for workspace_id: %s, expense_group: %s, payload: %s',
                    self.workspace_id,
                    expense_group.id,
                    vendor
                )
                vendor_response = self.connection.vendors.post(vendor)
                return vendor_response
                
            except NetSuiteRequestError as exception:
                retry_count += 1
                logger.info('Error in creating vendor (attempt %s of %s): %s',
                            retry_count, max_retries, {'error': exception})
                
                detail = exception.args[0] if exception.args else {}
                if isinstance(detail, dict):
                    error_message = detail.get('message', '')
                else:
                    error_message = detail

                modified = False
                
                if ('representingsubsidiary' in error_message or 'Represents Subsidiary must be different than Subsidiary' in error_message) and not attempted_modifications['representingSubsidiary']:
                    vendor['representingSubsidiary']['internalId'] = None
                    attempted_modifications['representingSubsidiary'] = True
                    modified = True
                    logger.info('Retrying vendor creation without representingSubsidiary')
                    
                
                elif 'isperson' in error_message and not attempted_modifications['isPerson']:
                    if 'isPerson' in vendor:
                        del vendor['isPerson']
                    attempted_modifications['isPerson'] = True
                    modified = True
                    logger.info('Retrying vendor creation without isPerson')
                    
                elif 'entityid' in error_message and not attempted_modifications['entityId']:
                    vendor['entityId'] = None
                    attempted_modifications['entityId'] = True
                    modified = True
                    logger.info('Retrying vendor creation without entityId')

                elif 'That record does not exist' in error_message and not attempted_modifications['updateExternalId']:
                    vendor['externalId'] = '{}_{}'.format(vendor['externalId'], randint(1, 100))
                    attempted_modifications['updateExternalId'] = True
                    modified = True
                    logger.info('Retrying vendor creation with updated externalId')

                if not modified or retry_count >= max_retries:
                    logger.info('Failed to create vendor after %s attempts', retry_count)
                    raise

    def sync_employees(self):
        """
        Sync employees
        """
        configuration = Configuration.objects.filter(workspace_id=self.workspace_id).first()

        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        max_updated_at = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id,
            attribute_type='EMPLOYEE').all().aggregate(
            max_updated_at=Max('updated_at')
        )['max_updated_at']

        last_modified_date_query = {}

        if max_updated_at:
            search_value = (max_updated_at - timedelta(days=30)).isoformat()

            last_modified_date_query['search_value'] = search_value
            last_modified_date_query['operator'] ='onOrAfter'

        employees_generator = self.connection.employees.get_all_generator(
            last_modified_date_query=last_modified_date_query,
            page_size=200
        )

        for employees in employees_generator:
            attributes = []
            for employee in employees:
                allow_access_to_fyle = False
                for field in employee['customFieldList']['customField']:    # Check if Allow access to fyle is enabled
                    if field['scriptId'] == 'custentityallow_fyle_access' and field['value']:
                        allow_access_to_fyle = True

                supervisor = []
                if configuration and configuration.import_netsuite_employees:
                    if employee['supervisor']:
                        supervisor.append(self.connection.employees.get(
                            employee['supervisor']['internalId'], employee['supervisor']['externalId'])['email'])

                parent_department = None
                if employee['department']:
                    if len(employee['department']['name'].split(':')) > 1:
                        parent_department = employee['department']['name'].split(':')[0].strip()

                detail = {
                    'email': employee['email'] if employee['email'] else None,
                    'department_id': employee['department']['internalId'] if employee['department'] else None,
                    'location_id': employee['location']['internalId'] if employee['location'] else None,
                    'class_id': employee['class']['internalId'] if employee['class'] else None,
                    'department_name': employee['department']['name'].split(':')[-1].strip() if employee['department'] else None,
                    'parent_department': parent_department,
                    'location_name': employee['location']['name'] if employee['location'] else None,
                    'full_name': ' '.join(filter(None, [employee['firstName'], employee['middleName'], employee['lastName']])),
                    'joined_at': employee['dateCreated'].isoformat(timespec='milliseconds') if employee['dateCreated'] else None,
                    'title': employee['title'] if employee['title'] else None,
                    'mobile': '+{}'.format(re.sub('\D', '', employee['mobilePhone'])) if employee['mobilePhone'] else None,
                    'approver_emails': supervisor,
                    'allow_access_to_fyle': allow_access_to_fyle
                }

                active_status = False if employee['isInactive'] else True
                if employee['releaseDate']:
                    if employee['releaseDate'].isoformat(timespec='milliseconds') < datetime.now().isoformat(timespec='milliseconds'):
                        active_status = False

                if 'subsidiary' in employee and employee['subsidiary']:
                    if employee['subsidiary']['internalId'] == subsidiary_mapping.internal_id:
                        attributes.append({
                            'attribute_type': 'EMPLOYEE',
                            'display_name': 'Employee',
                            'value': employee['entityId'],
                            'destination_id': employee['internalId'],
                            'detail': detail,
                            'active': active_status
                        })
                else:
                    attributes.append({
                        'attribute_type': 'EMPLOYEE',
                        'display_name': 'Employee',
                        'value': employee['entityId'],
                        'destination_id': employee['internalId'],
                        'detail': detail,
                        'active': active_status
                    })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'EMPLOYEE', self.workspace_id, True,
                    skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='EMPLOYEE'),
                    app_name=get_app_name(),
                    attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='EMPLOYEE'),
                    is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='EMPLOYEE')
                )

        return []

    def create_destination_attribute(self, attribute: str, name: str, destination_id: str, email: str = None):
        created_attribute = DestinationAttribute.create_or_update_destination_attribute({
            'attribute_type': attribute.upper(),
            'display_name': attribute,
            'value': name,
            'destination_id': destination_id,
            'detail': {
                'email': email
            },
            'active': True
        }, self.workspace_id)

        return created_attribute

    def get_or_create_vendor(self, expense_attribute: ExpenseAttribute, expense_group: ExpenseGroup):
        vendors = self.connection.vendors.search(
            attribute='entityId', value=expense_attribute.detail['full_name'], operator='is')

        active_vendors = list(filter(lambda vendor: not vendor['isInactive'], vendors)) if vendors else []

        if not active_vendors:
            created_vendor = self.post_vendor(expense_group, expense_attribute)
            return self.create_destination_attribute(
                'vendor', expense_attribute.detail['full_name'], created_vendor['internalId'], expense_attribute.value)
        else:
            vendor = active_vendors[0]
            return self.create_destination_attribute(
                'vendor', vendor['entityId'], vendor['internalId'], vendor['email'])

    def get_or_create_employee(self, expense_attribute: ExpenseAttribute, expense_group: ExpenseGroup):
        employee = self.connection.employees.search(
            attribute='entityId', value=expense_attribute.detail['full_name'], operator='is'
        )

        if not employee:
            created_employee = self.post_employee(expense_attribute, expense_group)
            return self.create_destination_attribute(
                'employee', expense_attribute.detail['full_name'], created_employee['internalId'],
                expense_attribute.value
            )
        else:
            employee = employee[0]
            return self.create_destination_attribute(
                'employee', employee['entityId'], employee['internalId'], employee['email']
            )

    def post_employee(self, employee: ExpenseAttribute, expense_group: ExpenseGroup):
        """
        Create an Employee on NetSuite
        :param expense_group: expense group
        :param employee: employee attribute to be created
        :return: Employee Destination Attribute
        """
        department = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id, attribute_type='DEPARTMENT',
            value__iexact=employee.detail['department']).first()

        location = DestinationAttribute.objects.filter(
            workspace_id=self.workspace_id, attribute_type='LOCATION',
            value__iexact=employee.detail['location']).first()

        subsidiary_mapping = SubsidiaryMapping.objects.get(workspace_id=self.workspace_id)

        expense = expense_group.expenses.first()

        currency = DestinationAttribute.objects.filter(
            value=expense.currency, workspace_id=self.workspace_id, attribute_type='CURRENCY').first()

        employee_entity_id = employee.detail['full_name']

        employee = {
            'location': {
                'name': None,
                'internalId': location.destination_id if location else None,
                'externalId': None,
                'type': None
            },
            'department': {
                'name': None,
                'internalId': department.destination_id if department else None,
                'externalId': None,
                'type': None
            },
            'entityId': employee_entity_id,
            'email': employee.value,
            'firstName': employee_entity_id.split(' ')[0],
            'lastName': employee_entity_id.split(' ')[-1]
            if len(employee_entity_id.split(' ')) > 1 else '',
            'inheritIPRules': True,
            'payFrequency': None,
            'subsidiary': {
                'name': None,
                'internalId': subsidiary_mapping.internal_id,
                'externalId': None,
                'type': None
            },
            'workCalendar': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': None
            },
            'defaultExpenseReportCurrency': {
                'internalId': currency.destination_id if currency else '1',
                'externalId': None,
                'type': 'currency'
            },
            'externalId': employee.detail['user_id']
        }

        return self.connection.employees.post(employee)

    def sync_subsidiaries(self):
        """
        Sync subsidiaries
        """
        subsidiary_generator = self.connection.subsidiaries.get_all_generator()
        subsidiary_attributes = []

        for subsidiaries in subsidiary_generator:
            for subsidiary in subsidiaries:
                subsidiary_attributes.append({
                    'attribute_type': 'SUBSIDIARY',
                    'display_name': 'Subsidiary',
                    'value': subsidiary['name'],
                    'destination_id': subsidiary['internalId'],
                    'detail': {
                        'country': subsidiary['country']
                    },
                    'active': True
                })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                subsidiary_attributes, 'SUBSIDIARY', self.workspace_id, True)

        return []
    
    def get_tax_item_attributes(self, tax_rate, tax_item, value, is_overide_tax_details=False):
        if tax_rate >= 0:
            return ({
                'attribute_type': 'TAX_ITEM',
                'display_name': 'Tax Item',
                'value': value,
                'destination_id': tax_item['internalId'],
                'active': True,
                'detail': {
                    'tax_rate': tax_rate,
                    'tax_type_internal_id': tax_item['taxType']['internalId'] if is_overide_tax_details else None,
                    'tax_type_name': tax_item['taxType']['name'] if is_overide_tax_details else None
                }
            })
    
    def sync_tax_items(self):
        """
        Sync Tax Details
        """
        general_mapping = GeneralMapping.objects.filter(workspace_id=self.workspace_id).first()

        tax_items_generator = self.connection.tax_items.get_all_generator()

        if general_mapping and general_mapping.override_tax_details:
            for tax_items in tax_items_generator:
                tax_item_attributes = []
                for tax_item in tax_items:
                    tax_rate = -1
                    for fields in tax_item['customFieldList']['customField']:
                        if fields['scriptId'] == 'custrecord_ste_taxcode_taxrate':
                            tax_rate = float(fields['value'])
                    if not tax_item['isInactive'] and tax_item['name'] and tax_item['taxType'] and tax_rate:
                        value = self.get_tax_code_name(tax_item['name'], tax_item['taxType']['name'], tax_rate)
                        
                        destination_attribute = self.get_tax_item_attributes(tax_rate, tax_item, value, True)
                        if destination_attribute:
                            tax_item_attributes.append(destination_attribute)

                DestinationAttribute.bulk_create_or_update_destination_attributes(
                        tax_item_attributes, 'TAX_ITEM', self.workspace_id, True) 
        else:
            for tax_items in tax_items_generator:
                tax_item_attributes = []
                for tax_item in tax_items:
                    if not tax_item['isInactive'] and tax_item['itemId'] and tax_item['taxType'] and tax_item['rate']:
                        tax_rate = float(tax_item['rate'].replace('%', ''))
                        value = self.get_tax_code_name(tax_item['itemId'], tax_item['taxType']['name'], tax_rate)

                        destination_attribute = self.get_tax_item_attributes(tax_rate, tax_item, value)
                        if destination_attribute:
                            tax_item_attributes.append(destination_attribute)

                DestinationAttribute.bulk_create_or_update_destination_attributes(
                        tax_item_attributes, 'TAX_ITEM', self.workspace_id, True)    

            tax_groups_generator = self.connection.tax_groups.get_all_generator()
            for tax_groups in tax_groups_generator:
                tax_group_attributes = []
                for tax_group in tax_groups:
                    if not tax_group['isInactive'] and tax_group['itemId']:
                        if tax_group['nexusCountry'] and tax_group['nexusCountry']['internalId'] == 'CA':
                            unit_price1 = float(tax_group['unitprice1'][:-1] if tax_group['unitprice1'] else 0)
                            unit_price2 = float(tax_group['unitprice2'][:-1] if tax_group['unitprice2'] else 0)
                            tax_rate = unit_price1 + unit_price2
                        else:
                            tax_rate = float(tax_group['rate'] if tax_group['rate'] else 0)
                        tax_type = tax_group['taxType']['name'] if tax_group['taxType'] else None
                        value = self.get_tax_code_name(tax_group['itemId'], tax_type, tax_rate)
                        if tax_rate >= 0:
                            tax_group_attributes.append({
                                'attribute_type': 'TAX_ITEM',
                                'display_name': 'Tax Item',
                                'value': value,
                                'destination_id': tax_group['internalId'],
                                'active': True,
                                'detail': {
                                    'tax_rate': tax_rate if tax_rate >= 0 else 0
                                }
                            })

                DestinationAttribute.bulk_create_or_update_destination_attributes(
                        tax_group_attributes, 'TAX_ITEM', self.workspace_id, True)

        return []

    def sync_projects(self):
        """
        Sync projects
        """
        attribute_count = self.connection.projects.count()
        if not self.is_sync_allowed(attribute_type = 'projects', attribute_count = attribute_count):
            logger.info('Skipping sync of projects for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return
        
        projects_generator = self.connection.projects.get_all_generator()
        for projects in projects_generator:
            attributes = []
            destination_ids = DestinationAttribute.objects.filter(
                workspace_id=self.workspace_id,
                attribute_type= 'PROJECT',
                display_name='Project'
            ).values_list('destination_id', flat=True)

            for project in projects:
                value = self.__decode_project_or_customer_name(project['entityId'])

                if project['internalId'] in destination_ids :
                    attributes.append({
                        'attribute_type': 'PROJECT',
                        'display_name': 'Project',
                        'value': value,
                        'destination_id': project['internalId'],
                        'active': not project['isInactive']
                    })
                elif not project['isInactive']:
                    attributes.append({
                        'attribute_type': 'PROJECT',
                        'display_name': 'Project',
                        'value': value,
                        'destination_id': project['internalId'],
                        'active': True
                    })
            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'PROJECT', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='PROJECT'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='PROJECT'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='PROJECT')
            )

        return []

    def sync_customers(self):
        """
        Sync customers
        """
        attribute_count = self.connection.customers.count()
        if not self.is_sync_allowed(attribute_type = 'customers', attribute_count = attribute_count):
            logger.info('Skipping sync of customers for workspace %s as it has %s counts which is over the limit', self.workspace_id, attribute_count)
            return

        params = self.get_generator_params(attribute_type='PROJECT', display_name='Customer')

        customers_generator = self.connection.customers.get_records_generator(**params)

        for customers in customers_generator:
            attributes = []
            for customer in customers:
                value = self.__decode_project_or_customer_name(customer['entityId'])
                attributes.append({
                    'attribute_type': 'PROJECT',
                    'display_name': 'Customer',
                    'value': value,
                    'destination_id': customer['internalId'],
                    'active': not customer['isInactive']
                })

            DestinationAttribute.bulk_create_or_update_destination_attributes(
                attributes, 'PROJECT', self.workspace_id, True,
                skip_deletion=self.is_duplicate_deletion_skipped(attribute_type='PROJECT'),
                app_name=get_app_name(),
                attribute_disable_callback_path=self.get_attribute_disable_callback_path(attribute_type='PROJECT'),
                is_import_to_fyle_enabled=self.is_import_enabled(attribute_type='PROJECT')
            )

        return []

    def get_accounting_fields(self, resource_type: str, internal_id: str):
        """
        Retrieve accounting fields for a specific resource type and internal ID.

        Args:
            resource_type (str): The type of resource to fetch.
            internal_id (str): The internal ID of the resource.

        Returns:
            list or dict: Parsed JSON representation of the resource data.
        """
        module = getattr(self.connection, resource_type)
        method_map = {
            'currencies': 'get_all',
            'custom_segments': 'get',
            'custom_lists': 'get',
            'custom_record_types': 'get_all_by_id',
        }
        method = method_map.get(resource_type, 'get_all_generator')

        if method in ('get', 'get_all_by_id'):
            response = getattr(module, method)(internal_id)
        else:
            response = getattr(module, method)()

        if method == 'get_all_generator':
            response = [row for responses in response for row in responses]

        return json.loads(json.dumps(response, default=str))

    def get_exported_entry(self, resource_type: str, export_id: str):
        module = getattr(self.connection, resource_type)
        response = getattr(module, 'get')(export_id)
        return json.loads(json.dumps(response, default=str))

    def handle_taxed_line_items(self, base_line, line, workspace_id, export_module, general_mapping: GeneralMapping):
        """
        Handle line items where tax is applied or modified by the user.
        :param base_line: The base line item template that will be modified.
        :param line: The original line with tax and amount information.
        :param is_credit_card_charge: Boolean flag to differentiate between credit card charges and other transactions.
        :return: List of lines (taxed and/or untaxed).
        """
        tax_item = DestinationAttribute.objects.filter(
            workspace_id=workspace_id,
            attribute_type='TAX_ITEM',
            destination_id=str(line.tax_item_id)
        ).first()
        tax_item_rate = tax_item.detail['tax_rate']

        lines = []
        original_amount = round(line.amount, 2)
        expected_tax_amount = round((line.amount * (tax_item_rate / 100)) / (1 + (tax_item_rate / 100)), 2)

        if general_mapping.is_tax_balancing_enabled and abs(round(line.tax_amount, 2)) != expected_tax_amount:
            # Recalculate the net amount based on the modified tax
            recalculated_net_amount = round((line.tax_amount * 100) / tax_item_rate, 2) if tax_item_rate != 0 else 0
            untaxed_amount = round(original_amount - recalculated_net_amount - line.tax_amount, 2)

            # Create a taxable line item
            taxable_line = copy.deepcopy(base_line)
            taxable_line['amount'] = recalculated_net_amount
            taxable_line['taxCode']['internalId'] = line.tax_item_id

            # Create an untaxed line item
            untaxed_line = copy.deepcopy(base_line)
            untaxed_line['amount'] = untaxed_amount
            untaxed_line['taxCode']['internalId'] = general_mapping.default_tax_code_id  # Use default for untaxed items

            if export_module == 'JOURNAL_ENTRY':
                taxable_line['grossAmt'] = round(recalculated_net_amount + line.tax_amount, 2)
                taxable_line['debit'] = recalculated_net_amount
                taxable_line.pop('amount', None)
                untaxed_line['grossAmt'] = round(untaxed_amount, 2)
                untaxed_line['debit'] = untaxed_amount
                untaxed_line.pop('amount', None)
                taxable_line['tax1Amt'] = round(line.tax_amount, 2) # Tax is applied to this line
            
            if export_module == 'EXPENSE_REPORT':
                taxable_line['tax1Amt'] = round(line.tax_amount, 2) # Tax is applied to this line
                if recalculated_net_amount == 0:
                    taxable_line['foreignAmount'] = 0
                if untaxed_amount == 0:
                    untaxed_line['foreignAmount'] = 0

            if export_module == 'BILL' and taxable_line.get('rate'):
                taxable_line['rate'] = str(round(line.amount - line.tax_amount, 2))

            lines.append(taxable_line)
            lines.append(untaxed_line)
        else:
            # When the tax is not modified, just subtract the tax and apply it directly
            base_line['amount'] = round(original_amount - line.tax_amount, 2)
            base_line['taxCode']['internalId'] = line.tax_item_id
            
            if export_module == 'EXPENSE_REPORT':
                base_line['tax1Amt'] = round(line.tax_amount, 2)  # Tax is applied to this line
                if base_line['amount'] == 0:
                    base_line['foreignAmount'] = 0

            if export_module == 'BILL' and base_line.get('rate'):
                base_line['rate'] = str(round(line.amount - line.tax_amount, 2))

            if export_module == 'JOURNAL_ENTRY':
                base_line['tax1Amt'] = round(line.tax_amount, 2)  # Tax is applied to this line
                base_line['grossAmt'] = original_amount
                base_line['debit'] = round(original_amount - line.tax_amount, 2)
                base_line.pop('amount', None)

            lines.append(base_line)

        return lines
    
    def prepare_custom_segments(self, line_netsuite_custom_segments, attachment_links, expense, org_id, is_credit=False):
        """
        Prepare custom segments for line items.
        """
        netsuite_custom_segments = line_netsuite_custom_segments

        if attachment_links and expense.expense_id in attachment_links:
            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_receipt_link',
                    'type': 'String',
                    'value': attachment_links[expense.expense_id]
                }
            )
            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_receipt_link_2',
                    'type': 'String',
                    'value': attachment_links[expense.expense_id]
                }
            )

        if not is_credit:
            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_expense_url',
                    'type': 'String',
                    'value': '{}/app/admin/#/enterprise/view_expense/{}?org_id={}'.format(
                        settings.FYLE_EXPENSE_URL,
                        expense.expense_id,
                        org_id
                    )
                }
            )
            netsuite_custom_segments.append(
                {
                    'scriptId': 'custcolfyle_expense_url_2',
                    'type': 'String',
                    'value': '{}/app/admin/#/enterprise/view_expense/{}?org_id={}'.format(
                        settings.FYLE_EXPENSE_URL,
                        expense.expense_id,
                        org_id
                    )
                }
            )

        return netsuite_custom_segments

    def construct_bill_lineitems(
            self,
            bill_lineitems: List[BillLineitem],
            attachment_links: Dict,
            cluster_domain: str, org_id: str,
            override_tax_details: bool,
            general_mapping: GeneralMapping
        ) -> List[Dict]:
        """
        Create bill line items
        :return: constructed line items
        """
        expense_list = []
        item_list = []

        for line in bill_lineitems:
            expense: Expense = Expense.objects.get(pk=line.expense_id)

            netsuite_custom_segments = self.prepare_custom_segments(line.netsuite_custom_segments, attachment_links, expense, org_id)

            base_line = {
                'orderDoc': None,
                'orderLine': None,
                'line': None,
                'amount': line.amount,
                'grossAmt': line.amount,
                'taxDetailsReference': None,
                'department': {
                    'name': None,
                    'internalId': line.department_id,
                    'externalId': None,
                    'type': 'department'
                },
                'class': {
                    'name': None,
                    'internalId': line.class_id,
                    'externalId': None,
                    'type': 'classification'
                },
                'location': {
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
                'customer': {
                    'name': None,
                    'internalId': line.customer_id,
                    'externalId': None,
                    'type': 'customer'
                },
                'customFieldList': netsuite_custom_segments,
                'isBillable': line.billable,
                'tax1Amt': None,
                'taxAmount': None,
                'taxCode':{
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup'
                },
                'taxRate1': None,
                'taxRate2': None,
                'amortizationSched': None,
                'amortizStartDate': None,
                'amortizationEndDate': None,
                'amortizationResidual': None,
            }

            if line.detail_type == 'AccountBasedExpenseLineDetail':
                base_line['account'] = {
                    'name': None,
                    'internalId': line.account_id,
                    'externalId': None,
                    'type': 'account'
                }
                base_line['category'] = None
                base_line['memo'] = line.memo
                base_line['projectTask'] = None

                if line.tax_item_id is None or line.tax_amount is None:
                    expense_list.append(base_line)
                else:
                    if override_tax_details:
                        base_line['grossAmt'] = None
                        base_line['taxDetailsReference'] = expense.expense_number
                        base_line['amount'] = line.amount - line.tax_amount
                        expense_list.append(base_line)
                    else:
                        expense_list += self.handle_taxed_line_items(base_line, line, expense.workspace_id, 'BILL', general_mapping)

            else:
                base_line['item'] = {
                    'name': None,
                    'internalId': line.item_id,
                    'externalId': None,
                    'type': None
                }
                base_line['vendorName'] = None
                base_line['quantity'] = 1.0
                base_line['units'] = None
                base_line['inventoryDetail'] = None
                base_line['description'] = line.memo
                base_line['serialNumbers'] = None
                base_line['binNumbers'] = None
                base_line['expirationDate'] = None
                base_line['rate'] = str(line.amount)
                base_line['options'] = None
                base_line['landedCostCategory'] = None
                base_line['billVarianceStatus'] = None
                base_line['billreceiptsList'] = None
                base_line['landedCost'] = None

                if line.tax_item_id is None or line.tax_amount is None:
                    item_list.append(base_line)
                else:
                    if override_tax_details:
                        base_line['grossAmt'] = None
                        base_line['taxDetailsReference'] = expense.expense_number
                        base_line['amount'] = line.amount - line.tax_amount
                        item_list.append(base_line)
                    else:
                        item_list += self.handle_taxed_line_items(base_line, line, expense.workspace_id, 'BILL', general_mapping)

        return expense_list, item_list
    
    def construct_tax_details_list(self, bill_lineitems: List[BillLineitem]):
        tax_details_list = {}
        tax_details = []

        for line in bill_lineitems:
            expense = line.expense

            tax_type_id = None
            tax_code_id = None
            tax_rate =  None

            tax_code_id, tax_rate, tax_type_id = get_tax_info(expense)

            details = {
                'taxType': {
                    'internalId' : tax_type_id
                },
                'taxCode': {
                    'internalId': tax_code_id
                },
                'taxRate': tax_rate,
                'taxBasis': expense.amount - expense.tax_amount,
                'taxAmount': expense.tax_amount,
                'taxDetailsReference': expense.expense_number
            }
            tax_details.append(details)

        tax_details_list['taxDetails'] = tax_details
        return tax_details_list


    def __construct_bill(self, bill: Bill, bill_lineitems: List[BillLineitem], general_mappings: GeneralMapping) -> Dict:
        """
        Create a bill
        :return: constructed bill
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=bill.expense_group.workspace_id)

        cluster_domain = fyle_credentials.cluster_domain
        org_id = Workspace.objects.get(id=bill.expense_group.workspace_id).fyle_org_id

        tax_details_list =  None
        expense_list, item_list = self.construct_bill_lineitems(bill_lineitems, {}, cluster_domain, org_id, bill.override_tax_details, general_mappings)

        if bill.override_tax_details:
            tax_details_list = self.construct_tax_details_list(bill_lineitems)

        bill_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'nexus': None,
            'subsidiaryTaxRegNum': None,
            'taxRegOverride': None,
            'taxDetailsOverride': True if bill.override_tax_details else None,
            'customForm': None,
            'billAddressList': None,
            'account': {
                'name': None,
                'internalId': bill.accounts_payable_id,
                'externalId': None,
                'type': 'account'
            },
            'entity': {
                'name': None,
                'internalId': bill.entity_id,
                'externalId': None,
                'type': 'vendor'
            },
            'subsidiary': {
                'name': None,
                'internalId': bill.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'location': {
                'name': None,
                'internalId': bill.location_id,
                'externalId': None,
                'type': 'location'
            },
            'department': {
                'name': None,
                'internalId': bill.department_id,
                'externalId': None,
                'type': 'department'
            },
            'class': {
                'name': None,
                'internalId': bill.class_id,
                'externalId': None,
                'type': 'classification'
            },
            'approvalStatus': None,
            'nextApprover': None,
            'vatRegNum': None,
            'postingPeriod': None,
            'tranDate': bill.transaction_date,
            'currencyName': None,
            'billingAddress': None,
            'exchangeRate': None,
            'entityTaxRegNum': None,
            'taxPointDate': None,
            'terms': None,
            'dueDate': None,
            'discountDate': None,
            'tranId': bill.reference_number,
            'userTotal': None,
            'discountAmount': None,
            'taxTotal': None,
            'paymentHold': None,
            'memo': bill.memo,
            'tax2Total': None,
            'creditLimit': None,
            'availableVendorCredit': None,
            'currency': {
                'name': None,
                'internalId': bill.currency,
                'externalId': None,
                'type': 'currency'
            },
            'status': None,
            'landedCostMethod': None,
            'landedCostPerLine': None,
            'transactionNumber': None,
            'expenseList': expense_list if expense_list else None,
            'itemList': item_list if item_list else None,
            'accountingBookDetailList': None,
            'landedCostsList': None,
            'purchaseOrderList': None,
            'taxDetailsList': tax_details_list if bill.override_tax_details else None,
            'customFieldList': None,
            'internalId': None,
            'externalId': bill.external_id
        }

        return bill_payload

    def post_bill(self, bill: Bill, bill_lineitems: List[BillLineitem], general_mappings: GeneralMapping):
        """
        Post vendor bills to NetSuite
        """
        configuration = Configuration.objects.get(workspace_id=self.workspace_id)
        try:
            bills_payload = self.__construct_bill(bill, bill_lineitems, general_mappings)

            logger.info("| Payload for Bill creation | Content: {{WORKSPACE_ID: {} EXPENSE_GROUP_ID: {} BILL_PAYLOAD: {}}}".format(self.workspace_id, bill.expense_group.id, bills_payload))
            created_bill = self.connection.vendor_bills.post(bills_payload)
            return created_bill

        except NetSuiteRequestError as exception:
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)
            message = 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'
            if configuration.change_accounting_period and detail['message'] == message:
                first_day_of_month = datetime.today().date().replace(day=1)
                bills_payload = self.__construct_bill(bill, bill_lineitems, general_mappings)
                bills_payload['tranDate'] = first_day_of_month
                created_bill = self.connection.vendor_bills.post(bills_payload)
                
                return created_bill

            else:
                raise

    def get_bill(self, internal_id):
        """
        GET vendor bill from NetSuite
        """
        bill = self.connection.vendor_bills.get(internal_id)
        return bill

    def construct_credit_card_charge_lineitems(
            self, credit_card_charge_lineitems: List[CreditCardChargeLineItem], general_mapping: GeneralMapping,
            attachment_links: Dict, cluster_domain: str, org_id: str) -> List[Dict]:
        """
        Create credit_card_charge line items
        :return: constructed line items
        """
        lines = []

        for line in credit_card_charge_lineitems:
            expense = Expense.objects.get(pk=line.expense_id)

            netsuite_custom_segments = self.prepare_custom_segments(line.netsuite_custom_segments, attachment_links, expense, org_id)

            base_line = {
                'account': {'internalId': line.account_id},
                'amount': line.amount,
                'memo': line.memo,
                'grossAmt': line.amount,
                'department': {'internalId': line.department_id},
                'class': {'internalId': line.class_id},
                'location': {'internalId': line.location_id},
                'customer': {'internalId': line.customer_id},
                'customFieldList': netsuite_custom_segments,
                'isBillable': line.billable,
                'taxAmount': None,
                'taxCode': {
                    'externalId': None,
                    'internalId': None,
                    'name': None,
                    'type': 'taxGroup'
                },
            }

            # Handle cases where no tax is applied first
            if line.tax_item_id is None or line.tax_amount is None:
                lines.append(base_line)
            else:
                lines += self.handle_taxed_line_items(base_line, line, expense.workspace_id, 'CREDIT_CARD_CHARGE', general_mapping)

        return lines

    def __construct_credit_card_charge(
            self, credit_card_charge: CreditCardCharge,
            credit_card_charge_lineitems: List[CreditCardChargeLineItem], general_mapping: GeneralMapping, attachment_links: Dict) -> Dict:
        """
        Create a credit_card_charge
        :return: constructed credit_card_charge
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=credit_card_charge.expense_group.workspace_id)

        cluster_domain = fyle_credentials.cluster_domain
        org_id = Workspace.objects.get(id=credit_card_charge.expense_group.workspace_id).fyle_org_id

        transaction_date = datetime.strptime(credit_card_charge.transaction_date, '%Y-%m-%d').strftime('%m/%d/%Y')

        credit_card_charge_payload = {
            'account': {
                'internalId': credit_card_charge.credit_card_account_id
            },
            'entity': {
                'internalId': credit_card_charge.entity_id
            },
            'subsidiary': {
                'internalId': credit_card_charge.subsidiary_id
            },
            'location': {
                'internalId': credit_card_charge.location_id
            },
            'currency': {
                'internalId': credit_card_charge.currency
            },
            'department': {
                'internalId': credit_card_charge.department_id
            },
            'class': {
                'internalId': credit_card_charge.class_id
            },
            'tranDate': transaction_date,
            'memo': credit_card_charge.memo,
            'tranid': credit_card_charge.reference_number,
            'expenses': self.construct_credit_card_charge_lineitems(
                credit_card_charge_lineitems, general_mapping, attachment_links, cluster_domain, org_id
            ),
            'externalId': credit_card_charge.external_id
        }

        return credit_card_charge_payload

    def post_credit_card_charge(self, credit_card_charge: CreditCardCharge,
                                credit_card_charge_lineitems: List[CreditCardChargeLineItem], general_mapping: GeneralMapping, attachment_links: Dict,
                                refund: bool):
        """
        Post vendor credit_card_charges to NetSuite
        """
        
        configuration = Configuration.objects.get(workspace_id=self.workspace_id)

        account = self.__netsuite_credentials.ns_account_id.replace('_', '-')
        consumer_key = self.__netsuite_credentials.ns_consumer_key
        consumer_secret = self.__netsuite_credentials.ns_consumer_secret
        token_key = self.__netsuite_credentials.ns_token_id
        token_secret = self.__netsuite_credentials.ns_token_secret
        is_sandbox = False

        if '-SB' in account:
            is_sandbox = True

        url = f"https://{account.lower()}.restlets.api.netsuite.com/app/site/hosting/restlet.nl?" \
            f"script=customscript_cc_charge_fyle&deploy=customdeploy_cc_charge_fyle"

        if refund:
            for credit_card_charge_lineitem in credit_card_charge_lineitems:    
                credit_card_charge_lineitem.amount = abs(credit_card_charge_lineitem.amount)
                credit_card_charge_lineitem.save()

            url = f"https://{account.lower()}.restlets.api.netsuite.com/app/site/hosting/restlet.nl?" \
                f"script=customscript_cc_refund_fyle&deploy=customdeploy_cc_refund_fyle"

        credit_card_charges_payload = self.__construct_credit_card_charge(
            credit_card_charge, credit_card_charge_lineitems, general_mapping, attachment_links)

        logger.info("| Payload for Credit Card Charge creation | Content: {{WORKSPACE_ID: {} EXPENSE_GROUP_ID: {} CREDIT_CARD_CHARGE_PAYLOAD: {}}}".format(self.workspace_id, credit_card_charge.expense_group.id, credit_card_charges_payload))        

        oauth = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=token_key,
            resource_owner_secret=token_secret,
            realm=self.__netsuite_credentials.ns_account_id.upper() if is_sandbox else account,
            signature_method='HMAC-SHA256'
        )

        raw_response = oauth.post(
            url, headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }, data=json.dumps(credit_card_charges_payload))

        status_code = raw_response.status_code

        if status_code == 200 and 'success' in json.loads(raw_response.text) and json.loads(raw_response.text)['success']:
            return json.loads(raw_response.text)

        elif configuration.change_accounting_period:
            logger.info('Charge Card Error - %s', raw_response.text)

            error_message = None
            try:
                error_message = parse_error_and_get_message(raw_response.text)
            except Exception as e:
                logger.info('Error while parsing error message - %s', e)

            if error_message == 'The transaction date you specified is not within the date range of your accounting period.':
                first_day_of_month = datetime.today().date().replace(day=1)
                credit_card_charges_payload['tranDate'] = first_day_of_month.strftime('%m/%d/%Y')
                raw_response = oauth.post(
                    url, headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }, data=json.dumps(credit_card_charges_payload))

                status_code = raw_response.status_code

                if status_code == 200 and 'success' in json.loads(raw_response.text) \
                        and json.loads(raw_response.text)['success']:
                    return json.loads(raw_response.text)

                code, message = self.get_message_and_code(raw_response)

                raise NetSuiteRequestError(code=code, message=message)

        code, message = self.get_message_and_code(raw_response)
        raise NetSuiteRequestError(code=code, message=message)

    def construct_expense_report_lineitems(
            self, expense_report_lineitems: List[ExpenseReportLineItem], general_mapping: GeneralMapping, attachment_links: Dict, cluster_domain: str,
            org_id: str
    ) -> List[Dict]:
        """
        Create expense report line items
        :return: constructed line items
        """
        lines = []

        for line in expense_report_lineitems:
            expense: Expense = Expense.objects.get(pk=line.expense_id)
            netsuite_custom_segments = self.prepare_custom_segments(line.netsuite_custom_segments, attachment_links, expense, org_id)

            if expense.foreign_amount:
                if expense.amount == 0:
                    foreign_amount = 0
                else:
                    foreign_amount = expense.foreign_amount
            else:
                foreign_amount = None

            base_line = {
                'amount': line.amount,
                'category': {
                    'name': None,
                    'internalId': line.category,
                    'externalId': None,
                    'type': 'account'
                },
                'corporateCreditCard': True if expense.fund_source == 'CCC' else None,
                'currency': {
                    'name': None,
                    'internalId': line.currency,
                    'externalId': None,
                    'type': 'currency'
                },
                'customer': {
                    'name': None,
                    'internalId': line.customer_id,
                    'externalId': None,
                    'type': 'customer'
                },
                'location': {
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
                'department': {
                    'name': None,
                    'internalId': line.department_id,
                    'externalId': None,
                    'type': 'department'
                },
                'class': {
                    'name': None,
                    'internalId': line.class_id,
                    'externalId': None,
                    'type': 'classification'
                },
                'customFieldList': netsuite_custom_segments,
                'exchangeRate': None,
                'expenseDate': line.transaction_date,
                'expMediaItem': None,
                'foreignAmount': foreign_amount,
                'grossAmt': line.amount,
                'isBillable': line.billable,
                'isNonReimbursable': None,
                'line': None,
                'memo': line.memo,
                'quantity': None,
                'rate': None,
                'receipt': None,
                'refNumber': None,
                'tax1Amt': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup'
                },
                'taxRate1': None,
                'taxRate2': None
            }

            # Handle cases where no tax is applied first
            if line.tax_item_id is None or line.tax_amount is None:
                lines.append(base_line)
            else:
                lines += self.handle_taxed_line_items(base_line, line, expense.workspace_id, 'EXPENSE_REPORT', general_mapping)

        return lines

    def __construct_expense_report(self, expense_report: ExpenseReport,
                                   expense_report_lineitems: List[ExpenseReportLineItem], general_mapping: GeneralMapping) -> Dict:
        """
        Create a expense report
        :return: constructed expense report
        """

        fyle_credentials = FyleCredential.objects.get(workspace_id=expense_report.expense_group.workspace_id)

        cluster_domain = fyle_credentials.cluster_domain
        org_id = Workspace.objects.get(id=expense_report.expense_group.workspace_id).fyle_org_id

        expense_report_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'status': None,
            'customForm': None,
            'account': {
                'name': None,
                'internalId': expense_report.account_id,
                'externalId': None,
                'type': 'account'
            },
            'entity': {
                'name': None,
                'internalId': expense_report.entity_id,
                'externalId': None,
                'type': 'vendor'
            },
            'expenseReportCurrency': {
                'name': None,
                'internalId': expense_report.currency,
                'externalId': None,
                'type': 'currency'
            },
            'subsidiary': {
                'name': None,
                'internalId': expense_report.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'expenseReportExchangeRate': None,
            'taxPointDate': None,
            'tranId': None,
            'acctCorpCardExp': {
                'name': None,
                'internalId': expense_report.credit_card_account_id,
                'externalId': None,
                'type': 'account'
            },
            'postingPeriod': None,
            'tranDate': expense_report.transaction_date,
            'dueDate': None,
            'approvalStatus': None,
            'total': None,
            'nextApprover': None,
            'advance': None,
            'tax1Amt': None,
            'amount': None,
            'memo': expense_report.memo,
            'complete': None,
            'supervisorApproval': True,
            'accountingApproval': True,
            'useMultiCurrency': None,
            'tax2Amt': None,
            'department': {
                'name': None,
                'internalId': expense_report.department_id if expense_report.department_id else None,
                'externalId': None,
                'type': 'department'
            },
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification'
            },
            'location': {
                'name': None,
                'internalId': expense_report.location_id,
                'externalId': None,
                'type': 'location'
            },
            'expenseList': self.construct_expense_report_lineitems(
                expense_report_lineitems, general_mapping, {}, cluster_domain, org_id
            ),
            'accountingBookDetailList': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': expense_report.external_id
        }

        return expense_report_payload

    def post_expense_report(
            self, expense_report: ExpenseReport,
            expense_report_lineitems: List[ExpenseReportLineItem], general_mapping: GeneralMapping):
        """
        Post expense reports to NetSuite
        """
        configuration = Configuration.objects.get(workspace_id=self.workspace_id)
        try:
            expense_report_payload = self.__construct_expense_report(expense_report,
                                                                    expense_report_lineitems, general_mapping)
           
            logger.info("| Payload for Expense Report creation | Content: {{WORKSPACE_ID: {} EXPENSE_GROUP_ID: {} EXPENSE_REPORT_PAYLOAD: {}}}".format(self.workspace_id, expense_report.expense_group.id, expense_report_payload))

            created_expense_report = self.connection.expense_reports.post(expense_report_payload)
            return created_expense_report

        except NetSuiteRequestError as exception:
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)
            message = 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'

            if configuration.change_accounting_period and detail['message'] == message:
                expense_report_payload = self.__construct_expense_report(expense_report,
                                                                    expense_report_lineitems, general_mapping)

                first_day_of_month = datetime.today().date().replace(day=1)
                expense_report_payload['tranDate'] = first_day_of_month.strftime('%Y-%m-%dT%H:%M:%S')
                created_expense_report = self.connection.expense_reports.post(expense_report_payload)
                expense_report.transaction_date = first_day_of_month
                expense_report.save()
                return created_expense_report

            else:
                raise

    def get_expense_report(self, internal_id):
        """
        GET expense report from NetSuite
        """
        expense_report = self.connection.expense_reports.get(internal_id)
        return expense_report


    def construct_journal_entry_lineitems(self, journal_entry_lineitems: List[JournalEntryLineItem], general_mapping: GeneralMapping, org_id: str,
                                            credit=None, debit=None, attachment_links: Dict = None,
                                            cluster_domain: str = None) -> List[Dict]:
        """
        Create journal entry line items
        :return: constructed line items
        """
        lines = []

        for line in journal_entry_lineitems:
            expense = Expense.objects.get(pk=line.expense_id)
            account_ref = None
            if credit is None:
                account_ref = line.account_id

            if debit is None:
                account_ref = line.debit_account_id

            netsuite_custom_segments = self.prepare_custom_segments(line.netsuite_custom_segments, attachment_links, expense, org_id, credit)

            base_line = {
                'account': {
                    'name': None,
                    'internalId': account_ref,
                    'externalId': None,
                    'type': 'account'
                },
                'department': {
                    'name': None,
                    'internalId': line.department_id,
                    'externalId': None,
                    'type': 'department'
                },
                'location': {
                    'name': None,
                    'internalId': line.location_id,
                    'externalId': None,
                    'type': 'location'
                },
                'class': {
                    'name': None,
                    'internalId': line.class_id,
                    'externalId': None,
                    'type': 'classification'
                },
                'entity': {
                    'name': None,
                    'internalId': line.entity_id,
                    'externalId': None,
                    'type': 'vendor'
                },
                'credit': None,
                'creditTax': None,
                'customFieldList': netsuite_custom_segments,
                'debit': line.amount,
                'debitTax': None,
                'eliminate': None,
                'endDate': None,
                'grossAmt': None,
                'line': None,
                'lineTaxCode': None,
                'lineTaxRate': None,
                'memo': line.memo,
                'residual': None,
                'revenueRecognitionRule': None,
                'schedule': None,
                'scheduleNum': None,
                'startDate': None,
                'tax1Acct': None,
                'taxAccount': None,
                'taxBasis': None,
                'tax1Amt': None,
                'taxCode': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'taxGroup'
                },
                'taxRate1': None,
                'totalAmount': None,
            }


            if debit:
                if line.tax_item_id is None or line.tax_amount is None:
                    lines.append(base_line)
                else:
                    lines += self.handle_taxed_line_items(base_line, line, expense.workspace_id, 'JOURNAL_ENTRY', general_mapping)
            elif credit:
                base_line['credit'] = line.amount
                base_line['debit'] = None
                lines.append(base_line)
        

        return lines

    @staticmethod
    def __construct_single_itemized_credit_line(journal_entry_lineitems: List[JournalEntryLineItem]):
        """
        Create journal entry line items for single credit line
        :return: constructed line items
        """
        lines = []
        distinct_line_ids = {}

        for line in journal_entry_lineitems:
            account_ref = line.debit_account_id
            entity_id = line.entity_id
            line_id = '{account_ref}::::{entity_id}'.format(account_ref=account_ref, entity_id=entity_id)

            if line_id in distinct_line_ids:
                distinct_line_ids[line_id] += line.amount
            else:
                distinct_line_ids[line_id] = line.amount

        for line_id, amount in distinct_line_ids.items():
            account_ref, entity_id = line_id.split('::::')
            lineitem = {
                'account': {
                    'name': None,
                    'internalId': account_ref,
                    'externalId': None,
                    'type': 'account'
                },
                'department': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'department'
                },
                'location': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'location'
                },
                'class': {
                    'name': None,
                    'internalId': None,
                    'externalId': None,
                    'type': 'classification'
                },
                'entity': {
                    'name': None,
                    'internalId': entity_id,
                    'externalId': None,
                    'type': 'vendor'
                },
                'credit': amount,
                'creditTax': None,
                'customFieldList': [],
                'debit': None,
                'debitTax': None,
                'eliminate': None,
                'endDate': None,
                'grossAmt': None,
                'line': None,
                'lineTaxCode': None,
                'lineTaxRate': None,
                'memo': 'Total Amount',
                'residual': None,
                'revenueRecognitionRule': None,
                'schedule': None,
                'scheduleNum': None,
                'startDate': None,
                'tax1Acct': None,
                'taxAccount': None,
                'taxBasis': None,
                'tax1Amt': None,
                'taxCode': None,
                'taxRate1': None,
                'totalAmount': None,
            }

            lines.append(lineitem)

        return lines

    def __construct_journal_entry(self, journal_entry: JournalEntry,
                                  journal_entry_lineitems: List[JournalEntryLineItem], configuration: Configuration, general_mapping: GeneralMapping) -> Dict:
        """
        Create a journal entry report
        :return: constructed journal entry
        """
        fyle_credentials = FyleCredential.objects.get(workspace_id=journal_entry.expense_group.workspace_id)

        cluster_domain = fyle_credentials.cluster_domain
        org_id = Workspace.objects.get(id=journal_entry.expense_group.workspace_id).fyle_org_id

        if configuration.je_single_credit_line:
            credit_line = self.__construct_single_itemized_credit_line(journal_entry_lineitems)
        else:
            credit_line = self.construct_journal_entry_lineitems(journal_entry_lineitems, credit='Credit', org_id=org_id, general_mapping=general_mapping)

        debit_line = self.construct_journal_entry_lineitems(
            journal_entry_lineitems,
            debit='Debit', attachment_links={},
            cluster_domain=cluster_domain, org_id=org_id, general_mapping=general_mapping
        )
        lines = []
        lines.extend(credit_line)
        lines.extend(debit_line)

        journal_entry_payload = {
            'accountingBook': None,
            'accountingBookDetailList': None,
            'approved': None,
            'createdDate': None,
            'createdFrom': None,
            'currency': {
                'name': None,
                'internalId': journal_entry.currency,
                'externalId': None,
                'type': 'currency'
            },
            'customFieldList': None,
            'customForm': None,
            'class': {
                'name': None,
                'internalId': None,
                'externalId': None,
                'type': 'classification'
            },
            'department': {
                'name': None,
                'internalId': journal_entry.department_id,
                'externalId': None,
                'type': 'department'
            },
            'location': {
                'name': None,
                'internalId': journal_entry.location_id,
                'externalId': None,
                'type': 'location'
            },
            'exchangeRate': None,
            'isBookSpecific': None,
            'lastModifiedDate': None,
            'lineList': lines,
            'memo': journal_entry.memo,
            'nexus': None,
            'parentExpenseAlloc': None,
            'postingPeriod': None,
            'reversalDate': None,
            'reversalDefer': None,
            'reversalEntry': None,
            'subsidiary': {
                'name': None,
                'internalId': journal_entry.subsidiary_id,
                'externalId': None,
                'type': 'subsidiary'
            },
            'subsidiaryTaxRegNum': None,
            'taxPointDate': None,
            'toSubsidiary': None,
            'tranDate': journal_entry.transaction_date,
            'tranId': None,
            'externalId': journal_entry.external_id
        }

        return journal_entry_payload

    def post_journal_entry(self, journal_entry: JournalEntry,
                           journal_entry_lineitems: List[JournalEntryLineItem], configuration: Configuration, general_mapping: GeneralMapping):
        """
        Post journal entries to NetSuite
        """
        configuration = Configuration.objects.get(workspace_id=self.workspace_id)
        try:
            journal_entry_payload = self.__construct_journal_entry(journal_entry, journal_entry_lineitems, configuration, general_mapping)

            logger.info("| Payload for Journal Entry creation | Content: {{WORKSPACE_ID: {} EXPENSE_GROUP_ID: {} JOURNAL_ENTRY_PAYLOAD: {}}}".format(self.workspace_id, journal_entry.expense_group.id, journal_entry_payload))

            created_journal_entry = self.connection.journal_entries.post(journal_entry_payload)
            return created_journal_entry

        except NetSuiteRequestError as exception:
            detail = json.dumps(exception.__dict__)
            detail = json.loads(detail)
            message = 'An error occured in a upsert request: The transaction date you specified is not within the date range of your accounting period.'

            if configuration.change_accounting_period and detail['message'] == message:
                first_day_of_month = datetime.today().date().replace(day=1)
                journal_entry_payload = self.__construct_journal_entry(journal_entry, journal_entry_lineitems, configuration, general_mapping)
                journal_entry_payload['tranDate'] = first_day_of_month
                created_journal_entry = self.connection.journal_entries.post(journal_entry_payload)
                
                return created_journal_entry

            else:
                raise

    @staticmethod
    def __construct_vendor_payment_lineitems(vendor_payment_lineitems: List[VendorPaymentLineitem]) -> List[Dict]:
        """
        Create vendor payment line items
        :return: constructed line items
        """
        lines = []

        for line in vendor_payment_lineitems:
            line = {
                'apply': 'true',
                'doc': line.doc_id,
                'line': 0,
                'job': None,
                'applyDate': None,
                'type': None,
                'refNum': None,
                'total': None,
                'due': None,
                'currency': None,
                'discDate': None,
                'discAmt': None,
                'disc': None,
                'amount': None
            }

            lines.append(line)

        return lines

    def __construct_vendor_payment(self, vendor_payment: VendorPayment,
                                   vendor_payment_lineitems: List[VendorPaymentLineitem],
                                   department, netsuite_class) -> Dict:
        """
        Create a vendor payment
        :return: constructed vendor payment
        """
        vendor_payment_payload = {
            'nullFieldList': None,
            'createdDate': None,
            'lastModifiedDate': None,
            'customForm': None,
            'account': {
                'name': None,
                'internalId': vendor_payment.account_id,
                'externalId': None,
                'type': None
            },
            'balance': None,
            'apAcct': {
                'name': None,
                'internalId': vendor_payment.accounts_payable_id,
                'externalId': None,
                'type': None
            },
            'entity': {
                'name': None,
                'internalId': vendor_payment.entity_id,
                'externalId': None,
                'type': None
            },
            'address': None,
            'tranDate': None,
            'voidJournal': None,
            'postingPeriod': None,
            'currencyName': None,
            'exchangeRate': None,
            'toAch': 'false',
            'toBePrinted': 'false',
            'printVoucher': 'false',
            'tranId': None,
            'total': None,
            'currency': {
                'name': None,
                'internalId': vendor_payment.currency,
                'externalId': None,
                'type': None
            },
            'department': {
                'name': None,
                'internalId': department['internalId'] if (department and 'internalId' in department) else None,
                'externalId': None,
                'type': 'department'
            },
            'memo': vendor_payment.memo,
            'subsidiary': {
                'name': None,
                'internalId': vendor_payment.subsidiary_id,
                'externalId': None,
                'type': None
            },
            'class': {
                'name': None,
                'internalId': netsuite_class['internalId'] if (netsuite_class and 'internalId' in netsuite_class) else None,
                'externalId': None,
                'type': 'classification'
            },
            'location': {
                'name': None,
                'internalId': vendor_payment.location_id,
                'externalId': None,
                'type': 'location'
            },
            'status': None,
            'transactionNumber': None,
            'applyList': {
                'apply':
                    self.__construct_vendor_payment_lineitems(vendor_payment_lineitems),
                'replaceAll': 'true'
            },
            'creditList': None,
            'billPay': None,
            'accountingBookDetailList': None,
            'availableBalance': None,
            'isInTransitPayment': None,
            'approvalStatus': None,
            'nextApprover': None,
            'customFieldList': None,
            'internalId': None,
            'externalId': vendor_payment.external_id
        }

        return vendor_payment_payload

    def post_vendor_payment(self, vendor_payment: VendorPayment,
                            vendor_payment_lineitems: List[VendorPaymentLineitem],
                            first_object):
        """
        Post vendor payments to NetSuite
        """
        department = first_object['department']
        netsuite_class = first_object['class']

        vendor_payment_payload = self.__construct_vendor_payment(
            vendor_payment, vendor_payment_lineitems, department, netsuite_class
        )

        logger.info("| Payload for Vendor Payment creation | Content: {{WORKSPACE_ID: {} VENDOR_PAYMENT_PAYLOAD: {}}}".format(self.workspace_id, vendor_payment_payload))

        created_vendor_payment = self.connection.vendor_payments.post(vendor_payment_payload)
        return created_vendor_payment


def parse_error_and_get_message(raw_response, get_code: bool = False):
    try:
        if raw_response == '<HTML><HEAD>' or raw_response == '<html>':
            return 'HTML bad response from NetSuite'
        raw_response = raw_response.replace("'", '"')\
            .replace("False", 'false')\
            .replace("True", 'true')\
            .replace("None", 'null')
        parsed_response = json.loads(raw_response)
        if get_code:
            return get_message_and_code(parsed_response)
        return get_message_from_parsed_error(parsed_response)
    except Exception:
        raw_response = raw_response.replace('"creditCardCharge"', 'creditCardCharge')\
            .replace('""{', '{').replace('}""', '}')\
            .replace('"{', '{').replace('}"', '}')\
            .replace('\\"', '"').replace('\\', '')\
            .replace('"https://', "'https://").replace('.html"', ".html'")\
            .replace('="', "=").replace('">', ">")
        parsed_response = json.loads(raw_response)
        if get_code:
            return get_message_and_code(parsed_response)
        return get_message_from_parsed_error(parsed_response)


def get_message_from_parsed_error(parsed_response):
    try:
        if 'error' in parsed_response:
            if 'message' in parsed_response['error']:
                if 'message' in parsed_response['error']['message']:
                    return parsed_response['error']['message']['message']
                return parsed_response['error']['message']
        elif 'message' in parsed_response:
            if 'message' in parsed_response['message']:
                return parsed_response['message']['message']
    except Exception:
        raise


def get_message_and_code(parsed_response):
    message = get_message_from_parsed_error(parsed_response)
    code = parsed_response['error']['code'] if 'error' in parsed_response and 'code' in parsed_response['error'] else parsed_response['code']
    return code, message
