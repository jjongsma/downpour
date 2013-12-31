import logging, traceback

# Standard events
DOWNPOUR_STARTED = 'downpour_started'
DOWNPOUR_SHUTDOWN = 'downpour_shutdown'
DOWNPOUR_PAUSED = 'downpour_paused'
DOWNPOUR_RESUMED = 'downpour_resumed'

# Upload / download
ADDED = 'transfer_added'
ENQUEUE = 'transfer_enqueue'
START = 'transfer_start'
INITIALIZED = 'transfer_initialized'
STARTED = 'transfer_started'
UPDATED = 'transfer_updated'
COMPLETE = 'transfer_complete'
STOP = 'transfer_stop'
STOPPED = 'transfer_stopped'
FAILED = 'transfer_failed'
REMOVE = 'transfer_remove'
REMOVED = 'transfer_removed'

# Download only
FETCHED = 'transfer_fetched'
FETCH_FAILED = 'transfer_fetch_failed'

# TODO Refactor to plugins
LIBRARY_FILE_ADDED = 'library_file_added'
LIBRARY_FILE_UPDATED = 'library_file_updated'
LIBRARY_FILE_REMOVED = 'library_file_removed'
LIBRARY_FILE_TRANSCODED = 'library_file_transcoded'

SERIES_ADDED = 'series_added'
SERIES_UPDATED = 'series_updated'
SERIES_REMOVED = 'series_removed'
SERIES_PRUNED = 'series_pruned'

FEED_ADDED = 'feed_added'
FEED_UPDATED = 'feed_updated'
FEED_REMOVED = 'feed_removed'
FEED_ITEM_ADDED = 'feed_item_added'


class EventBus:

    def __init__(self):
        self.listeners = {}
        self.log = logging.getLogger(__name__);

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
        self.fire_event(event, *args)
        return result
