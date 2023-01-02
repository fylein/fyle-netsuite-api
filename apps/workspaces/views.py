from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache



from rest_framework.response import Response
from rest_framework.views import status
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from fyle.platform import exceptions as fyle_exc

from fyle_rest_auth.utils import AuthUtils
from fyle_rest_auth.models import AuthToken
from fyle_rest_auth.helpers import get_fyle_admin
from fyle_accounting_mappings.models import ExpenseAttribute

from fyle_netsuite_api.utils import assert_valid

from apps.netsuite.connector import NetSuiteConnection
from apps.fyle.models import ExpenseGroupSettings
from apps.fyle.helpers import get_cluster_domain
from apps.users.models import User

from .models import Workspace, FyleCredential, NetSuiteCredentials, Configuration, \
    WorkspaceSchedule
from .tasks import schedule_sync
from .serializers import WorkspaceSerializer, FyleCredentialSerializer, NetSuiteCredentialSerializer, \
    ConfigurationSerializer, WorkspaceScheduleSerializer
from .permissions import IsAuthenticatedForTest


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

        Workspace.objects.first()

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

        access_token = request.META.get('HTTP_AUTHORIZATION')
        fyle_user = get_fyle_admin(access_token.split(' ')[1], None)
        org_name = fyle_user['data']['org']['name']
        org_id = fyle_user['data']['org']['id']

        workspace = Workspace.objects.filter(fyle_org_id=org_id).first()

        if workspace:
            workspace.user.add(User.objects.get(user_id=request.user))
            cache.delete(str(workspace.id))
        else:
            workspace = Workspace.objects.create(name=org_name, fyle_org_id=org_id)

            ExpenseGroupSettings.objects.create(workspace_id=workspace.id)

            workspace.user.add(User.objects.get(user_id=request.user))

            auth_tokens = AuthToken.objects.get(user__user_id=request.user)
            cluster_domain = get_cluster_domain(auth_tokens.refresh_token)

            FyleCredential.objects.update_or_create(
                refresh_token=auth_tokens.refresh_token,
                workspace_id=workspace.id,
                cluster_domain=cluster_domain
            )

        return Response(
            data=WorkspaceSerializer(workspace).data,
            status=status.HTTP_200_OK
        )

    def get(self, request):
        """
        Get workspace
        """
        user = User.objects.get(user_id=request.user)
        org_id = request.query_params.get('org_id')
        workspace = Workspace.objects.filter(user__in=[user], fyle_org_id=org_id).all()

        return Response(
            data=WorkspaceSerializer(workspace, many=True).data,
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
            ns_consumer_key = settings.NS_CONSUMER_KEY
            ns_consumer_secret = settings.NS_CONSUMER_SECRET
            ns_token_key = request.data.get('ns_token_id')
            ns_token_secret = request.data.get('ns_token_secret')

            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])

            netsuite_credentials = NetSuiteCredentials.objects.filter(workspace=workspace).first()

            connection = NetSuiteConnection(ns_account_id, ns_consumer_key, ns_consumer_secret, ns_token_key,
                                            ns_token_secret)
            accounts = connection.accounts.get_all_generator(1)

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
                workspace.save()

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
            netsuite_credentials = NetSuiteCredentials.objects.get(workspace=workspace)

            if netsuite_credentials:
                return Response(
                    data=NetSuiteCredentialSerializer(netsuite_credentials).data,
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

            tokens = auth_utils.generate_fyle_refresh_token(authorization_code)
            refresh_token = tokens['refresh_token']

            fyle_user = get_fyle_admin(tokens['access_token'], None)
            org_name = fyle_user['data']['org']['name']
            org_id = fyle_user['data']['org']['id']

            assert_valid(workspace.fyle_org_id and workspace.fyle_org_id == org_id,
                         'Please select the correct Fyle account - {0}'.format(workspace.name))

            workspace.name = org_name
            workspace.fyle_org_id = org_id
            workspace.save()

            cluster_domain = get_cluster_domain(refresh_token)

            fyle_credentials, _ = FyleCredential.objects.update_or_create(
                workspace_id=kwargs['workspace_id'],
                defaults={
                    'refresh_token': refresh_token,
                    'cluster_domain': cluster_domain
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
        except Exception:
            return Response(
                {
                    'message': 'Signature has expired'
                },
                status=status.HTTP_403_FORBIDDEN
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


class ScheduleView(viewsets.ViewSet):
    """
    Schedule View
    """
    def post(self, request, **kwargs):
        """
        Post Settings
        """
        schedule_enabled = request.data.get('schedule_enabled')
        assert_valid(schedule_enabled is not None, 'Schedule enabled cannot be null')

        hours = request.data.get('hours')
        assert_valid(hours is not None, 'Hours cannot be left empty')

        email_added = request.data.get('added_email')
        emails_selected = request.data.get('selected_email')

        workspace_schedule_settings = schedule_sync(
            workspace_id=kwargs['workspace_id'],
            schedule_enabled=schedule_enabled,
            hours=hours,
            email_added=email_added,
            emails_selected=emails_selected
        )

        return Response(
            data=WorkspaceScheduleSerializer(workspace_schedule_settings).data,
            status=status.HTTP_200_OK
        )

    def get(self, *args, **kwargs):
        try:
            schedule = WorkspaceSchedule.objects.get(workspace_id=kwargs['workspace_id'])

            return Response(
                data=WorkspaceScheduleSerializer(schedule).data,
                status=status.HTTP_200_OK
            )
        except WorkspaceSchedule.DoesNotExist:
            return Response(
                data={
                    'message': 'Schedule settings does not exist in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ConfigurationsView(generics.ListCreateAPIView):
    """
    General Settings
    """
    serializer_class = ConfigurationSerializer
    queryset = Configuration.objects.all()

    def get(self, request, *args, **kwargs):
        """
        Get workspace general settings
        """
        try:
            configuration = self.queryset.get(workspace_id=kwargs['workspace_id'])
            return Response(
                data=self.serializer_class(configuration).data,
                status=status.HTTP_200_OK
            )
        except Configuration.DoesNotExist:
            return Response(
                {
                    'message': 'General Settings does not exist in workspace'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request, **kwargs):
        """
        PATCH workspace configuration settings
        """
        configurations_object = Configuration.objects.get(workspace_id=kwargs['workspace_id'])
        serializer = ConfigurationSerializer(
            configurations_object, data=request.data, partial=True
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                data=serializer.data,
                status=status.HTTP_200_OK
            )

class WorkspaceAdminsView(viewsets.ViewSet):

    def get(self, request, *args, **kwargs):
        """
        Get Admins for the workspaces
        """

        workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
        
        admin_email = []
        users = workspace.user.all()
        for user in users:
            admin = User.objects.get(user_id=user)
            name = ExpenseAttribute.objects.get(
                value=admin.email, 
                workspace_id=kwargs['workspace_id'],
                attribute_type='EMPLOYEE'
            ).detail['full_name']

            admin_email.append({
                'name': name,
                'email': admin.email
            })

        return Response(
                data=admin_email,
                status=status.HTTP_200_OK
            )

class SetupE2ETestView(viewsets.ViewSet):
    """
    NetSuite Workspace
    """
    authentication_classes = []
    permission_classes = [IsAuthenticatedForTest]

    def post(self, request, **kwargs):
        """
        Setup end to end test for a given workspace
        """
        try:
            workspace = Workspace.objects.get(pk=kwargs['workspace_id'])
            error_message = 'Something unexpected has happened. Please try again later.'

            # Filter out prod orgs
            if 'fyle for' in workspace.name.lower():
                with transaction.atomic():
                    # Reset the workspace completely
                    with connection.cursor() as cursor:
                        cursor.execute('select reset_workspace(%s)', [workspace.id])

            return Response(status=status.HTTP_200_OK, data={'message': {}})

        except Exception as error:
            logger.error(error)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'message': 'Not e2e test workspace'})
