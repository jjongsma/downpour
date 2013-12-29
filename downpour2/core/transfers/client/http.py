import time
import os
import gzip
import logging
from twisted.web import http
from twisted.web.client import HTTPDownloader, _makeGetterFactory
from twisted.protocols.htb import ShapedProtocolFactory
from downpour2.core import VERSION
from downpour2.core.net.throttling import ThrottledBucketFilter
from downpour2.core.transfers import state, client, event


class HTTPDownloadClientFactory(client.TransferClientFactory):

    def __init__(self, application, agent, work_dir):
        self.application = application
        self.agent = agent
        self.working_directory = work_dir

    def client(self, transfer):
        return HTTPDownloadClient(transfer, self.application, self.agent, self.working_directory)


class HTTPDownloadClient(client.SimpleDownloadClient):

    def __init__(self, transfer, application, agent, work_dir):
        """

        @param transfer:
        @type transfer: downpour2.core.store.Transfer
        @param application:
        @type application: downpour2.core.Application
        @param agent:
        @type agent: downpour2.core.transfers.agent.TransferAgent
        """

        super(HTTPDownloadClient, self).__init__(transfer, application)

        self.log = logging.getLogger(__name__)
        self.agent = agent
        self.original_mimetype = None
        self.factory = None
        self.rate = 0

        transfer_work_dir = os.path.sep.join((work_dir, self.transfer.id))

        if not os.path.exists(transfer_work_dir):
            os.makedirs(transfer_work_dir)

        self.working_directory = transfer_work_dir

    def onstart(self):

        self.original_mimetype = self.transfer.mime_type
        self.transfer.state = state.STARTING

        bucket_filter = ThrottledBucketFilter(0, self.agent.download_filter())

        factory_factory = lambda url, *a, **kw: HTTPManagedDownloader(
            str(self.transfer.url),
            os.path.join(self.working_directory, self.transfer.filename),
            statusCallback=DownloadStatus(self.transfer),
            bucketFilter=bucket_filter, *a, **kw)

        self.factory = _makeGetterFactory(str(self.transfer.url), factory_factory)
        self.factory.deferred.addCallback(lambda x: self.fire(event.COMPLETE))
        self.factory.deferred.addErrback(lambda x: self.fire(event.FAILED))

        return True

    def onbeforetransfer_complete(self):

        # Check if mimetype reported by server has changed from original
        if self.transfer.mime_type != self.original_mimetype:

            try:

                # Check if new mimetype dictates a different download handler
                next_client = self.agent.client(self.transfer)

                if next_client != self:

                    # New mimetype requires different download handler, we just downloaded a metadata file
                    self.log.debug(u'Got metadata for %s (%s)' % (self.transfer.id, self.transfer.description))

                    metafile = os.path.sep.join((self.working_directory, self.transfer.filename))
                    if os.access(metafile, os.R_OK):
                        f = open(metafile, 'rb')
                        self.transfer.metadata = f.read()
                        f.close()

                    if self.agent.reprovision(self):
                        return False

            except NotImplementedError:
                pass

    def onstopping(self):

        if self.factory.connector:
            self.factory.connector.disconnect()

        self.fire(event.STOPPED)

    @property
    def download_rate(self):
        return self.rate

    @download_rate.setter
    def download_rate(self, rate):
        self.rate = rate
        self.factory.setRateLimit(rate)

    def files(self):
        return ({'path': self.transfer.filename,
                 'size': self.transfer.size,
                 'progress': self.transfer.progress},)


class DownloadStatus(object):

    def __init__(self, download):
        self.download = download
        self.bytes_start = 0
        self.bytes_downloaded = 0
        self.start_time = 0
        self.start_elapsed = 0
        self.download_rate = 0
        self.last_rate_sample = 0
        self.rate_samples = []

    def onConnect(self, downloader):
        self.download.state = state.STARTING

    def onError(self, downloader):
        self.download.state = state.FAILED
        self.download.health = 0

    def onStop(self, downloader):
        if self.download.state != state.FAILED:
            if self.download.progress == 100:
                self.download.state = state.COMPLETED
            else:
                self.download.state = state.STOPPED
        self.download.elapsed = self.download.elapsed + (time.time() - self.start_time)

    def onHeaders(self, downloader, headers):
        contentLength = 0
        if downloader.requestedPartial:
            contentRange = headers.get('content-range', None)
            start, end, contentLength = http.parseContentRange(contentRange[0])
            self.bytes_start = start - 1
            self.bytes_downloaded = self.bytes_start
        else:
            contentLength = headers.get('content-length', [0])[0]
        self.download.size = float(contentLength)
        contentType = headers.get('content-type', None)
        if contentType:
            self.download.mime_type = unicode(contentType[0])
        contentDisposition = headers.get('content-disposition', None)
        if contentDisposition and contentDisposition[0].startswith('attachment'):
            newName = contentDisposition[0].split('=')[1]
            if newName[0] == '"' and newName[len(newName) - 1] == '"':
                newName = newName[1:len(newName) - 1]
            if downloader.renameFile(newName):
                self.download.filename = unicode(newName)

    def onStart(self, downloader, partialContent):
        self.start_time = time.time()
        self.start_elapsed = self.download.elapsed
        self.download.state = state.DOWNLOADING
        self.download.health = 100

    def onPart(self, downloader, data):
        self.bytes_downloaded = self.bytes_downloaded + len(data)
        if self.download.size:
            self.download.progress = (float(self.bytes_downloaded)
                                      / float(self.download.size)) * 100

        now = int(time.time())
        if self.last_rate_sample == 0:
            self.last_rate_sample = now
            self.rate_samples.insert(0, self.bytes_downloaded)
        elif now > self.last_rate_sample:
            for i in range(self.last_rate_sample, now):
                self.rate_samples.insert(0, self.bytes_downloaded)
            while len(self.rate_samples) > 10:
                self.rate_samples.pop()
            if len(self.rate_samples) > 1:
                rate_diff = []
                for i in range(0, len(self.rate_samples) - 1):
                    rate_diff.append(self.rate_samples[i] - self.rate_samples[i + 1])
                self.download_rate = float(sum(rate_diff)) / len(rate_diff)
            self.last_rate_sample = now

        self.download.downloadrate = self.download_rate

        self.download.downloaded = self.bytes_downloaded
        self.download.elapsed = self.start_elapsed + (now - self.start_time)
        if self.download.size and self.download_rate:
            self.download.timeleft = float(self.download.size - self.bytes_downloaded) / self.download_rate

    def onEnd(self, downloader):
        self.download.progress = 100
        self.download.state = state.COMPLETED
        self.download_rate = (self.bytes_downloaded - self.bytes_start) / (time.time() - self.start_time)


# noinspection PyPep8Naming,PyClassicStyleClass
class HTTPManagedDownloader(HTTPDownloader):
    def __init__(self, url, file, statusCallback=None, bucketFilter=None, *args, **kwargs):
        self.bytes_received = 0
        self.encoding = None
        self.statusHandler = statusCallback
        self.bucketFilter = bucketFilter

        # TODO: Apparently this only works for servers, not clients :/
        if self.bucketFilter:
            self.protocol = ShapedProtocolFactory(self.protocol, self.bucketFilter)

        HTTPDownloader.__init__(self, url, file, supportPartial=1,
                                agent='Downpour v%s' % VERSION,
                                *args, **kwargs)

        self.origPartial = self.requestedPartial

    def setRateLimit(self, rate=None):
        if self.bucketFilter:
            self.bucketFilter.rate = rate

    def renameFile(self, newName):
        fullName = os.path.sep.join((os.path.dirname(self.fileName), newName))
        # Only override filename if we're not resuming a download
        if not self.requestedPartial or not os.path.exists(self.fileName):
            self.fileName = fullName
            return True
        elif os.rename(self.fileName, fullName):
            self.fileName = fullName
            return True
        return False

    def gotHeaders(self, headers):
        HTTPDownloader.gotHeaders(self, headers)
        # This method is being called twice sometimes,
        # first time without a content-range
        self.encoding = headers.get('content-encoding', None)
        contentRange = headers.get('content-range', None)
        if contentRange and self.requestedPartial == 0:
            self.requestedPartial = self.origPartial
        if self.statusHandler:
            self.statusHandler.onHeaders(self, headers)

    def pageStart(self, partialContent):
        HTTPDownloader.pageStart(self, partialContent)
        if self.statusHandler:
            self.statusHandler.onStart(self, partialContent)

    def pagePart(self, data):
        HTTPDownloader.pagePart(self, data)
        if self.statusHandler:
            self.statusHandler.onPart(self, data)

    def pageEnd(self):
        if self.statusHandler:
            self.statusHandler.onEnd(self)
            # And the hacks are piling up, Twisted is really not very flexible
        if self.encoding[0] == 'gzip':
            self.file.close()
            g = gzip.open(self.fileName, 'rb')
            # This will blow up for large files
            decompressed = g.read()
            g.close()
            self.file = open(self.fileName, 'wb');
            self.file.write(decompressed);
        HTTPDownloader.pageEnd(self)

    def startedConnecting(self, connector):
        self.connector = connector
        if self.statusHandler:
            self.statusHandler.onCnnect(self)
        HTTPDownloader.startedConnecting(self, connector)

    def clientConnectionFailed(self, connector, reason):
        if self.statusHandler:
            self.statusHandler.onError(self)
        HTTPDownloader.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        if self.statusHandler:
            self.statusHandler.onStop(self)
        HTTPDownloader.clientConnectionLost(self, connector, reason)


# noinspection PyPep8Naming,PyShadowingNames,PyArgumentList,PyShadowingBuiltins
def downloadFile(url, file, statusCallback=None, bucketFilter=None, contextFactory=None, *args, **kwargs):

    factory_factory = lambda url, *a, **kw: HTTPManagedDownloader(
        url, file, statusCallback=statusCallback,
        bucketFilter=bucketFilter, *a, **kw)

    return _makeGetterFactory(
        url,
        factorFactory=factory_factory,
        contextFactory=contextFactory,
        *args, **kwargs).deferred
