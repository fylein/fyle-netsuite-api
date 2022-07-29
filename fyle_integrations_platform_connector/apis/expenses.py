from typing import List
from datetime import datetime

from dateutil import parser

from .base import Base


class Expenses(Base):
    """Class for Expenses APIs."""

    def get(self, source_account_type: List[str], state: str, last_synced_at: datetime=None,
        settled_at: datetime=None, filter_credit_expenses: bool=False, last_paid_at=None) -> List[dict]:
        """
        Get expenses.

        Args:
            source_account_type (List[str]): Source account types.
            state (str): Import state.
            last_synced_at (datetime, optional): Last synced at. Defaults to None.
            filter_credit_expenses (bool, optional): Filter negative expenses. Defaults to False.

        Returns:
            List[dict]: Response.
        """
        all_expenses = []

        query_params = self.__construct_expenses_query_params(source_account_type, state, last_synced_at, settled_at, last_paid_at)
        generator = self.connection.list_all(query_params)

        for expense_list in generator:
            expenses = self.__filter_personal_expenses(expense_list)
            if filter_credit_expenses:
                expenses = self.__filter_credit_expenses(expenses)
            all_expenses.extend(expenses)

        return self.__construct_expenses_objects(all_expenses)


    @staticmethod
    def __construct_expenses_query_params(source_account_type: List[str], state: str, updated_at: datetime, settled_at: datetime, last_paid_at: datetime) -> dict:
        """
        Construct expenses query params.
        :param source_account_type: Source account types.
        :param state: Import state.
        :param updated_at: Updated at.
        :return: Query params.
        """

        state = [state]
        if state[0] == 'PAYMENT_PROCESSING' and (updated_at is not None or settled_at is not None):
            state.append('PAID')
            state = 'in.{}'.format(tuple(state)).replace("'", '"')
        else:
            state = 'eq.{}'.format(state[0])

        source_account_type_filter = ['PERSONAL_CASH_ACCOUNT']
        if len(source_account_type) == 1:
            source_account_type_filter = 'eq.{}'.format(source_account_type[0])
        elif len(source_account_type) > 1 and 'PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT' in source_account_type:
            source_account_type_filter.append('PERSONAL_CORPORATE_CREDIT_CARD_ACCOUNT')
            source_account_type_filter = 'in.{}'.format(tuple(source_account_type_filter)).replace("'", '"')

        query_params = {
            'order': 'updated_at.desc',
            'source_account->type': source_account_type_filter,
            'state': state
        }

        if updated_at:
            updated_at = 'gte.{}'.format(datetime.strftime(updated_at, '%Y-%m-%dT%H:%M:%S.000Z'))
            query_params['updated_at'] = updated_at

        if settled_at:
            settled_at = 'gte.{}'.format(datetime.strftime(settled_at, '%Y-%m-%dT%H:%M:%S.000Z'))
            query_params['last_settled_at'] = settled_at

        if last_paid_at:
            last_paid_at = 'gte.{}'.format(datetime.strftime(last_paid_at, '%Y-%m-%dT%H:%M:%S.000Z'))
            query_params['report->last_paid_at'] = last_paid_at

        return query_params


    @staticmethod
    def __filter_personal_expenses(expense_list: dict) -> List[dict]:
        """
        Filter personal expenses.
        :param expense_list: Expense list.
        :return: Expense list.
        """
        return list(
            filter(
                lambda expense: not (
                    not expense['is_reimbursable'] and expense['source_account']['type'] == 'PERSONAL_CASH_ACCOUNT'
                ),
                expense_list['data']
            )
        )


    @staticmethod
    def __filter_credit_expenses(expense_list: dict) -> List[dict]:
        """
        Filter negative expenses.

        Args:
            expenses (dict): Expenses.

        Returns:
            list: Expenses.
        """
        return list(filter(lambda expense: expense['amount'] > 0, expense_list))


    def __construct_expenses_objects(self, expenses: List[dict]) -> List[dict]:
        """
        Construct expenses objects.

        Args:
            expense (List[dict]): Expenses.

        Returns:
            list: Expenses.
        """
        objects = []

        for expense in expenses:
            custom_properties = {}
            for custom_field in expense['custom_fields']:
                custom_properties[custom_field['name']] = custom_field['value']

            objects.append({
                'id': expense['id'],
                'employee_email': expense['employee']['user']['email'],
                'employee_name': expense['employee']['user']['full_name'],
                'category': expense['category']['name'],
                'sub_category': expense['category']['sub_category'],
                'project': expense['project']['name'] if expense['project'] else None,
                'project_id': expense['project']['id'] if expense['project'] else None,
                'expense_number': expense['seq_num'],
                'org_id': expense['org_id'],
                'claim_number': expense['report']['seq_num'] if expense['report'] else None,
                'amount': expense['amount'],
                'tax_amount': expense['tax_amount'],
                'tax_group_id': expense['tax_group_id'],
                'settled_at': expense['last_settled_at'],
                'currency': expense['currency'],
                'foreign_amount': expense['foreign_amount'],
                'foreign_currency': expense['foreign_currency'],
                'settlement_id': expense['report']['settlement_id'] if expense['report'] else None,
                'reimbursable': expense['is_reimbursable'],
                'billable': expense['is_billable'],
                'state': expense['state'],
                'vendor': expense['merchant'],
                'cost_center': expense['cost_center']['name'] if expense['cost_center'] else None,
                'corporate_card_id': expense['matched_corporate_card_transactions'][0]['corporate_card_id'] \
                    if expense['matched_corporate_card_transactions'] else None,
                'purpose': expense['purpose'],
                'report_id': expense['report_id'],
                'file_ids': expense['file_ids'],
                'spent_at': self.__format_date(expense['spent_at']),
                'approved_at': self.__format_date(expense['report']['last_approved_at']) if expense['report'] else None,
                'expense_created_at': expense['created_at'],
                'expense_updated_at': expense['updated_at'],
                'source_account_type': expense['source_account']['type'],
                'verified_at': self.__format_date(expense['last_verified_at']),
                'custom_properties': custom_properties,
                'payment_number': expense['report']['reimbursement_seq_num'] if expense['report'][
                    'reimbursement_seq_num'] else None
            })

        return objects


    @staticmethod
    def __format_date(date_string) -> datetime:
        """
        Format date.

        Args:
            date_string (str): Date string.

        Returns:
            dateime: Formatted date.
        """
        if date_string:
            date_string = parser.parse(date_string)

        return date_string
