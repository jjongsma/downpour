from downpour2.core.plugin import Plugin
from downpour2.sharing import store

class SharingManager(Plugin):

    def setup(self, config):

        self.config = config;

        store.update_store(self.application.store)
