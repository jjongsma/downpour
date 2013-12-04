import logging
from twisted.internet import task, defer
from downpour2.core.plugin import Plugin
from downpour2.transfers import store

class TransferManager(Plugin):

    def setup(self, config):

        self.config = config;

        if 'work_directory' in config:
            if not os.path.exists(config['work_directory']):
                try:
                    os.makedirs(config['work_directory'])
                except OSError as oe:
                    logging.error('Could not create working directory')

        store.update_store(self.application.store)

    def start(self):

        if not os.path.exists(config['work_directory']):
            logging.error('Working directory not available, not starting plugin')
            return defer.fail('Working directory not available, not starting plugin')

        logging.info('Resuming previous downloads')
        dl = [self.start_download(d.id, True) \
            for d in self.get_downloads() if d.active]

        # Start download queue checker
        self.queue_checker = task.LoopingCall(self.auto_queue).start(30, True)

        return dl

    def stop(self):

        return self.pause()
