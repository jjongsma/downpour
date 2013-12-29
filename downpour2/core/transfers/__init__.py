import os
import logging
import socket
import urllib
from time import time
from twisted.web import http
from storm.locals import *
from downpour2.core import VERSION, net, store, event
from downpour2.core.transfers import agent, state


class TransferManager(object):

    def __init__(self, app):

        self.log = logging.getLogger(__name__)
        self.application = app
        self.agents = []

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

        self.hostname = '%s (%s)' % (socket.gethostname(), interface)

        # Recently completed downloads
        self.recent = list(self.application.store.find(
            store.Transfer, store.Transfer.removed == True).order_by(
                Desc(store.Transfer.completed))[:30])

        # Update recent download list on transfer complete
        self.application.events.subscribe(event.COMPLETE, self.transfer_complete)

    def transfer_complete(self, transfer):
        self.recent.insert(0, transfer)
        self.recent = self.recent[:30]

    def add(self, transfer):

        transfer.added = time()
        transfer.removed = False
        transfer.progress = 0
        transfer.status = state.QUEUED
        transfer.downloaded = 0
        transfer.uploaded = 0

        if transfer.url:
            if not transfer.description:
                transfer.description = transfer.url
            if not transfer.filename:
                transfer.filename = unicode(urllib.unquote(
                    os.path.basename(http.urlparse(str(transfer.url))[2])
                ))

        self.application.store.add(transfer)
        self.application.store.commit()

        self.log.info(u'Added new download ' + transfer.description)
        self.application.events.fire(event.ADDED, transfer)

        def provision_failed(failure):
            self.log.debug('Could not provision download: %s' % failure.getErrorMessage())
            alert = store.Alert()
            alert.user_id = transfer.user_id
            alert.timestamp = time()
            alert.title = 'No agents were found to handle download'
            alert.description = 'The download %s was rejected by all registered agents.' % transfer.description
            alert.level = 'warn'
            alert.viewed = False
            self.application.alerts.add(alert)

        return self.provision(transfer).addErrback(provision_failed)

    def register_agent(self, agt):
        self.agents.append(agt)

    def accepts(self, transfer):
        for agt in self.agents:
            if agt.accepts(transfer):
                return agt
        return None

    def provision(self, transfer):
        for agt in self.agents:
            if agt.accepts(transfer):
                return agt.provision(transfer)
        raise NotImplementedError('No agents could handle this download')

    @property
    def status(self):

        statuses = [a.status() for a in self.agents]

        ssum = lambda sl, f: sum([getattr(s, f) for s in sl])
        savg = lambda sl, f: ssum(sl, f) / len(sl)

        status = agent.AgentStatus()
        status.host = self.hostname
        status.version = VERSION
        status.active_downloads = ssum(statuses, 'active_downloads')
        status.queued_downloads = ssum(statuses, 'queued_downloads')
        status.active_uploads = ssum(statuses, 'active_uploads')
        status.downloadrate = savg(statuses, 'downloadrate')
        status.uploadrate = savg(statuses, 'uploadrate')
        status.connections = ssum(statuses, 'connections')

        return status

    @property
    def transfers(self):
        return [t for a in self.agents for t in a.transfers]

    def transfer(self, tid):

        for a in self.agents:
            t = a.transfer(tid)
            if t is not None:
                return t

        return None
