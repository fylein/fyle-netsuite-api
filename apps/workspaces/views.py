from django.contrib.auth import get_user_model

from rest_framework.response import Response
from rest_framework.views import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from fylesdk import exceptions as fyle_exc

from fyle_rest_auth.utils import AuthUtils
from fyle_rest_auth.models import AuthToken

from fyle_netsuite_api.utils import assert_valid

from .models import Workspace, FyleCredential, NetSuiteCredentials
from .serializers import WorkspaceSerializer, FyleCredentialSerializer, NetSuiteCredentialSerializer
from .utils import NSConnector

User = get_user_model()
auth_utils = AuthUtils()


class ReadyView(viewsets.ViewSet):
    """
    Ready call
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """
        Ready call
        """

        Workspace.objects.raw('Select 1 from workspaces_workspace')

        return Response(
            data={
                'message': 'Ready'
            },
            status=status.HTTP_200_OK
        )


class WorkspaceView(viewsets.ViewSet):
    """
    NetSuite Workspace
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a Workspace
        """

        all_workspaces_count = Workspace.objects.filter(user__user_id=request.user).count()

        auth_tokens = AuthToken.objects.get(user__user_id=request.user)
        fyle_user = auth_utils.get_fyle_user(auth_tokens.refresh_token)
        org_name = fyle_user['org_name']
        org_id = fyle_user['org_id']

        workspace = Workspace.objects.filter(fyle_org_id=org_id).first()
        workspace_exists = False

        if workspace:
            workspace.user.add(User.objects.get(user_id=request.user))
            workspace_exists = True
        else:
            workspace = Workspace.objects.create(name='Workspace {0}'.format(all_workspaces_count + 1))

            workspace.user.add(User.objects.get(user_id=request.user))

        if all_workspaces_count == 0 and not workspace_exists:
            workspace.name = org_name
            workspace.fyle_org_id = org_id

            workspace.save(update_fields=['name', 'fyle_org_id'])

            FyleCredential.objects.update_or_create(
                refresh_token=auth_tokens.refresh_token,
                workspace_id=workspace.id
            )

        return Response(
            data=WorkspaceSerializer(workspace).data,
            status=status.HTTP_200_OK
        )

    def get_all(self, request):
        """
        Get all workspaces
        """
        user = User.objects.get(user_id=request.user)
        workspaces = Workspace.objects.filter(user__in=[user]).all()

        return Response(
            data=WorkspaceSerializer(workspaces, many=True).data,
            status=status.HTTP_200_OK
        )

    def get_by_id(self, request, **kwargs):
        """
        Get Workspace by id
        """
        try:
            user = User.objects.get(user_id=request.user)
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'], user=user)

            return Response(
                data=WorkspaceSerializer(workspace).data if workspace else {},
                status=status.HTTP_200_OK
            )
        except Workspace.DoesNotExist:
            return Response(
                data={
                    'message': 'Workspace with this id does not exist'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ConnectNetSuiteView(viewsets.ViewSet):
    """
    NetSuite Connect View
    """

    def post(self, request, **kwargs):
        """
        Post of NetSuite Credentials
        """
        try:
            ns_account_id = request.data.get('ns_account_id')
            ns_consumer_key = request.data.get('ns_consumer_key')
            ns_consumer_secret = request.data.get('ns_consumer_secret')
            ns_token_key = request.data.get('ns_token_id')
            ns_token_secret = request.data.get('ns_token_secret')

            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])

            netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=workspace).first()

            ns = NSConnector(ns_account_id, ns_consumer_key, ns_consumer_secret, ns_token_key, ns_token_secret)
            accounts = ns.get_accounts()

            if not netsuite_credentials or not accounts:
                if workspace.ns_account_id:
                    assert_valid(ns_account_id == workspace.ns_account_id,
                                 'Please choose the correct NetSuite account')
                netsuite_credentials = NetSuiteCredentials.objects.create(
                    ns_account_id=ns_account_id,
                    ns_consumer_key=ns_consumer_key,
                    ns_consumer_secret=ns_consumer_secret,
                    ns_token_id=ns_token_key,
                    ns_token_secret=ns_token_secret,
                    workspace=workspace

                )
                workspace.ns_account_id = ns_account_id
                workspace.save(update_fields=['ns_account_id'])

            else:
                assert_valid(ns_account_id == netsuite_credentials.ns_account_id,
                             'Please choose the correct NetSuite online account')
                netsuite_credentials.ns_account_id = ns_account_id
                netsuite_credentials.ns_consumer_key = ns_consumer_key
                netsuite_credentials.ns_consumer_secret = ns_consumer_secret
                netsuite_credentials.ns_token_id = ns_token_key
                netsuite_credentials.ns_token_secret = ns_token_secret

                netsuite_credentials.save()

            return Response(
                data=NetSuiteCredentialSerializer(netsuite_credentials).data,
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {
                    'message': 'Invalid Login Attempt'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, **kwargs):
        """
        Delete NetSuite credentials
        """
        workspace_id = kwargs['workspace_id']
        NetSuiteCredentials.objects.filter(workspace_id=workspace_id).delete()

        return Response(data={
            'workspace_id': workspace_id,
            'message': 'NetSuite credentials deleted'
        })

    def get(self, request, **kwargs):
        """
        Get NetSuite Credentials in Workspace
        """
        try:
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
            fyle_credentials = NetSuiteCredentials.objects.get(workspace=workspace)

            if fyle_credentials:
                return Response(
                    data=NetSuiteCredentialSerializer(fyle_credentials).data,
                    status=status.HTTP_200_OK
                )
        except NetSuiteCredentials.DoesNotExist:
            return Response(
                data={
                    'message': 'NetSuite Credentials not found in this workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ConnectFyleView(viewsets.ViewSet):
    """
    Fyle Connect Oauth View
    """

    def post(self, request, **kwargs):
        """
        Post of Fyle Credentials
        """
        try:
            authorization_code = request.data.get('code')

            workspace = Workspace.objects.get(id=kwargs['workspace_id'])

            refresh_token = auth_utils.generate_fyle_refresh_token(authorization_code)['refresh_token']
            fyle_user = auth_utils.get_fyle_user(refresh_token)
            org_id = fyle_user['org_id']
            org_name = fyle_user['org_name']

            assert_valid(workspace.fyle_org_id and workspace.fyle_org_id == org_id,
                         'Please select the correct Fyle account - {0}'.format(workspace.name))

            workspace.name = org_name
            workspace.fyle_org_id = org_id
            workspace.save(update_fields=['name', 'fyle_org_id'])

            fyle_credentials, _ = FyleCredential.objects.update_or_create(
                workspace_id=kwargs['workspace_id'],
                defaults={
                    'refresh_token': refresh_token,
                }
            )

            return Response(
                data=FyleCredentialSerializer(fyle_credentials).data,
                status=status.HTTP_200_OK
            )
        except fyle_exc.UnauthorizedClientError:
            return Response(
                {
                    'message': 'Invalid Authorization Code'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except fyle_exc.NotFoundClientError:
            return Response(
                {
                    'message': 'Fyle Application not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except fyle_exc.WrongParamsError:
            return Response(
                {
                    'message': 'Some of the parameters are wrong'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except fyle_exc.InternalServerError:
            return Response(
                {
                    'message': 'Wrong/Expired Authorization code'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

    def delete(self, request, **kwargs):
        """Delete credentials"""
        workspace_id = kwargs['workspace_id']
        FyleCredential.objects.filter(workspace_id=workspace_id).delete()

        return Response(data={
            'workspace_id': workspace_id,
            'message': 'Fyle credentials deleted'
        })

    def get(self, request, **kwargs):
        """
        Get Fyle Credentials in Workspace
        """
        try:
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
            fyle_credentials = FyleCredential.objects.get(workspace=workspace)

            if fyle_credentials:
                return Response(
                    data=FyleCredentialSerializer(fyle_credentials).data,
                    status=status.HTTP_200_OK
                )
        except FyleCredential.DoesNotExist:
            return Response(
                data={
                    'message': 'Fyle Credentials not found in this workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
