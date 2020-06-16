from rest_framework import serializers

from .models import Bill, BillLineitem


class BillSerializer(serializers.ModelSerializer):
    """
    NetSuite Bill serializer
    """
    class Meta:
        model = Bill
        fields = '__all__'


class BillLineItemSerializer(serializers.ModelSerializer):
    """
    NetSuite Bill Lineitem serializer
    """
    class Meta:
        model = BillLineitem
        fields = '__all__'
