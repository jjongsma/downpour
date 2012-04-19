from twisted.internet import defer
from twisted.protocols.htb import Bucket, HierarchicalBucketFilter
import tempfile, os, logging, shutil

class Status:
    NONE = 0
    QUEUED = 1
    LOADING = 2
    STARTING = 3
    RUNNING = 4
    STOPPING = 5
    STOPPED = 6
    COMPLETED = 7
    FAILED = 8
    SEEDING = 9
    
    descriptions = ['None', 'Queued', 'Loading', 'Starting', 'Running',
            'Stopping', 'Stopped', 'Completed', 'Failed', 'Seeding']

class Capabilities:
    NONE = 0
    MULTICONN = 1
    UPLOAD = 2

class DownloadClientFactory:

    MIMETYPES = ['*']

    def __init__(self, manager):
        self.manager = manager
        self.clients = {}

    def get_client(self, download):
        if download.id in self.clients:
            return self.clients[download.id]

        dc = DownloadClient(download, self.manager,
            self.manager.get_work_directory(download))
        self.clients[download.id] = dc

        return dc

class DownloadClient:

    capabilities = Capabilities.NONE

    def __init__(self, download, manager, directory=tempfile.gettempdir()):
        self.download = download
        self.manager = manager
        self.directory = directory

        self.deferred = defer.Deferred()
        self.download_rate = 0
        self.upload_rate = 0
        self.max_connections = 0

        if not os.path.exists(directory):
            os.makedirs(directory)
        if not os.access(directory, os.R_OK):
            raise OSError('Could not write to download directory %s' % directory)

    def callback(self, new_mimetype=False):
        self.deferred.callback(new_mimetype)

    def errback(self, failure):
        self.deferred.errback(failure)

    def addCallback(self, cb, *args, **kwargs):
        self.deferred.addCallback(cb, *args, **kwargs)

    def addErrback(self, cb, *args, **kwargs):
        self.deferred.addErrback(cb, *args, **kwargs)

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def resume(self):
        return self.start()

    def pause(self):
        return self.stop()

    def remove(self):
        pass

    def set_download_rate(self, rate):
        self.download_rate = rate

    def set_upload_rate(self, rate):
        self.upload_rate = rate

    def set_max_connections(self, connections):
        self.max_connections = connections

    def get_files(self):
        return ({'path': self.download.filename,
                 'size': self.download.size,
                 'progress': self.download.progress},)

    def can_upload(self):
        return (self.capabilities & Capabilities.UPLOAD)

    def is_running(self):
        return self.download.status == Status.RUNNING or \
            self.download.status == Status.SEEDING

    def is_finished(self):
        return self.download.progress == 100

    def is_startable(self):
        return not self.is_running() and \
            (self.download.status == Status.QUEUED or \
                self.download.status == Status.STOPPED or \
                self.download.status == Status.FAILED or \
                (self.download.status == Status.COMPLETED and \
                    (self.capabilities & Capabilities.UPLOAD)))

    def is_stoppable(self):
        return self.is_running() or \
            self.download.status == Status.LOADING or \
            self.download.status == Status.STARTING or \
            self.download.status == Status.STOPPING
