from .base import Base

from apps.fyle.models import Reimbursement


class Reimbursements(Base):
    """Class for Reimbursements APIs."""

    def __construct_query_params(self) -> dict:
        """
        Constructs the query params for the API call.
        :return: dict
        """
        last_synced_record = Reimbursement.get_last_synced_at(self.workspace_id)
        updated_at = self.format_date(last_synced_record.updated_at) if last_synced_record else None

        query_params = {'order': 'updated_at.desc'}

        if updated_at:
            query_params['updated_at'] = updated_at

        return query_params


    def __get_all_generator(self):
        """
        Returns the generator for retrieving data from the API.
        :return: Generator
        """
        query_params = self.__construct_query_params()

        return self.connection.list_all(query_params)
    

    def search_reimbursements(self, query_params):
        """
        Get of reimbursements filtered on query parameters
        :return: Generator
        """
        query_params['order'] = 'updated_at.desc'
        return self.connection.list_all(query_params)

    def bulk_post_reimbursements(self, data):
        """
        Post of reimbursements
        """
        payload = {
            'data': data
        }

        return self.connection.bulk_post_reimbursements(payload)

    def sync(self):
        """
        Syncs the latest API data to DB.
        """
        generator = self.__get_all_generator()
        for items in generator:
            Reimbursement.create_or_update_reimbursement_objects(items['data'], self.workspace_id)
