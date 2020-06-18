from rest_framework import serializers

from .models import SubsidiaryMapping, LocationMapping


class SubsidiaryMappingSerializer(serializers.ModelSerializer):
    """
    Subsidiary mappings group serializer
    """
    class Meta:
        model = SubsidiaryMapping
        fields = '__all__'


class LocationMappingSerializer(serializers.ModelSerializer):
    """
    Location mappings group serializer
    """
    class Meta:
        model = LocationMapping
        fields = '__all__'
