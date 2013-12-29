import os
import logging
import socket
import time
from twisted.internet import defer
from downpour2.core import VERSION, plugin, event, net
from downpour2.core.transfers import state, agent, store
from downpour2.core.net.throttling import ThrottledBucketFilter


class LocalAgent(plugin.Plugin, agent.TransferAgent):

    """
    Transfer agent that downloads to the local directory specified in the work_directory
    configuration value.
    """

    def __init__(self, app):

        super(LocalAgent, self).__init__(app)

        self.log = logging.getLogger(__name__)
        self.ready = False
        self.config = {}
        self.working_directory = None
        self.paused = False
        self.clients = []
        # TODO register supported transports (torrent, http, ftp, etc)
        self.transports = []

        self.agent_status = agent.AgentStatus()
        self.agent_status.version = VERSION
        self.agent_status.paused = False

        self.upload_rate_filter = None
        self.download_rate_filter = None

    def setup(self, config):

        self.config = config

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except OSError as oe:
                self.log.error('Could not create directory "%s": %s' % (work_dir, oe))

        self.working_directory = work_dir

        self.application.transfer_manager.register_agent(self)

        self.ready = True

    def start(self):

        if not self.ready:
            raise RuntimeError('Plugin configuration failed, not starting')

        # Listen for core pause/resume events
        self.application.events.subscribe(event.DOWNPOUR_PAUSED, self.pause)
        self.application.events.subscribe(event.DOWNPOUR_RESUMED, self.resume)

        transfers = list(self.application.store.find(
            store.Transfer, store.Transfer.removed == False).order_by(
            store.Transfer.added))

        return defer.DeferredList(
            [self.provision(t) for t in transfers],
            consumeErrors=True).addCallback(self.resume)

    def reload(self):
        # The only real config-dependent stuff is in auto-queue
        self.auto_queue()

    def stop(self):
        return self.pause()

    def pause(self):

        self.agent_status.paused = True
        self.log.info('Pausing all transfers')

        def requeue(results):
            for r in results:
                r[1].transfer.state = state.QUEUED

        return defer.DeferredList(
            [t.stop() for t in self.clients if t.transfer.state.transferring],
            consumeErrors=True).addCallback(requeue)

    def resume(self):
        self.agent_status.paused = False
        self.log.info('Resuming previous transfers')
        self.auto_queue()
        return defer.succeed(True)

    def accepts(self, transfer):
        for t in self.transports:
            if t.accepts(transfer):
                return t
        return None

    def client(self, transfer):

        for c in self.clients:
            if c.transfer == transfer:
                return c

        t = self.accepts(transfer)
        if t is not None:
            return t.client(transfer)

        raise NotImplementedError('No transports could handle this transfer')

    def provision(self, transfer):

        client = self.client(transfer)
        if client not in self.clients:
            self.clients.append(client)
            self.auto_queue()
        return client

    def reprovision(self, existing):

        # Check if metadata requires a different handler
        client = self.client(existing.transfer)

        if client != existing:

            running = existing.transfer.state.transferring

            existing.transfer.state == state.QUEUED
            existing.transfer.uploaded = 0
            existing.transfer.downloaded = 0
            existing.transfer.progress = 0

            try:
                idx = self.clients.index(self)
                self.clients[idx] = client
            except ValueError:
                self.clients.append(client)

            if running:
                client.start()

            return client

        return None

    @property
    def transfers(self):
        return self.clients

    def transfer(self, tid):
        for t in self.transfers:
            if t.id == tid:
                return t
        return None

    @property
    def status(self):

        now = time.time()

        if now - self.agent_status.local_updated >= 10:
            self.update_local_status(self.agent_status)

        if now - self.agent_status.transfers_updated >= 1:
            self.update_transfer_status(self.agent_status)

        return self.agent_status

    def update_transfer_status(self, status):

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

        status.active_downloads = active_downloads
        status.queued_downloads = queued_downloads
        status.active_uploads = active_uploads
        status.progress = progress
        status.downloadrate = download_rate
        status.uploadrate = upload_rate
        status.connections = connections

        status.transfers_updated = time.time()

    def update_local_status(self, status):

        s = os.statvfs(self.working_directory)
        diskfree = s.f_bfree * s.f_bsize
        diskfreepct = (float(s.f_bfree) / s.f_blocks) * 100

        try:
            interface = net.get_interface(self.application.config.value(
                ('downpour', 'interface'), '0.0.0.0'))
            if interface == '0.0.0.0':
                # Load IPs for local host
                ips = [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
                ips = filter(lambda ip: ip[:4] != '127.' and ip[:2] != '::', ips)
                interface = ', '.join(dict(map(lambda j: (j, 1), ips)).keys())
        except IOError:
            interface = 'disconnected'

        hostname = '%s (%s)' % (socket.gethostname(), interface)

        status.host = hostname
        status.diskfree = diskfree
        status.diskfreepct = diskfreepct

        status.local_updated = time.time()

    def auto_queue(self):
        """
        Start as many downloads as allowed by current configuration, in the order they were added
        """

        if not self.status.paused:

            logging.debug(u'Running auto-queue')

            active = self.status.active_downloads

            max_active = int(self.application.get_setting('agent.local.max_active', 0))
            max_ulrate = int(self.application.get_setting('agent.local.upload_rate', 0)) * 1024
            max_dlrate = int(self.application.get_setting('agent.local.download_rate', 0)) * 1024
            max_conn = int(self.application.get_setting('agent.local.connection_limit', 0))

            transfers = sorted(self.transfers, key=lambda x: -x.priority)

            # TODO: make this fairly distributed among users
            for t in filter(lambda x: x.status == state.QUEUED, transfers):
                if not max_active or active < max_active:
                    t.start()
                    active += 1

            self.application.store.commit()

            # Auto stop downloads if we're over config limits
            if max_active and active > max_active:
                transfers.reverse()
                for t in filter(lambda x: x.state == state.DOWNLOADING, transfers):
                    if active > max_active:
                        sdfr = t.stop()
                        sdfr.addCallback(self.update_state, t, state.QUEUED)
                        sdfr.addErrback(self.update_state, t, state.QUEUED)
                        active -= 1
                    else:
                        break

            if active > 0:

                client_dlrate = int(max_dlrate / active)
                client_ulrate = int(max_ulrate / active)
                client_conn = int(max_conn / active)

                # Reset transfer limits
                for t in transfers:

                    changed = False

                    if max_dlrate > 0 and t.state == state.DOWNLOADING and t.transfer.bandwidth != client_dlrate:
                        t.transfer.bandwidth = client_dlrate
                        changed = True
                    elif max_ulrate > 0 and t.state == state.SEEDING and t.transfer.bandwidth != client_ulrate:
                        t.transfer.bandwidth = client_ulrate
                        changed = True

                    if max_conn > 0 and t.transfer.connection_limit != client_conn:
                        t.transfer.connection_limit = client_conn
                        changed = True

                    if changed:
                        t.update()

    def upload_filter(self):
        max_ulrate = int(self.application.get_setting('agent.local.upload_rate', 0)) * 1024
        if not self.upload_rate_filter:
            self.upload_rate_filter = ThrottledBucketFilter(max_ulrate)
        else:
            self.upload_rate_filter.rate = max_ulrate
        return self.upload_rate_filter

    def download_filter(self):
        max_dlrate = int(self.application.get_setting('agent.local.download_rate', 0)) * 1024
        if not self.download_rate_filter:
            self.download_rate_filter = ThrottledBucketFilter(max_dlrate)
        else:
            self.download_rate_filter.rate = max_dlrate
        return self.download_rate_filter

    @staticmethod
    def update_state(transfer, new_state, message=None):
        transfer.transfer.state = new_state
        transfer.transfer.status = message
