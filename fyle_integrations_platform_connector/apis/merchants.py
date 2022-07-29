from apps.workspaces.models import Workspace
from .base import Base
from typing import List
from fyle_accounting_mappings.models import ExpenseAttribute

class Merchants(Base):
    """
    Class for Merchants API
    """
    def __init__(self):
        Base.__init__(self, attribute_type='MERCHANT', query_params={'field_name':'eq.Merchant'})
    
    def construct_query_params(self) -> dict:
        """
        Constructs the query params for the API call.
        :return: dict
        """
        params = {'order': 'updated_at.desc'}
        params.update(self.query_params)

        return params

    def get(self):
        generator = self.get_all_generator()
        for items in generator:
            merchants = items['data'][0]
        
        return merchants

    def post(self, payload: List[str]):
        """
        Post data to Fyle 
        """
        generator = self.get_all_generator()
        for items in generator:
            merchants = items['data'][0]
            print('merchant', merchants)
            merchants['options'].extend(payload)
            merchant_payload = { 
                'id': merchants['id'],
                'field_name': 'Merchant',
                'type': 'SELECT',
                'options': merchants['options'],
                'placeholder': merchants['placeholder'],
                'category_ids': merchants['category_ids'],
                'is_enabled': merchants['is_enabled'],
                'is_custom': merchants['is_custom'],
                'is_mandatory': merchants['is_mandatory'],
                'code': merchants['code'],
                'default_value': merchants['default_value'] if merchants['default_value'] else '',
            }

        print('merchant payload', merchant_payload)
        return self.connection.post({'data': merchant_payload})

    def sync(self, workspace_id: int):
        """
        Syncs the latest API data to DB.
        """
        generator = self.get_all_generator()
        for items in generator:
            merchants=items['data'][0]
            existing_merchants = ExpenseAttribute.objects.filter(
                attribute_type='MERCHANT', workspace_id=workspace_id)
            delete_merchant_ids = []

            if(existing_merchants):
                for existing_merchant in existing_merchants:
                    if existing_merchant.value not in merchants['options']:
                        delete_merchant_ids.append(existing_merchant.id)
                    
                ExpenseAttribute.objects.filter(id__in=delete_merchant_ids).delete()

            merchant_attributes = []

            for option in merchants['options']:
                merchant_attributes.append({
                    'attribute_type': 'MERCHANT',
                    'display_name': 'Merchant',
                    'value': option,
                    'source_id': merchants['id'],
                })

            self.bulk_create_or_update_expense_attributes(merchant_attributes, True)
