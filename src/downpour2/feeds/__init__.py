from twisted.internet import task, defer
from downpour2.core.plugin import Plugin
from downpour2.feeds import store

class FeedManager(Plugin):

    def setup(self, config):

        self.config = config;

        store.update_store(self.application.store)

    def start(self):

        # Start RSS feed checker
        #self.feed_checker = task.LoopingCall(checker.check_feeds, self.manager).start(60, True)

        return defer.succeed(True)
