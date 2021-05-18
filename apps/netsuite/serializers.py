from rest_framework import serializers

from fyle_accounting_mappings.models import DestinationAttribute
from .models import CustomSegment


class NetSuiteFieldSerializer(serializers.ModelSerializer):
    """
    Expense Fields Serializer
    """
    class Meta:
        model = DestinationAttribute
        fields = ['attribute_type', 'display_name']


class CustomSegmentSerializer(serializers.ModelSerializer):
    """
    Custom List Serializer
    """
    class Meta:
        model = CustomSegment
        fields = '__all__'
