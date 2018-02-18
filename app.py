# pylint: disable=C0413,E0401
"""Tenreads database monitor API
Runs a minimal Tornado API that notifies on a database connection drop.
Uses periodic callback to plug a listener that sends out an incoming
webhook notification to a specified Slack channel/other receivers.

TODO: Ways to configure notifications

"""

__all__ = ("run_api",)
__author__ = "Sriram Velamur<sriram.velamur@gmail.com>"

import sys
sys.dont_write_bytecode = True
from os import getenv
from datetime import datetime, timedelta

from tornado.web import RequestHandler, Application
from tornado.ioloop import IOLoop, PeriodicCallback
from pymongo.mongo_client import MongoClient

try:
    DATABASE = MongoClient()["testdb"]
except BaseException:
    print("Unable to connect to database. Cannot proceed")
    sys.exit(1)

LAST_NOTIFIED = None
DATABASE_STATE_CHANGED = False


def is_database_available(database):
    """Helper to check the availability status of the database"""
    global DATABASE_STATE_CHANGED, LAST_NOTIFIED
    try:
        database.collection_names()
        if DATABASE_STATE_CHANGED:
            DATABASE_STATE_CHANGED = False
            LAST_NOTIFIED = None
            notify_db_return()
        return True
    except BaseException as db_error:
        DATABASE_STATE_CHANGED = True
        notify_error(db_error)
        return False


def notify_db_return():
    """Helper to notify the consumers of the database returning"""
    print("Database back up...")


def notify_error(db_error):
    """Helper to notify the targets on database failure"""
    current_time_stamp = datetime.utcnow()
    global LAST_NOTIFIED
    if LAST_NOTIFIED is not None:
        valid = current_time_stamp >= LAST_NOTIFIED + timedelta(minutes=5)
    else:
        valid = True

    failure_msg = "Database connection failed. Attempting to notify {}"

    if valid:
        LAST_NOTIFIED = current_time_stamp
        print(failure_msg.format(db_error))


class MonitorApplication(Application):
    """Application class for database monitor"""

    def __init__(self, *args, **kwargs):
        """Database monitor application class init"""
        kwargs.update({"debug": getenv("debug")  == "True"})
        super(MonitorApplication, self).__init__(*args, **kwargs)
        self.database = DATABASE
        PeriodicCallback(
            lambda: is_database_available(DATABASE), 500
        ).start()
        self.loop = IOLoop.instance()

    def run(self, port=9999):
        """
        Helper to start the app and listen on the specified port.

        :param port: Port to listen on
        :type  port: int
        """
        if not isinstance(port, int):
            port = 9999
        print("Listening on http://0.0.0.0:{}".format(port))
        try:
            self.listen(port)
            self.loop.start()
        except KeyboardInterrupt:
            print("Exiting monitoring app")


def run_api():
    """Main runner for monitor API"""
    MonitorApplication().run()


if __name__ == '__main__':
    run_api()
