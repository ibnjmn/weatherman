import os
import sys

class User(object):
    """
    Represents a user of the service.
    """
    address = ""
    events = []
    regions = []
    message_format = ""
    truncate_txt = True

    def __init__(self,
                 address = "",
                 events = [],
                 regions = [],
                 message_format = "",
                 truncate_txt = True):
        """
        Initialize a user
        """
        self.address = address
        self.events = events
        self.regions = regions
        self.message_format = message_format
        self.truncate_txt = truncate_txt

    def __repr__(self):
        return 'User: %s' % self.address


class Model(object):
    """
    Superclass for weatherman's persistence model
    """
    __alert_log = []
    __users = {}
    __email_log = []

    def load(self, filename):
        """
        Load data from a file
        """
        pass

    def save(self, filename):
        """
        Save data to a file
        """
        pass

    def log_email(self, recipient, message):
        """
        Record what message was just sent.
        """
        self.__email_log.append((recipient, message))

    def iter_users(self):
        """
        Iterate through currently existing users
        """
        for u in self.__users.values():
            yield u

    def add_user(self, user):
        """
        Record a user in the database
        """
        self.__users[user.address] = user

    def get_user(self, address):
        """
        Fetch a particular user
        """
        return self.__users[address]

    def insert_alert(self, alert):
        """
        Record an alert ID so that we know we've seen it.
        """
        self.__alert_log.append(alert)
        
