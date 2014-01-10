import logging
import traceback

# Standard events
DOWNPOUR_STARTED = u'downpour_started'
DOWNPOUR_SHUTDOWN = u'downpour_shutdown'
DOWNPOUR_PAUSED = u'downpour_paused'
DOWNPOUR_RESUMED = u'downpour_resumed'

# Upload / download
ADDED = u'transfer_added'
ENQUEUE = u'transfer_enqueue'
START = u'transfer_start'
INITIALIZED = u'transfer_initialized'
STARTED = u'transfer_started'
UPDATED = u'transfer_updated'
COMPLETE = u'transfer_complete'
STOP = u'transfer_stop'
STOPPED = u'transfer_stopped'
FAILED = u'transfer_failed'
REMOVE = u'transfer_remove'
REMOVED = u'transfer_removed'

# Download only
FETCHED = u'transfer_fetched'
FETCH_FAILED = u'transfer_fetch_failed'

# TODO Refactor to plugins
LIBRARY_FILE_ADDED = u'library_file_added'
LIBRARY_FILE_UPDATED = u'library_file_updated'
LIBRARY_FILE_REMOVED = u'library_file_removed'
LIBRARY_FILE_TRANSCODED = u'library_file_transcoded'

SERIES_ADDED = u'series_added'
SERIES_UPDATED = u'series_updated'
SERIES_REMOVED = u'series_removed'
SERIES_PRUNED = u'series_pruned'

FEED_ADDED = u'feed_added'
FEED_UPDATED = u'feed_updated'
FEED_REMOVED = u'feed_removed'
FEED_ITEM_ADDED = u'feed_item_added'


class EventBus(object):

    def __init__(self):
        self.listeners = {}
        self.log = logging.getLogger(__name__)

    def subscribe(self, event, listener, *args):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append([listener, args])

    def fire(self, event, *args):
        self.log.debug('event: %s' % event)
        if event in self.listeners:
            for l in self.listeners[event]:
                try:
                    cargs = []
                    cargs.extend(args)
                    cargs.extend(l[1])
                    l[0](*cargs)
                except Exception as e:
                    self.log.error('Caught error in event listener: %s' % e)
                    traceback.print_exc()

    def callback(self, result, event, *args):
        self.fire(event, *args)
        return result
