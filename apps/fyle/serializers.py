from rest_framework import serializers

from fyle_accounting_mappings.models import ExpenseAttribute

from .models import Expense, ExpenseFilter, ExpenseGroup, ExpenseGroupSettings


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


class ExpenseFilterSerializer(serializers.ModelSerializer):
    """
    Expense Filter Serializer
    """
    class Meta:
        model = ExpenseFilter
        fields = '__all__'
        read_only_fields = ('id', 'workspace', 'created_at', 'updated_at') 

    def create(self, validated_data):
        workspace_id = self.context['request'].parser_context.get('kwargs').get('workspace_id')

        expense_filter, _ = ExpenseFilter.objects.update_or_create(
            workspace_id=workspace_id,
            rank=validated_data['rank'],
            defaults=validated_data
        )

        return expense_filter
