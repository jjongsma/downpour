import logging, traceback

# Standard events
DOWNPOUR_STARTED = 'downpour_started'
DOWNPOUR_SHUTDOWN = 'downpour_shutdown'
DOWNPOUR_PAUSED = 'downpour_paused'
DOWNPOUR_RESUMED = 'downpour_resumed'

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
        self.LOG = logging.getLogger(__name__);

    def subscribe(self, event, listener, *args):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append([listener, args])

    def fire(self, event, *args):
        self.LOG.debug('event: %s' % event)
        if event in self.listeners:
            for l in self.listeners[event]:
                try:
                    cargs = []
                    cargs.extend(args)
                    cargs.extend(l[1])
                    l[0](*cargs)
                except Exception as e:
                    self.LOG.error('Caught error in event listener: %s' % e)
                    traceback.print_exc()

    def callback(self, result, event, *args):
        self.fire_event(event, *args)
        return result
