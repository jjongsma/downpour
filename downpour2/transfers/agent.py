import abc


class TransferAgent(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def pause(self):
        return NotImplemented

    @abc.abstractmethod
    def resume(self):
        return NotImplemented

    @abc.abstractmethod
    def accepts(self, transfer):
        return False

    @abc.abstractmethod
    def provision(self, transfer):
        return NotImplemented

    @abc.abstractproperty
    def transfers(self):
        return NotImplemented

    @abc.abstractmethod
    def status(self):
        return NotImplemented


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
