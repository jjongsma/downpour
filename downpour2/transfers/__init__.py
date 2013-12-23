import os
import logging
from time import time
from twisted.internet import task, defer
from storm.locals import *
from downpour2.core import event, store
from downpour2.core.plugin import Plugin
from downpour2.transfers import store, manager, agent

class TransferManager(Plugin, agent.TransferAgent):

    def setup(self, config):

        self.LOG = logging.getLogger(__name__)

        self.config = config

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except OSError as oe:
                self.LOG.error('Could not create directory: %s' % work_dir)

        store.update_store(self.application.store)

        self.agents = []
        self.paused = False

    def start(self):

        work_dir = self.application.config.value(('downpour', 'work_directory'))
        if not os.path.exists(work_dir):
            raise IOError('Working directory not available, not starting plugin')

        self.application.events.subscribe(event.DOWNPOUR_PAUSED, self.pause)
        self.application.events.subscribe(event.DOWNPOUR_RESUMED, self.resume)

        self.LOG.info('Resuming previous transfers')

        # Recently completed downloads
        self.recent = list(self.application.store.find(store.Transfer,
            store.Transfer.removed == True).order_by(Desc(store.Transfer.completed))[:5])

        transfers = list(self.application.store.find(store.Transfer,
            store.Transfer.removed == False).order_by(store.Transfer.added))

        return defer.DeferredList([self.provision(t) for t in transfers],
            consumeErrors=True).addCallback(self.resume)

    def stop(self):
        return self.pause()

    def paused(self):
        return self.paused

    def add(self, transfer):

        transfer.added = time()
        transfer.removed = False
        transfer.progress = 0
        transfer.status = Status.QUEUED
        transfer.downloaded = 0
        transfer.uploaded = 0

        if transfer.url:
            if not transfer.description:
                transfer.description = transfer.url
            if not transfer.filename:
                transfer.filename = unicode(urllib.unquote(
                    os.path.basename(http.urlparse(str(url))[2])
                    ))

        self.application.store.add(transfer)
        self.store.commit()

        self.LOG.info(u'Added new download ' + transfer.description)
        self.application.events.fire(event.ADDED, transfer)

        def add_failed(failure):
            alert = Alert()
            alert.user_id = transfer.user_id
            alert.timestamp = time()
            alert.title = 'No agents were found to handle download'
            alert.description = 'The download %s was rejected by all registered agents.' % transfer.description
            alert.level = 'warn'
            alert.viewed = False
            self.application.alerts.add(alert)

        return self.provision(transfer).addErrback(add_failed)

    def register_agent(self, agent):
        self.agents.append(agent)

    """
    TransferAgent aggregate methods
    """

    def pause(self):
        self.paused = True
        return defer.DeferredList([a.pause() for a in self.agents], consumeErrors=True)

    def resume(self):
        self.paused = False
        return defer.DeferredList([a.resume() for a in self.agents], consumeErrors=True)

    def accepts(self, transfer):
        for agent in self.agents:
            if agent.accepts(transfer):
                return True
        return False

    def provision(self, transfer):
        for agent in self.agents:
            if agent.accepts(transfer):
                return agent.provision(transfer)
        raise NotImplementedError('No agents could provision this download')

    def status(self):

        if len(self.agents) == 1:
            return self.agents[0].status()

        dfr = defer.Deferred()

        defer.DeferredList([a.status() for a in self.agents], consumeErrors=True) \
            .addCallback(lambda rl: aggregate_status([r[1] for r in rl], dfr)) \
            .addErrback(dfr.errback)

        return dfr

    def transfers(self):

        if len(self.agents) == 1:
            return self.agents[0].active_transfers()

        dfr = defer.Deferred()
        
        defer.DeferredList([a.active_transfers() for a in self.agents], consumeErrors=True) \
            .addCallback(lambda results: dfr.callback(
                [t for res in results for tl in res[1] for t in tl])) \
            .addErrback(dfr.errback)

        return dfr

    def aggregate_status(statuses, dfr=None):

        ssum = lambda sl, f: sum([getattr(s, f) for s in sl])
        savg = lambda sl, f: ssum(sl, f) / len(sl)

        status = agent.AgentStatus()
        status.active_downloads = ssum(statuses, 'active_downloads')
        status.queued_downloads = ssum(statuses, 'queued_downloads')
        status.active_uploads = ssum(statuses, 'active_uploads')
        status.downloadrate = savg(statuses, 'downloadrate')
        status.uploadrate = savg(statuses, 'uploadrate')
        status.connections = ssum(statuses, 'connections')

        if dfr is not None:
            dfr.callback(status)

        return status
