from rest_framework import serializers

from fyle_accounting_mappings.models import DestinationAttribute
from .models import CustomSegment, NetSuiteAttributesCount


class NetSuiteFieldSerializer(serializers.ModelSerializer):
    """
    Expense Fields Serializer
    """
    class Meta:
        model = DestinationAttribute
        fields = ['attribute_type', 'display_name']


class CustomSegmentSerializer(serializers.ModelSerializer):
    """
    Custom Segment Serializer
    """
    name = serializers.CharField(required=False)
    class Meta:
        model = CustomSegment
        fields = '__all__'


class NetSuiteAttributesCountSerializer(serializers.ModelSerializer):
    """
    Serializer for NetSuite Attributes Count
    """
    class Meta:
        model = NetSuiteAttributesCount
        fields = '__all__'
