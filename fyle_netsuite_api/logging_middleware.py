import logging
import json
import traceback
import os
import random
import string

from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not settings.DEBUG:
            if exception:
                message = {
                    'url': request.build_absolute_uri(),
                    'error': repr(exception),
                    'traceback': traceback.format_exc()
                }
                logger.error(str(message).replace('\n', ''))

            return HttpResponse("Error processing the request.", status=500)


def generate_worker_id():
    return 'worker_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))


def set_worker_id_in_env():
    worker_id = generate_worker_id()
    os.environ['WORKER_ID'] = worker_id


def get_logger():
    if 'WORKER_ID' not in os.environ:
        set_worker_id_in_env()
    worker_id = os.environ['WORKER_ID']
    extra = {'worker_id': worker_id}
    updated_logger = logging.LoggerAdapter(logger, extra)
    updated_logger.setLevel(logging.INFO)

    return updated_logger


class WorkerIDFilter(logging.Filter):
    def filter(self, record):
        worker_id = getattr(record, 'worker_id', '')
        record.worker_id = worker_id
        return True

class LogPostRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ['POST', 'PUT'] :
            try:
                body_unicode = request.body.decode('utf-8')
                request_body = json.loads(body_unicode)
                logger.info("POST request to %s: %s", request.path, request_body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.warning("Failed to decode POST request body for %s", request.path)
            except Exception as e:
                logger.info('Something went wrong when logging post call - %s', e)

        response = self.get_response(request)
        return response
