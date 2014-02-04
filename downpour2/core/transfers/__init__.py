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

        self.hostname = socket.gethostname()
        self.interface = app.config.value(('downpour', 'interface'), '0.0.0.0')
        self.address = net.get_interface_ip(self.interface)

        if self.address == self.interface:
            self.interface = None

        if self.address is None:
            self.address = 'disconnected'

        # Recently completed downloads
        self.recent = list(self.application.store.find(
            store.Transfer, store.Transfer.removed == True).order_by(
                Desc(store.Transfer.completed))[:30])

        # Update recent download list on transfer complete
        self.application.events.subscribe(event.REMOVED, self.transfer_complete)

    def transfer_complete(self, transfer):
        self.recent.insert(0, transfer)
        self.recent = self.recent[:30]

    def add(self, transfer):

        transfer.added = time()
        transfer.removed = False
        transfer.priority = 0
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

        try:
            return self.provision(transfer)
        except Exception as e:
            self.log.debug('Could not provision download: %s' % e)
            alert = store.Alert()
            alert.user_id = transfer.user_id
            alert.timestamp = time()
            alert.title = u'Transfer protocol unknown or not supported'
            alert.description = u'The download %s was rejected by all registered agents.' % transfer.description
            alert.level = u'warn'
            alert.viewed = False
            self.application.alerts.add(alert)

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

    def user(self, user_id):
        return UserTransferManager(user_id, self)

    @property
    def status(self):

        statuses = [a.status for a in self.agents]

        ssum = lambda sl, f: sum([getattr(s, f) for s in sl])
        savg = lambda sl, f: ssum(sl, f) / len(sl)

        status = agent.AgentStatus()
        status.host = self.hostname
        status.interface = self.interface
        status.address = self.address
        status.version = VERSION
        status.active_downloads = ssum(statuses, 'active_downloads')
        status.queued_downloads = ssum(statuses, 'queued_downloads')
        status.active_uploads = ssum(statuses, 'active_uploads')
        status.downloadrate = savg(statuses, 'downloadrate') if len(statuses) else 0
        status.uploadrate = savg(statuses, 'uploadrate') if len(statuses) else 0
        status.connections = ssum(statuses, 'connections')

        return status

    @property
    def transfers(self):
        return [t for a in self.agents for t in a.clients]

    def transfer(self, tid):

        for a in self.agents:
            t = a.client(tid)
            if t is not None:
                return t

        return None


class UserTransferManager(object):

    def __init__(self, user_id, manager):
        self.user_id = user_id
        self.manager = manager

    @property
    def status(self):

        statuses = [a.agent(self.user_id).status for a in self.manager.agents if a.agent(self.user_id) is not None]

        ssum = lambda sl, f: sum([getattr(s, f) for s in sl])
        savg = lambda sl, f: ssum(sl, f) / len(sl)

        status = agent.AgentStatus()
        status.host = self.manager.hostname
        status.interface = self.manager.interface
        status.address = self.manager.address
        status.version = VERSION
        status.active_downloads = ssum(statuses, 'active_downloads')
        status.queued_downloads = ssum(statuses, 'queued_downloads')
        status.active_uploads = ssum(statuses, 'active_uploads')
        status.downloadrate = savg(statuses, 'downloadrate') if len(statuses) else 0
        status.uploadrate = savg(statuses, 'uploadrate') if len(statuses) else 0
        status.connections = ssum(statuses, 'connections')

        return status

    @property
    def clients(self):
        return [c for a in self.manager.agents if a.agent(self.user_id) is not None
                for c in a.agent(self.user_id).clients]

    def client(self, tid):

        for c in self.clients:
            if c.transfer.id == tid:
                return c

        return None
