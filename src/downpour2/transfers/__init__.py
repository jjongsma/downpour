import os
import logging
from twisted.internet import task, defer
from downpour2.core import event
from downpour2.core.plugin import Plugin
from downpour2.transfers import store

class TransferManager(Plugin):

    def setup(self, config):

        self.LOG = logging.getLogger(__name__);

        self.config = config;

        work_dir = self.application.config.value(('downpour', 'work_directory'));
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except OSError as oe:
                self.LOG.error('Could not create directory: %s' % work_dir)

        store.update_store(self.application.store)

    def start(self):

        work_dir = self.application.config.value(('downpour', 'work_directory'));
        if not os.path.exists(work_dir):
            self.LOG.error('Working directory not available, not starting plugin')
            return defer.fail(IOError('Working directory not available, not starting plugin'))

        self.application.event_bus.subscribe(event.DOWNPOUR_PAUSED, self.pause)
        self.application.event_bus.subscribe(event.DOWNPOUR_RESUMED, self.resume)

        self.LOG.info('Resuming previous transfers')

        return defer.DeferredList([self.start_transfer(t.id, True) \
                for t in self.get_transfers() if t.active])

    def stop(self):
        return self.pause()

    def pause(self):
        return defer.succeed(True)

    def resume(self):
        return defer.succeed(True)

    def get_transfers(self):
        return list(self.application.store.find(store.Transfer,
            store.Transfer.deleted == False).order_by(store.Transfer.added))

    def start_transfer(self, id):
        return defer.succeed(True)
