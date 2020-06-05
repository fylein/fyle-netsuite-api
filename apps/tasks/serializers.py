from rest_framework import serializers

from .models import TaskLog


class TaskLogSerializer(serializers.ModelSerializer):
    """
    Task Log serializer
    """
    class Meta:
        model = TaskLog
        fields = '__all__'
