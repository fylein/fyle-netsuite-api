from fyle_accounting_mappings.models import ExpenseAttribute
from rest_framework import serializers

from apps.fyle.models import ExpenseGroup
from apps.fyle.serializers import ExpenseSerializer
from apps.tasks.models import Error


class ExpenseAttributeSerializer(serializers.ModelSerializer):
    """
    Serializer for Expense Attribute
    """

    class Meta:
        model = ExpenseAttribute
        fields = '__all__'


class ExpenseGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Expense Group
    """

    expenses = ExpenseSerializer(many=True)

    class Meta:
        model = ExpenseGroup
        fields = '__all__'


class ErrorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Errors
    """

    expense_attribute = ExpenseAttributeSerializer()
    expense_group = ExpenseGroupSerializer()

    class Meta:
        model = Error
        exclude = ['mapping_error_expense_group_ids']

