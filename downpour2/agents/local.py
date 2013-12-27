import os
import logging
import socket
from twisted.internet import task, defer
from downpour2.transfers import agent, state
from downpour2.core import VERSION, plugin, event
from downpour2.core.net import get_interface


class LocalAgent(plugin.Plugin, agent.TransferAgent):

    # TODO register supported transports (torrent, http, ftp, etc)
    transports = [
    ]

    def __init__(self, app):

        super(LocalAgent, self).__init__(app)

        self.log = logging.getLogger(__name__)
        self.config = {}
        self.working_directory = None
        self.paused = False
        self.clients = []

    def setup(self, config):

        self.config = config

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except OSError as oe:
                self.log.error('Could not create directory "%s": %s' % (work_dir, oe))

        self.application.plugins[plugin.TRANSFERS].register_agent(self)

    def start(self):

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            raise IOError('Working directory not available, not starting plugin')

        self.application.events.subscribe(event.DOWNPOUR_PAUSED, self.pause)
        self.application.events.subscribe(event.DOWNPOUR_RESUMED, self.resume)

        task.LoopingCall(self.auto_queue).start(5, True)

        self.log.info('Resuming previous transfers')

        self.resume()

    def stop(self):
        return self.pause()

    def resume(self):
        self.paused = False
        return defer.DeferredList([t.start() for t in self.clients], consumeErrors=True)

    def accepts(self, transfer):
        for t in self.transports:
            if t.accepts(transfer):
                return True
        return False

    def provision(self, transfer):
        for t in self.transports:
            if t.accepts(transfer):
                client = t.client(transfer)
                self.clients.append(client)
                return defer.succeed(client)
        return defer.fail(NotImplementedError('No transports could handle this transfer'))

    @property
    def transfers(self):
        return self.clients

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

        for client in self.transfers:

            if client.transfer.size:
                queuedsize += client.transfer.size
                queueddone += client.transfer.downloaded

            if client.transfer.state == state.DOWNLOADING:
                active_downloads += 1
            elif client.transfer.state == state.SEEDING:
                active_uploads += 1
            elif client.transfer.state == state.QUEUED:
                queued_downloads += 1

            download_rate += client.transfer.downloadrate
            upload_rate += client.transfer.uploadrate
            connections += client.transfer.connections

        if queuedsize:
            progress = round((float(queueddone) / queuedsize) * 100, 2)
        else:
            progress = 0

        try:
            interface = get_interface(self.application.config.value(
                ('downpour', 'interface'), '0.0.0.0'))
            if interface == '0.0.0.0':
                # Load IPs for local host
                ips = [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
                ips = filter(lambda ip: ip[:4] != '127.' and ip[:2] != '::', ips)
                interface = ', '.join(dict(map(lambda j: (j, 1), ips)).keys())
        except IOError:
            interface = 'disconnected'

        hostname = '%s (%s)' % (socket.gethostname(), interface)

        status = agent.Status()
        status.host = hostname
        status.version = VERSION
        status.active_downloads = active_downloads
        status.queued_downloads = queued_downloads
        status.active_uploads = active_uploads
        status.progress = progress
        status.downloadrate = download_rate
        status.uploadrate = upload_rate
        status.diskfree = diskfree
        status.diskfreepct = diskfreepct
        status.connections = connections
        status.paused = self.paused

        return status

    # Start as many downloads as allowed by current configuration,
    # in the order they were added
    def auto_queue(self):

        if not self.application.is_paused():

            logging.debug(u'Running auto-queue')
            status = self.status()

            active = status['active_downloads']
            ulrate = status['uploadrate']
            dlrate = status['downloadrate']
            conn = status['connections']

            max_active = int(self.get_setting('max_active', 0))
            max_ulrate = int(self.get_setting('upload_rate', 0)) * 1024
            max_dlrate = int(self.get_setting('download_rate', 0)) * 1024
            max_conn = int(self.get_setting('connection_limit', 0))

            # TODO make this fairly distributed among users
            for d in filter(lambda x: x.status == state.QUEUED and not x.active, downloads):
                if not max_active or active < max_active:
                    self.start_download(d.id)
                    active = active + 1

            self.store.commit()

            # Auto stop downloads if we're over config limits
            if max_active and active > max_active:
                downloads.reverse()
                for d in filter(lambda x: x.active, downloads):
                    if active > max_active:
                        sdfr = self.stop_download(d.id)
                        sdfr.addCallback(self.update_status, d, state.QUEUED)
                        sdfr.addErrback(self.update_status, d, state.QUEUED)
                        active -= 1
                    else:
                        break

            if active > 0:
                # Reset transfer limits
                if max_ulrate > 0:
                    client_ulrate = int(max_ulrate / active)
                    for d in filter(lambda x: x.active, downloads):
                        dc = self.get_download_client(d.id)
                        if (dc):
                            dc.set_upload_rate(client_ulrate)
                if max_dlrate > 0:
                    client_dlrate = int(max_dlrate / active)
                    for d in filter(lambda x: x.active, downloads):
                        dc = self.get_download_client(d.id)
                        if (dc):
                            dc.set_download_rate(client_dlrate)
                if max_conn > 0:
                    client_conn = int(max_conn / active)
                    for d in filter(lambda x: x.active, downloads):
                        dc = self.get_download_client(d.id)
                        if (dc):
                            dc.set_max_connections(client_conn)
