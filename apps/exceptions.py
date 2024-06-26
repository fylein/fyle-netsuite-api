import logging

from fyle.platform.exceptions import InvalidTokenError as FyleInvalidTokenError
from fyle.platform.exceptions import NoPrivilegeError
from rest_framework.response import Response
from rest_framework.views import status
from rest_framework.exceptions import ValidationError

from apps.fyle.models import ExpenseGroup
from apps.mappings.models import GeneralMapping
from apps.workspaces.models import FyleCredential, NetSuiteCredentials, Workspace, Configuration

logger = logging.getLogger(__name__)
logger.level = logging.INFO


def handle_view_exceptions():
    def decorator(func):
        def new_fn(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ExpenseGroup.DoesNotExist:
                return Response(
                    data={'message': 'Expense group not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except FyleCredential.DoesNotExist:
                return Response(
                    data={'message': 'Fyle credentials not found in workspace'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except FyleInvalidTokenError as exception:
                logger.info(
                    'Fyle token expired workspace_id - %s %s',
                    kwargs['workspace_id'],
                    {'error': exception.response}
                )
                return Response(
                    data={'message': 'Fyle token expired workspace_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except GeneralMapping.DoesNotExist:
                return Response(
                    {'message': 'General mappings do not exist for the workspace'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except NoPrivilegeError as exception:
                logger.info(
                    'Invalid Fyle Credentials / Admin is disabled  for workspace_id%s %s',
                    kwargs['workspace_id'],
                    {'error': exception.response}
                )
                return Response(
                    data={'message': 'Invalid Fyle Credentials / Admin is disabled'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Workspace.DoesNotExist:
                return Response(
                    data={'message': 'Workspace with this id does not exist'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Configuration.DoesNotExist:
                return Response(
                    data={'message': 'Configuration does not exist in workspace'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except NetSuiteCredentials.DoesNotExist:
                logger.info('Netsuite credentials not found in workspace')
                return Response(
                    data={'message': 'Netsuite credentials not found in workspace'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except ValidationError as e:
                logger.exception(e)
                return Response(
                    {"message": e.detail},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Exception as exception:
                logger.exception(exception)
                return Response(
                    data={'message': 'An unhandled error has occurred, please re-try later'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return new_fn

    return decorator
