from twisted.internet import defer

# Core plugins
LIBRARY = 'downpour2.library.LibraryManager'
TRANSFERS = 'downpour2.transfers.TransferManager'
FEEDS = 'downpour2.feeds.FeedManager'
SEARCH = 'downpour2.search.SearchManager'
SHARING = 'downpour2.sharing.SharingManager'
WEB = 'downpour2.web.WebInterfacePlugin'

class Plugin(object):

    def __init__(self, app):
        self.application = app

    def setup(self, config):
        self.config = config

    def start(self):
        return defer.succeed(True)

    def stop(self):
        return defer.succeed(True)
