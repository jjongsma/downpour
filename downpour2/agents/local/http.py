import time
import os
import logging
import shutil
from twisted.web import http
from twisted.web.client import _makeGetterFactory
from downpour2.core.net.http import HTTPManagedDownloader, DownloadStatus
from downpour2.core.net.throttling import ThrottledBucketFilter
from downpour2.core.transfers import state, client, event


class HTTPDownloadClientFactory(client.TransferClientFactory):

    def __init__(self, application, agent, work_dir):

        self.log = logging.getLogger(__name__)
        self.application = application
        self.agent = agent
        self.working_directory = work_dir

    def client(self, transfer):
        self.log.debug('Created HTTP client for %s' % transfer.url)
        return HTTPDownloadClient(transfer, self.application, self.agent, self.working_directory)

    def accepts(self, transfer):
        return transfer.url[:4] == 'http'


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

        self.log = logging.getLogger(__name__)

        super(HTTPDownloadClient, self).__init__(transfer, application)

        self.agent = agent
        self.original_mimetype = None
        self.factory = None
        self.rate = 0

        transfer_work_dir = os.path.sep.join((work_dir, str(self.transfer.id)))

        if not os.path.exists(transfer_work_dir):
            os.makedirs(transfer_work_dir)

        self.working_directory = transfer_work_dir

    def update(self):
        self.log.debug('settings updated')
        pass

    def shutdown(self):
        self.fire(event.STOP)

    def onstarting(self, e):

        self.log.debug('starting transfer for %s' % self.transfer.url)
        self.original_mimetype = self.transfer.mime_type
        self.transfer.state = state.STARTING
        self.transfer.status = None

        if not self.transfer.started:
            self.transfer.started = time.time()

        bucket_filter = ThrottledBucketFilter(0, self.agent.download_filter())

        factory_factory = lambda url, *a, **kw: HTTPManagedDownloader(
            str(self.transfer.url),
            os.path.join(self.working_directory, self.transfer.filename),
            status_callback=TransferStatus(self),
            bucket_filter=bucket_filter, *a, **kw)

        self.factory = _makeGetterFactory(str(self.transfer.url), factory_factory)
        self.factory.deferred.addCallbacks(
            lambda x: self.fire(event.COMPLETE),
            lambda x: self.fire(event.FAILED))

        return True

    def oncopying(self, e):
        self.log.debug('copying transfer %s' % self.transfer.url)
        # Local agent doesn't need to copy anywhere
        self.fire(event.FETCHED)

    def oncompleted(self, e):
        self.log.debug('completed transfer %s' % self.transfer.url)
        self.transfer.connections = 0
        self.transfer.downloadrate = 0
        self.transfer.progress = 100
        self.transfer.completed = time.time()
        self.transfer.status = None

    def onremoving(self, e):
        self.log.debug('removing transfer %s' % self.transfer.url)
        self.onstopping()

    def onremoved(self, e):
        self.log.debug('removed transfer %s' % self.transfer.url)
        # Cleanup working directory
        self.transfer.removed = True
        if os.path.isdir(self.working_directory):
            shutil.rmtree(self.working_directory)
        self.application.events.fire(event.REMOVED, self)

    def onstopping(self, e):
        self.log.debug('stopping transfer %s' % self.transfer.url)
        if self.factory.connector:
            self.factory.connector.disconnect()
        self.fire(event.STOPPED)

    def onfailed(self, e):
        self.log.debug('failed transfer %s' % self.transfer.url)
        self.transfer.connections = 0
        self.transfer.health = 'dead'

    def onbeforetransfer_complete(self, e):

        self.log.debug('before_complete transfer %s' % self.transfer.url)

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
                        # Successfully reinjected, block COMPLETE event
                        return False

            except NotImplementedError:
                pass

        return True

    @property
    def download_rate(self):
        return self.rate

    @download_rate.setter
    def download_rate(self, rate):
        self.rate = rate
        if hasattr(self, 'factory') and self.factory:
            self.factory.setRateLimit(rate)

    def directory(self):
        return self.working_directory

    def files(self):
        return ({'path': self.transfer.filename,
                 'size': self.transfer.size,
                 'progress': self.transfer.progress},)

    def fetch(self, directory=None):

        if directory is None:
            return self.working_directory

        if self.is_same_fs(directory, self.working_directory):

            pass

        return directory


class TransferStatus(DownloadStatus):

    def __init__(self, transfer_client):
        self.client = transfer_client
        self.bytes_start = 0
        self.bytes_downloaded = 0
        self.start_time = 0
        self.start_elapsed = 0
        self.download_rate = 0
        self.last_rate_sample = 0
        self.rate_samples = []

    def onconnect(self, downloader):
        self.client.fire(event.STARTED)

    def onerror(self, downloader):
        self.client.fire(event.FAILED)

    def onstop(self, downloader):
        if self.client.transfer.state != state.FAILED:
            if self.client.transfer.progress == 100:
                self.client.fire(event.COMPLETE)
            elif self.client.transfer.state == state.STOPPING:
                self.client.fire(event.STOPPED)
            else:
                self.client.fire(event.FAILED)
        self.client.transfer.download_rate = 0
        self.client.transfer.elapsed += (time.time() - self.start_time)

    def onheaders(self, downloader, headers):
        if downloader.requestedPartial:
            content_range = headers.get('content-range', None)
            start, end, content_length = http.parseContentRange(content_range[0])
            self.bytes_start = start - 1
            self.bytes_downloaded = self.bytes_start
        else:
            content_length = headers.get('content-length', [0])[0]
        self.client.transfer.size = float(content_length)
        content_type = headers.get('content-type', None)
        if content_type:
            self.client.transfer.mime_type = unicode(content_type[0])
        content_disposition = headers.get('content-disposition', None)
        if content_disposition and content_disposition[0].startswith('attachment'):
            new_name = content_disposition[0].split('=')[1]
            if new_name[0] == '"' and new_name[len(new_name) - 1] == '"':
                new_name = new_name[1:len(new_name) - 1]
            if downloader.rename_file(new_name):
                self.client.transfer.filename = unicode(new_name)

    def onstart(self, downloader, partial_content):
        self.start_time = time.time()
        self.start_elapsed = self.client.transfer.elapsed
        self.client.transfer.connections = 1
        self.client.transfer.health = 'excellent'

    def onpart(self, downloader, data):

        self.bytes_downloaded += len(data)

        if self.client.transfer.size:
            self.client.transfer.progress = \
                (float(self.bytes_downloaded) / float(self.client.transfer.size)) * 100

        now = int(time.time())
        if self.last_rate_sample == 0:
            self.last_rate_sample = now
            self.rate_samples.insert(0, self.bytes_downloaded)
        elif now > self.last_rate_sample:
            # Add value for every second since last sample
            for i in range(self.last_rate_sample, now):
                self.rate_samples.insert(0, self.bytes_downloaded)
            # Trim sample period to 10 seconds
            if len(self.rate_samples) > 10:
                self.rate_samples = self.rate_samples[:10]
            if len(self.rate_samples) > 1:
                rate_diff = [self.rate_samples[i] - self.rate_samples[i + 1]
                             for i in range(0, len(self.rate_samples) - 1)]
                self.download_rate = float(sum(rate_diff)) / len(rate_diff)
            self.last_rate_sample = now

        self.client.transfer.downloadrate = self.download_rate

        self.client.transfer.downloaded = self.bytes_downloaded
        self.client.transfer.elapsed = self.start_elapsed + (now - self.start_time)
        if self.client.transfer.size and self.download_rate:
            self.client.transfer.timeleft = \
                float(self.client.transfer.size - self.bytes_downloaded) / self.download_rate

    def onend(self, downloader):
        # self.download_rate = (self.bytes_downloaded - self.bytes_start) / (time.time() - self.start_time)
        self.download_rate = 0
        self.client.transfer.download_rate = 0
        self.client.fire(event.COMPLETE)
