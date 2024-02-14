import logging
import traceback

from netsuitesdk import NetSuiteRateLimitError, NetSuiteLoginError, NetSuiteRequestError
from fyle.platform.exceptions import (
    WrongParamsError,
    InvalidTokenError,
    InternalServerError,
    RetryException
)
import requests


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
                error['message'] = 'NetSuite request error - '.format(exception.code)
                error['response'] = exception.message

            except RetryException:
                error['message'] = 'Fyle Retry Exception occured'

            except InternalServerError as exception:
                error['message'] = 'Internal server error while importing to Fyle'
                error['response'] = exception.__dict__

            except requests.exceptions.HTTPError as exception:
                error['message'] = 'Gateway Time-out for netsuite (HTTPError - %s)'.format(exception.code)
                error['response'] = exception.__dict__

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
