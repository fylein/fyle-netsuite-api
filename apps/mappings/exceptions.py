import logging
import traceback

from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError, NetSuiteRequestError
from fyle.platform.exceptions import (
    WrongParamsError,
    InvalidTokenError,
    InternalServerError,
    RetryException,
    NoPrivilegeError
)
from apps.workspaces.models import NetSuiteCredentials
from fyle_integrations_imports.models import ImportLog
import requests
import zeep.exceptions as zeep_exceptions


logger = logging.getLogger(__name__)
logger.level = logging.INFO


def handle_exceptions(task_name):
    def decorator(func):
        def new_fn(workspace_id: int, *args):
            error = {
                'task': task_name,
                'workspace_id': workspace_id,
                'alert': False,
                'message': None,
                'response': None
            }
            try:
                return func(workspace_id, *args)
            except InvalidTokenError:
                error['message'] = 'Invalid Fyle refresh token'

            except WrongParamsError as exception:
                error['message'] = exception.message
                error['response'] = exception.response
                error['alert'] = True

            except NetSuiteRateLimitError:
                error['message'] = 'NetSuite rate limit reached'

            except NetSuiteLoginError:
                error['message'] = 'Invalid netsuite credentials'

            except NetSuiteRequestError as exception:
                error['message'] = 'NetSuite request error - {0}'.format(exception.code)
                error['response'] = exception.message

            except RetryException:
                error['message'] = 'Fyle Retry Exception occured'

            except InternalServerError as exception:
                error['message'] = 'Internal server error while importing to Fyle'
                error['response'] = exception.__dict__

            except requests.exceptions.HTTPError as exception:
                error['message'] = ('Gateway Time-out for netsuite (HTTPError - %s)' % exception.code)
                error['response'] = exception.__dict__

            except zeep_exceptions.Fault as exception:
                error['message'] = 'Zeep Fault error'
                error['alert'] = False
                try:
                    error['response'] = "{0} {1}".format(exception.message, exception.code)
                except Exception:
                    error['response'] = 'Zeep Fault error'

            except NoPrivilegeError as exception:
                error['message'] = 'The user has insufficient privilege'
                error['response'] = exception.__dict__
                error['alert'] = False

            except Exception:
                response = traceback.format_exc()
                error['message'] = 'Something went wrong'
                error['response'] = response
                error['alert'] = True

            if error['alert']:
                logger.error(error)
            else:
                logger.info(error)

        return new_fn

    return decorator


def handle_import_exceptions_v2(func):
    def new_fn(expense_attribute_instance, *args):
        import_log: ImportLog = args[0]
        workspace_id = import_log.workspace_id
        attribute_type = import_log.attribute_type
        error = {
            'task': 'Import {0} to Fyle and Auto Create Mappings'.format(attribute_type),
            'workspace_id': workspace_id,
            'message': None,
            'response': None
        }
        try:
            return func(expense_attribute_instance, *args)
        except WrongParamsError as exception:
            error['message'] = exception.message
            error['response'] = exception.response
            error['alert'] = True
            import_log.status = 'FAILED'

        except InvalidTokenError:
            error['message'] = 'Invalid Token for fyle'
            error['alert'] = False
            import_log.status = 'FAILED'

        except InternalServerError:
            error['message'] = 'Internal server error while importing to Fyle'
            error['alert'] = True
            import_log.status = 'FAILED'

        except (NetSuiteLoginError, NetSuiteCredentials.DoesNotExist) as exception:
            error['message'] = 'Invalid Token or NetSuite credentials does not exist workspace_id - {0}'.format(workspace_id)
            error['alert'] = False
            error['response'] = exception.__dict__
            import_log.status = 'FAILED'

        except zeep_exceptions.Fault as exception:
            error['message'] = 'Zeep Fault error'
            error['alert'] = False
            import_log.status = 'FAILED'
            try:
                error['response'] = "{0} {1}".format(exception.message, exception.code)
            except Exception:
                error['response'] = 'Zeep Fault error'

        except NoPrivilegeError as exception:
            error['message'] = 'The user has insufficient privilege'
            error['alert'] = False
            error['response'] = exception.__dict__
            import_log.status = 'FAILED'

        except Exception:
            response = traceback.format_exc()
            error['message'] = 'Something went wrong'
            error['response'] = response
            error['alert'] = False
            import_log.status = 'FATAL'

        if error['alert']:
            logger.error(error)
        else:
            logger.info(error)

        import_log.error_log = error
        import_log.save()

    return new_fn
