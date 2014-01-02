from twisted.internet import task, defer
from downpour2.core import plugin
from downpour2.feeds import store
from downpour2.feeds.web.root import FeedModule


class FeedManager(plugin.Plugin):

    def setup(self, config):

        self.config = config;

        store.update_store(self.application.store)

        if plugin.WEB in self.application.plugins:
            web = self.application.plugins[plugin.WEB]
            web.register_module(FeedModule(web))

    def start(self):

        # Start RSS feed checker
        #self.feed_checker = task.LoopingCall(checker.check_feeds, self.manager).start(60, True)

        return defer.succeed(True)
