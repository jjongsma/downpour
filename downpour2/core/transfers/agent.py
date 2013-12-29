import abc
from downpour2.core.net.throttling import ThrottledBucketFilter


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
        """
        Create a client for a transfer and enqueue it for download if it is not already.

        @param transfer: The transfer
        @type transfer: downpour2.core.store.Transfer
        @return: The download client
        @rtype: downpour2.core.transfers.client.DownloadClient
        """

        return NotImplemented

    @abc.abstractmethod
    def reprovision(self, existing):
        """
        Re-inject an existing transfer back into the transfer queue after metadata has changed. If the
        metadata requires using a different download client transport, the transfer state will be reset
        and the new client will replace the existing one in the active transfer queue.

        @param existing: The existing download client
        @type existing: downpour2.core.transfers.client.DownloadClient
        @return: The new download client, or None if no re-provisioning is needed
        @rtype existing: downpour2.core.transfers.client.DownloadClient
        """

        return NotImplemented

    @abc.abstractmethod
    def client(self, transfer):
        """
        Retrieve (or creates) a download client for the specified transfer. This differs from provision()
        in that it does not automatically enqueue the transfer for download, which allows for manual creation
        and comparison of clients.

        @param transfer: The transfer to create a download client for
        @type transfer: downpour2.core.store.Transfer
        @return: The download client
        @rtype: downpour2.core.transfers.client.DownloadClient
        """

        return NotImplemented

    @abc.abstractproperty
    def transfers(self):
        return NotImplemented

    def transfer(self, tid):
        for t in self.transfers:
            if t.id == tid:
                return t
        return None

    @abc.abstractproperty
    def status(self):
        return NotImplemented

    def upload_filter(self):
        return ThrottledBucketFilter()

    def download_filter(self):
        return ThrottledBucketFilter()


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

    local_updated = 0
    transfers_updated = 0
