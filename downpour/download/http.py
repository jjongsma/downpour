from downpour.core import VERSION
from downpour.download import *
from downpour.download.throttling import ThrottledBucketFilter
from twisted.web import http
from twisted.web.client import HTTPDownloader, _makeGetterFactory
from twisted.internet import defer
from twisted.protocols.htb import ShapedProtocolFactory
import time, os

class HTTPDownloadClient(DownloadClient):

    def start(self):
        self.original_mimetype = self.download.mime_type
        self.download.status = Status.STARTING
        bucketFilter = ThrottledBucketFilter(0, self.manager.get_download_rate_filter())
        factoryFactory = lambda url, *a, **kw: HTTPManagedDownloader(str(self.download.url),
                                    os.path.join(self.directory, self.download.filename),
                                    statusCallback=DownloadStatus(self.download),
                                    bucketFilter=bucketFilter, *a, **kw)
        self.factory = _makeGetterFactory(str(self.download.url), factoryFactory)
        self.factory.deferred.addCallback(self.check_mimetype);
        self.factory.deferred.addErrback(self.errback);
        return True

    def check_mimetype(self, *args):
        self.callback(self.download.mime_type != self.original_mimetype)

    def stop(self):
        self.download.status = Status.STOPPED
        self.download.downloadrate = 0
        if self.factory.connector:
            self.factory.connector.disconnect()
            return True
        return False

    def set_download_rate(self, rate):
        self.download_rate = rate
        self.factory.setRateLimit(rate)

    def get_files(self):
        return ({'path': self.download.filename,
                 'size': self.download.size,
                 'progress': self.download.progress},)

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
        self.download.status = Status.STARTING

    def onError(self, downloader):
        self.download.status = Status.FAILED
        self.download.health = 0

    def onStop(self, downloader):
        if self.download.status != Status.FAILED:
            if self.download.progress == 100:
                self.download.status = Status.COMPLETED
            else:
                self.download.status = Status.STOPPED
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
            if newName[0] == '"' and newName[len(newName)-1] == '"':
                newName = newName[1:len(newName)-1]
            if downloader.renameFile(newName):
                self.download.filename = unicode(newName)

    def onStart(self, downloader, partialContent):
        self.start_time = time.time()
        self.start_elapsed = self.download.elapsed
        self.download.status = Status.RUNNING
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
                for i in range(0, len(self.rate_samples)-1):
                    rate_diff.append(self.rate_samples[i] - self.rate_samples[i+1])
                self.download_rate = float(sum(rate_diff)) / len(rate_diff)
            self.last_rate_sample = now

        self.download.downloadrate = self.download_rate

        self.download.downloaded = self.bytes_downloaded
        self.download.elapsed = self.start_elapsed + (now - self.start_time)
        if self.download.size and self.download_rate:
            self.download.timeleft = float(self.download.size - self.bytes_downloaded) / self.download_rate

    def onEnd(self, downloader):
        self.download.progress = 100
        self.download.status = Status.COMPLETED
        self.download_rate = (self.bytes_downloaded - self.bytes_start) / (time.time() - self.start_time)

class HTTPManagedDownloader(HTTPDownloader):

    def __init__(self, url, file, statusCallback=None, bucketFilter=None, *args, **kwargs):
        self.bytes_received = 0
        self.statusHandler = statusCallback
        self.bucketFilter = bucketFilter

        # TODO: Apparently this only works for servers, not clients :/
        #if self.bucketFilter:
        #   self.protocol = ShapedProtocolFactory(self.protocol, self.bucketFilter)

        HTTPDownloader.__init__(self, url, file, supportPartial=1,
                                agent='Downpour v%s' % VERSION,
                                *args, **kwargs)

        self.origPartial = self.requestedPartial

    def setRateLimit(self, rate=None):
        if self.bucketFilter:
            self.bucketFilter.rate = rate

    def renameFile(self, newName):
        fullName = os.path.sep.join((os.path.dirname(self.fileName),newName))
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
        HTTPDownloader.pageEnd(self)

    def startedConnecting(self, connector):
        self.connector = connector
        if (self.statusHandler):
            self.statusHandler.onConnect(self)
        HTTPDownloader.startedConnecting(self, connector)

    def clientConnectionFailed(self, connector, reason):
        if (self.statusHandler):
            self.statusHandler.onError(self)
        HTTPDownloader.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        if (self.statusHandler):
            self.statusHandler.onStop(self)
        HTTPDownloader.clientConnectionLost(self, connector, reason)

def downloadFile(url, file, statusCallback=None, bucketFilter=None, contextFactory=None, *args, **kwargs):
    factoryFactory = lambda url, *a, **kw: HTTPManagedDownloader(url, file, statusCallback=statusCallback, bucketFilter=bucketFilter, *a, **kw)
    return _makeGetterFactory(
        url,
        factoryFactory,
        contextFactory=contextFactory,
        *args, **kwargs).deferred
