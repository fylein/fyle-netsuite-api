from rest_framework import serializers

from .models import SubsidiaryMapping


class SubsidiaryMappingSerializer(serializers.ModelSerializer):
    """
    Subsidiary mappings group serializer
    """
    class Meta:
        model = SubsidiaryMapping
        fields = '__all__'
