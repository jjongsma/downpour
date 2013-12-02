from twisted.internet import defer

class Plugin(object):

    def __init__(self, app):
        self.application = app

    def setup(self, config):
        self.config = config

    def start(self):
        return defer.succeed(True)

    def stop(self):
        return defer.succeed(True)
