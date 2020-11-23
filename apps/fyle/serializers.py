from rest_framework import serializers

from .models import Expense, ExpenseGroup, ExpenseGroupSettings, Reimbursement
from fyle_accounting_mappings.models import ExpenseAttribute


class ExpenseGroupSerializer(serializers.ModelSerializer):
    """
    Expense group serializer
    """
    class Meta:
        model = ExpenseGroup
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Expense serializer
    """
    class Meta:
        model = Expense
        fields = '__all__'


class ExpenseGroupSettingsSerializer(serializers.ModelSerializer):
    """
    Expense group serializer
    """
    class Meta:
        model = ExpenseGroupSettings
        fields = '__all__'


class ExpenseFieldSerializer(serializers.ModelSerializer):
    """
    Expense Fields Serializer
    """
    class Meta:
        model = ExpenseAttribute
        fields = ['attribute_type', 'display_name']


class ReimbursementSerializer(serializers.ModelSerializer):
    """
    Reimbursement serializer
    """
    class Meta:
        model = Reimbursement
        fields = '__all__'
