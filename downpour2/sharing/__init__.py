from downpour2.core import plugin
from downpour2.sharing import store
from downpour2.sharing.web.root import SharingModule


class SharingManager(plugin.Plugin):

    def setup(self, config):

        self.config = config

        store.update_store(self.application.store)

        if plugin.WEB in self.application.plugins:
            web = self.application.plugins[plugin.WEB]
            web.register_module(SharingModule(web))
