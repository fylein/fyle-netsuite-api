from rest_framework import serializers

from .models import Bill, BillLineitem, ExpenseReport, ExpenseReportLineItem, JournalEntry, JournalEntryLineItem


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


class ExpenseReportSerializer(serializers.ModelSerializer):
    """
    NetSuite Expense Report serializer
    """
    class Meta:
        model = ExpenseReport
        fields = '__all__'


class ExpenseReportLineItemSerializer(serializers.ModelSerializer):
    """
    NetSuite ExpenseReport Lineitem serializer
    """
    class Meta:
        model = ExpenseReportLineItem
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    """
    NetSuite Journal Entry serializer
    """
    class Meta:
        model = JournalEntry
        fields = '__all__'


class JournalEntryLineItemSerializer(serializers.ModelSerializer):
    """
    NetSuite JournalEntry Lineitem serializer
    """
    class Meta:
        model = JournalEntryLineItem
        fields = '__all__'
