from fyle.platform.exceptions import WrongParamsError, InvalidTokenError, NoPrivilegeError
from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError, NetSuiteRequestError

from apps.mappings.exceptions import handle_exceptions


def test_exception_decarator(db, mocker):

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise WrongParamsError(msg='Something went wrong while posting to Fyle', response={'data': {
            'id': '00001'
        }})

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise Exception('Some bad code detected')

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise InvalidTokenError('Invalid Fyle refresh token')

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise NetSuiteRateLimitError('NetSuite rate limit exceeded')

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise NetSuiteLoginError('NetSuite login error')

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise NetSuiteRequestError(code='INSUFFICIENT_PERMISSION', message='An error occured in a search request: Permission Violation: You need  the \'Lists -> Tax Records\' permission to access this page. Please contact your account administrator.\n')

    test(1)

    @handle_exceptions("Testing Exception Handling")
    def test(workspace_id: int):
        raise NoPrivilegeError('Forbidden. The user has insufficient privilege')

    test(1)
