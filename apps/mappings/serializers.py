from rest_framework import serializers

from .models import GeneralMapping, SubsidiaryMapping


class SubsidiaryMappingSerializer(serializers.ModelSerializer):
    """
    Subsidiary mappings group serializer
    """
    class Meta:
        model = SubsidiaryMapping
        fields = '__all__'


class GeneralMappingSerializer(serializers.ModelSerializer):
    """
    General mappings group serializer
    """
    class Meta:
        model = GeneralMapping
        fields = '__all__'
