from apps.fyle.models import ExpenseGroupSettings


def add_expense_id_to_expense_group_settings(workspace_id: int):
    """
    Add Expense id to card expense grouping
    :param workspace_id: Workspace id
    return: None
    """
    expense_group_settings = ExpenseGroupSettings.objects.get(workspace_id=workspace_id)
    ccc_expense_group_fields = expense_group_settings.corporate_credit_card_expense_group_fields
    ccc_expense_group_fields.append('expense_id')
    expense_group_settings.corporate_credit_card_expense_group_fields = list(set(ccc_expense_group_fields))
    expense_group_settings.save()