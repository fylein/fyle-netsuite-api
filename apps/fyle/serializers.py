from rest_framework import serializers

from .models import Expense, ExpenseGroup


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
