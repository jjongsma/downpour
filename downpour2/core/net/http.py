import abc
import os
import gzip
from twisted.web.client import HTTPDownloader, _makeGetterFactory
from downpour2.core import VERSION


# noinspection PyPep8Naming
class HTTPManagedDownloader(HTTPDownloader, object):
    def __init__(self, url, save_file, status_callback=None, bucket_filter=None, *args, **kwargs):

        self.bytes_received = 0
        self.encoding = None
        self.status_handler = status_callback
        self.bucket_filter = bucket_filter
        self.connector = None

        # TODO: Apparently this only works for servers, not clients :/
        # if self.bucket_filter:
        #    self.protocol = ShapedProtocolFactory(self.protocol, self.bucket_filter)

        HTTPDownloader.__init__(self, url, save_file, supportPartial=1,
                                agent='Downpour v%s' % VERSION,
                                *args, **kwargs)

        self.orig_partial = self.requestedPartial

    def set_rate_limit(self, rate=None):
        if self.bucket_filter:
            self.bucket_filter.rate = rate

    def rename_file(self, new_name):
        full_name = os.path.sep.join((os.path.dirname(self.fileName), new_name))
        # Only override filename if we're not resuming a download
        if not self.requestedPartial or not os.path.exists(self.fileName):
            self.fileName = full_name
            return True
        elif os.rename(self.fileName, full_name):
            self.fileName = full_name
            return True
        return False

    def gotHeaders(self, headers):
        HTTPDownloader.gotHeaders(self, headers)
        # This method is being called twice sometimes, first time without a content-range
        self.encoding = headers.get('content-encoding', None)
        content_range = headers.get('content-range', None)
        if content_range and self.requestedPartial == 0:
            self.requestedPartial = self.orig_partial
        if self.status_handler:
            self.status_handler.onheaders(self, headers)

    def pageStart(self, partial_content):
        HTTPDownloader.pageStart(self, partial_content)
        if self.status_handler:
            self.status_handler.onstart(self, partial_content)

    def pagePart(self, data):
        HTTPDownloader.pagePart(self, data)
        if self.status_handler:
            self.status_handler.onpart(self, data)

    def pageEnd(self):
        if self.status_handler:
            self.status_handler.onend(self)
            # And the hacks are piling up, Twisted is really not very flexible
        if self.encoding[0] == 'gzip':
            self.file.close()
            g = gzip.open(self.fileName, 'rb')
            # This will blow up for large files
            decompressed = g.read()
            g.close()
            self.file = open(self.fileName, 'wb')
            self.file.write(decompressed)
        HTTPDownloader.pageEnd(self)

    def startedConnecting(self, connector):
        self.connector = connector
        if self.status_handler:
            self.status_handler.onconnect(self)
        HTTPDownloader.startedConnecting(self, connector)

    def clientConnectionFailed(self, connector, reason):
        if self.status_handler:
            self.status_handler.onerror(self)
        HTTPDownloader.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        if self.status_handler:
            self.status_handler.onstop(self)
        HTTPDownloader.clientConnectionLost(self, connector, reason)


# noinspection PyUnusedLocal
class DownloadStatus(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def onconnect(self, downloader):
        return NotImplemented

    @abc.abstractmethod
    def onerror(self, downloader):
        return NotImplemented

    @abc.abstractmethod
    def onstop(self, downloader):
        return NotImplemented

    @abc.abstractmethod
    def onheaders(self, downloader, headers):
        return NotImplemented

    @abc.abstractmethod
    def onstart(self, downloader, partial_content):
        return NotImplemented

    @abc.abstractmethod
    def onpart(self, downloader, data):
        return NotImplemented

    @abc.abstractmethod
    def onend(self, downloader):
        return NotImplemented


def download_file(download_url, save_file, status_callback=None, bucket_filter=None, context_factory=None, *args,
                  **kwargs):

    factory_factory = lambda url, *a, **kw: HTTPManagedDownloader(
        url, save_file, status_callback=status_callback,
        bucket_filter=bucket_filter, *a, **kw)

    return _makeGetterFactory(
        download_url,
        factorFactory=factory_factory,
        contextFactory=context_factory,
        *args, **kwargs).deferred
