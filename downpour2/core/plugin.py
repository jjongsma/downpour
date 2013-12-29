import abc

# Core plugins
from twisted.internet import defer

LIBRARY = 'downpour2.library.LibraryManager'
FEEDS = 'downpour2.feeds.FeedManager'
SEARCH = 'downpour2.search.SearchManager'
SHARING = 'downpour2.sharing.SharingManager'
WEB = 'downpour2.web.WebInterface'
AGENT = 'downpour2.agents.local.LocalAgent'


class Plugin(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, app):
        self.application = app
        self.config = {}

    def setup(self, config):
        self.config = config

    def start(self):
        return defer.succeed(True)

    def stop(self):
        return defer.succeed(True)
