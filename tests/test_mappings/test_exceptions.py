from unittest import mock

from fyle.platform.exceptions import WrongParamsError, InvalidTokenError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError, NetSuiteRequestError

from tests.test_netsuite.fixtures import data as netsuite_data
from .fixtures import data
from apps.mappings.exceptions import handle_exceptions


def test_exception_decarator(db, mocker):
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
        'netsuitesdk.api.customers.Customers.count',
        return_value=len(netsuite_data['get_all_projects'][0])
    )

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        pass

    with mock.patch('apps.netsuite.connector.NetSuiteConnector.sync_projects') as mock_call:
        mock_call.side_effect = WrongParamsError(msg='Something went wrong while posting to Fyle', response={'data': {
            'id': '00001'
        }})
        test(workspace_id=1)

        mock_call.side_effect = Exception('Some bad code detected')
        test(workspace_id=1)

        mock_call.side_effect = InvalidTokenError('Invalid Fyle refresh token')
        test(workspace_id=1)

        mock_call.side_effect = NetSuiteRateLimitError('NetSuite rate limit exceeded')
        test(workspace_id=1)

        mock_call.side_effect = NetSuiteLoginError('NetSuite login error')
        test(workspace_id=1)

        mock_call.side_effect = NetSuiteRequestError(code='INSUFFICIENT_PERMISSION', message='An error occured in a search request: Permission Violation: You need  the \'Lists -> Tax Records\' permission to access this page. Please contact your account administrator.\n')
        test(workspace_id=1)
