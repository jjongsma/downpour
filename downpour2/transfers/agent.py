from twisted.internet import defer

class TransferAgent(object):

    def pause(self, transfer):
        return defer.fail(NotImplementedError());

    def resume(self, transfer):
        return defer.fail(NotImplementedError());

    def accepts(self, transfer):
        return False

    def provision(self, transfer):
        return defer.fail(NotImplementedError());

    def transfers(self):
        return defer.fail(NotImplementedError());

    def status(self):
        return defer.fail(NotImplementedError());

class AgentStatus(object):

    host = None
    version = None
    active_downloads = 0
    queued_downloads = 0
    active_uploads = 0
    progress = 0.0
    downloadrate = 0
    uploadrate = 0
    diskfree = 0
    diskfreepct = 0.0
    connections = 0
    paused = False
