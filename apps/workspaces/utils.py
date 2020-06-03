import itertools
from netsuitesdk import NetSuiteConnection


class NSConnector:
    """
    NetSuite Utility Functions
    """
    def __init__(self, account, consumer_key, consumer_secret, token_key, token_secret):
        self.connection = NetSuiteConnection(
            account=account,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            token_key=token_key,
            token_secret=token_secret
        )

    def get_accounts(self):
        """
        Get accounts
        """
        return list(itertools.islice(self.connection.accounts.get_all_generator(), 100))

    def get_locations(self):
        """
        Get locations
        """
        return self.connection.locations.get_all()

    def get_departments(self):
        """
        Get departments
        """
        return self.connection.departments.get_all()

    def get_vendors(self):
        """
        Get vendors
        """
        return list(itertools.islice(self.connection.vendors.get_all_generator(), 10))
