"""
Workspace Serializers
"""
from rest_framework import serializers

from .models import Workspace, FyleCredential, NetSuiteCredentials, WorkspaceSchedule, WorkspaceGeneralSettings


class WorkspaceSerializer(serializers.ModelSerializer):
    """
    Workspace serializer
    """

    class Meta:
        model = Workspace
        fields = '__all__'


class FyleCredentialSerializer(serializers.ModelSerializer):
    """
    Fyle credential serializer
    """

    class Meta:
        model = FyleCredential
        fields = '__all__'


class NetSuiteCredentialSerializer(serializers.ModelSerializer):
    """
    NetSuite credential serializer
    """

    class Meta:
        model = NetSuiteCredentials
        fields = ['id', 'workspace_id', 'ns_account_id', 'created_at', 'updated_at']


class WorkspaceScheduleSerializer(serializers.ModelSerializer):
    """
    Workspace Schedule Serializer
    """
    class Meta:
        model = WorkspaceSchedule
        fields = '__all__'


class WorkSpaceGeneralSettingsSerializer(serializers.ModelSerializer):
    """
    General settings serializer
    """
    class Meta:
        model = WorkspaceGeneralSettings
        fields = '__all__'
