import logging
import traceback

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
