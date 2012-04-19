class Plugin(object):

    def __init__(self, app):
        self.application = app

    def setup(self, config):
        self.config = config

    def start(self):
        pass

    def stop(self):
        pass
