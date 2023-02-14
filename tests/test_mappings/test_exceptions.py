from unittest import mock

from fyle.platform.exceptions import WrongParamsError, InvalidTokenError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError, NetSuiteRequestError

from tests.test_netsuite.fixtures import data as netsuite_data
from apps.mappings.tasks import auto_create_project_mappings
from .fixtures import data

def test_exception_decarator(db, mocker):
    workspace_id = 1

    mocker.patch(
        'fyle_integrations_platform_connector.apis.Projects.post_bulk',
        return_value=[]
    )
    mocker.patch(
        'fyle_integrations_platform_connector.apis.Projects.sync',
        return_value=[]
    )
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.sync_projects',
        return_value=None
    )
    mocker.patch(
        'apps.netsuite.connector.NetSuiteConnector.sync_customers',
        return_value=None
    )
    mocker.patch(
        'apps.mappings.tasks.create_fyle_projects_payload',
        return_value=data['fyle_project_payload']
    )

    mocker.patch(
        'netsuitesdk.api.customers.Customers.count',
        return_value=len(netsuite_data['get_all_projects'][0])
    )
    workspace_id = 1

    auto_create_project_mappings(workspace_id=workspace_id)

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.sync_projects') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='Something went wrong while posting to Fyle', response={'data': {
            'id': '00001'
        }})
        auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = Exception('Some bad code detected')
        auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = InvalidTokenError('Invalid Fyle refresh token')
        auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = NetSuiteRateLimitError('NetSuite rate limit exceeded')
        auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = NetSuiteLoginError('NetSuite login error')
        auto_create_project_mappings(workspace_id=1)

        mock_call.side_effect = NetSuiteRequestError(code='INSUFFICIENT_PERMISSION', message='An error occured in a search request: Permission Violation: You need  the \'Lists -> Tax Records\' permission to access this page. Please contact your account administrator.\n')
        auto_create_project_mappings(workspace_id=1)
