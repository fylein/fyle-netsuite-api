from datetime import datetime
from typing import Dict, List

from fyle_accounting_mappings.models import ExpenseAttribute


class Base:
    """The base class for all API classes."""

    def __init__(self, attribute_type: str = None, query_params: dict = {}):
        self.attribute_type = attribute_type
        self.query_params = query_params
        self.connection = None
        self.workspace_id = None


    def set_connection(self, connection):
        self.connection = connection


    def set_workspace_id(self, workspace_id):
        self.workspace_id = workspace_id


    def format_date(self, last_synced_at: datetime) -> str:
        """
        Formats the date in the format of gte.2021-09-30T11:00:57.000Z
        """
        return 'gte.{}'.format(datetime.strftime(last_synced_at, '%Y-%m-%dT%H:%M:%S.000Z'))


    def __get_last_synced_at(self):
        """
        Returns the last time the API was synced.
        """
        return ExpenseAttribute.get_last_synced_at(self.attribute_type, self.workspace_id)


    def construct_query_params(self) -> dict:
        """
        Constructs the query params for the API call.
        :return: dict
        """
        last_synced_record = self.__get_last_synced_at()
        updated_at = self.format_date(last_synced_record.updated_at) if last_synced_record else None

        params = {'order': 'updated_at.desc'}
        params.update(self.query_params)

        if updated_at:
            params['updated_at'] = updated_at

        return params


    def get_all_generator(self):
        """
        Returns the generator for retrieving data from the API.
        :return: Generator
        """
        query_params = self.construct_query_params()

        return self.connection.list_all(query_params)

    def post_bulk(self, payload: List[Dict]):
        """
        Post data to Fyle in Bulk
        """
        return self.connection.post_bulk({'data': payload})
    
    def post(self, payload: Dict):
        """
        Post date to Fyle
        """
        return self.connection.post({'data': payload})

    def bulk_create_or_update_expense_attributes(self, attributes: List[dict], update_existing: bool = False) -> None:
        """
        Bulk creates or updates expense attributes.
        :param attributes: List of expense attributes.
        :param update_existing: If True, updates/creates the existing expense attributes.
        """
        ExpenseAttribute.bulk_create_or_update_expense_attributes(
            attributes, self.attribute_type, self.workspace_id, update_existing
        )


    def __construct_expense_attribute_objects(self, generator) -> List[dict]:
        """
        Constructs the expense attribute objects.
        :param generator: Generator
        :return: List of expense attribute objects.
        """
        attributes = []
        for items in generator:
            for row in items['data']:
                attributes.append({
                    'attribute_type': self.attribute_type,
                    'display_name': self.attribute_type.replace('_', ' ').title(),
                    'value': row['name'],
                    'source_id': row['id']
                })

        return attributes


    def sync(self) -> None:
        """
        Syncs the latest API data to DB.
        """
        generator = self.get_all_generator()
        attributes = self.__construct_expense_attribute_objects(generator)
        self.bulk_create_or_update_expense_attributes(attributes)
