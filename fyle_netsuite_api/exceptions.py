"""
Exceptions
"""


class BulkError(Exception):
    """
    Bulk Error Exception.

    Parameters:
        msg (str): Short description of the error.
        response: Error response.
    """

    def __init__(self, msg, response=None):
        super(BulkError, self).__init__(msg)
        self.message = msg
        self.response = response

    def __str__(self):
        return repr(self.message)
