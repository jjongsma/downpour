import logging
from twisted.internet import task, defer
from downpour2.core.plugin import Plugin

class FeedManager(Plugin):

    def start(self):

        # Start RSS feed checker
        self.feed_checker = task.LoopingCall(checker.check_feeds, self.manager).start(60, True)
        self.add_event_listener('download_imported', checker.clean_download_feed, self)

        return defer.succeed(True)
