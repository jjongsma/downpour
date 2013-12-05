from downpour2.core.plugin import Plugin
from downpour2.library import store

class LibraryManager(Plugin):

    def setup(self, config):

        self.config = config;

        store.update_store(self.application.store)
