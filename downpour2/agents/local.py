import os
import logging
from twisted.internet import task, defer
from storm.locals import *
from downpour2.transfers import agent
from downpour2.core import VERSION, plugin, event
from downpour2.core.net import get_interface

class LocalAgent(plugin.Plugin, agent.TransferAgent):

    transports = [
        # TODO
    ]
    
    def setup(self, config):

        self.LOG = logging.getLogger(__name__)

        self.config = config

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except OSError as oe:
                self.LOG.error('Could not create directory: %s' % work_dir)

        self.working_directory = work_dir
        self.paused = False
        self.transfers = []

        self.application.plugins[plugin.TRANSFERS].register_agent(self)

    def start(self):

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            raise IOError('Working directory not available, not starting plugin')

        self.application.events.subscribe(event.DOWNPOUR_PAUSED, self.pause)
        self.application.events.subscribe(event.DOWNPOUR_RESUMED, self.resume)

        self.LOG.info('Resuming previous transfers')

        self.resume()

    def stop(self):
        return self.pause()

    def pause(self):
        self.paused = True
        return defer.DeferredList([t.stop() for t in self.transfers], consumeErrors=True)

    def resume(self):
        self.paused = False
        return defer.DeferredList([t.start() for t in self.transfers], consumeErrors=True)

    def accepts(self, transfer):
        for t in self.transports:
            if t.accepts(transfer):
                return True;
        return False

    def provision(self, transfer):
        for t in self.transports:
            if t.accepts(transfer):
                client = t.client(transfer)
                self.transfers.append(client)
                return defer.succeed(client)
        return defer.fail(NotImplementedError('No transports could handle this transfer'))

    def transfers(self):
        return self.transfers

    def status(self):

        s = os.statvfs(self.working_directory)
        diskfree = s.f_bfree * s.f_bsize
        diskfreepct = (float(s.f_bfree) / s.f_blocks) * 100

        queuedsize = 0
        queueddone = 0
        active_downloads = 0
        queued_downloads = 0
        active_uploads = 0
        download_rate = 0
        upload_rate = 0
        connections = 0

        for c in self.transfers:
            if c.transfer.size:
                queuedsize += c.transfer.size
                queueddone += c.transfer.downloaded
            if c.transfer.state == state.DOWNLOADING:
                active_downloads += 1
            elif c.transfer.state == state.SEEDING:
                active_uploads += 1
            elif c.transfer.state == Status.QUEUED:
                queued_downloads += 1
            download_rate += c.transfer.downloadrate
            upload_rate += c.transfer.uploadrate
            connections += c.transfer.connections

        if queuedsize:
            progress = round((float(queueddone) / queuedsize) * 100, 2)
        else:
            progress = 0

        interface = None
        try:
            interface = get_interface(self.get_option(
                ('downpour', 'interface'), '0.0.0.0'))
            if interface == '0.0.0.0':
                # Load IPs for local host
                ips = [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
                ips = filter(lambda ip: ip[:4] != '127.' and ip[:2] != '::', ips)
                interface = ', '.join(dict(map(lambda i: (i,1), ips)).keys())
        except IOError as ioe:
            interface = 'disconnected'

        hostname = '%s (%s)' % (socket.gethostname(), interface)

        status = agent.Status()
        status.host = hostname,
        status.version = VERSION,
        status.active_downloads = active_downloads,
        status.queued_downloads = queued_downloads,
        status.active_uploads = active_uploads,
        status.progress = progress,
        status.downloadrate = download_rate,
        status.uploadrate = upload_rate,
        status.diskfree = diskfree,
        status.diskfreepct = diskfreepct,
        status.connections = connections,
        status.paused = self.paused

        return status
    
