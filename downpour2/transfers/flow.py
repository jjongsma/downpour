import logging
from twisted.internet import defer
import state, event

WILDCARD = '*'

class FlowError(Exception):
    pass

class Flow(object):

    def __init__(self, cfg):
        self.LOG = logging.getLogger(__name__)
        self._apply(cfg)
        self._transition = False

    def isstate(self, state):
        return self.current == state

    def can(self, event):
        return (event in self._map and ((self.current in self._map[event]) or WILDCARD in self._map[event])
            and not self._transition

    def cannot(self, event):
        return not self.can(event)

    def is_finished(self):
        return self._final and (self.current == self._final)

    def _apply(self, cfg):
        init = cfg['initial'] if 'initial' in cfg else None
        if self._is_base_string(init):
            init = {'state': init}

        self._final = cfg['final'] if 'final' in cfg else None

        events = cfg['events'] if 'events' in cfg else []
        callbacks = cfg['callbacks'] if 'callbacks' in cfg else {}
        tmap = {}
        self._map = tmap

        def add(e):
            if 'src' in e:
                src = [e['src']] if self._is_base_string(e['src']) else e['src']
            else:
                src = [WILDCARD]
            if e['name'] not in tmap:
                tmap[e['name']] = {}
            for s in src:
                tmap[e['name']][s] = e['dst']

        if init:
            if 'event' not in init:
                init['event'] = 'startup'
            add({'name': init['event'], 'src': 'none', 'dst': init['state']})

        for e in events:
            add(e)

        for name in tmap:
            setattr(self, name, self._build_event(name))

        for name in callbacks:
            setattr(self, name, callbacks[name])

        self.current = 'none'

        if init and 'defer' not in init:
            getattr(self, init['event'])()

    def _build_event(self, event):

        def fn(*args, **kwargs):

            if self._transition:
                raise FlowError(
                    "event %s inappropriate because previous transition did not complete" % event)
            if not self.can(event):
                raise FlowError(
                    "event %s inappropriate in current state %s" % (event, self.current))

            src = self.current
            dst = ((src in self._map[event] and self._map[event][src]) or
                WILDCARD in self._map[event] and self._map[event][WILDCARD])

            class _e_obj(object):
                pass
            e = _e_obj()
            e.fsm, e.event, e.src, e.dst = self, event, src, dst
            for k in kwargs:
                setattr(e, k, kwargs[k])

            setattr(e, 'args', args)

            if self._before_event(e) is False:
                return defer.fail(FlowError('before event handler returned false'))

            dfr = defer.Deferred()

            def _after():
                self._transition = False
                self._change_state(e)
                self._after_event(e)
                dfr.callback()
                return dfr

            if self.current == dst:
                return _after()

            def _enter():
                self.current = dst
                defer.maybeDeferred(self._enter_state, e)
                    .addCallback(_after).addErrback(dfr.errback)

            def _leave():
                self._transition = True
                defer.maybeDeferred(self._leave_state, e)
                    .addCallback(_enter).addErrback(dfr.errback)

            _leave()

            return dfr

        return fn

    def _before_event(self, e):
        fnname = 'onbefore' + e.event
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _after_event(self, e):
        for fnname in ['onafter' + e.event, 'on' + e.event]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _leave_state(self, e):
        fnname = 'onleave' + e.src
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _enter_state(self, e):
        for fnname in ['onenter' + e.dst, 'on' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _change_state(self, e):
        fnname = 'onchangestate'
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _is_base_string(self, object):
        try:
            return isinstance(object, basestring)
        except NameError:
            return isinstance(object, str)

class TransferFlow(Flow):

    def __init__(self, transfer, application, rules):

        super(TransferFlow, self).__init__(rules)

        self.transfer = transfer
        self.application = application

    def fire(self, event):
        if hasattr(self, event):
            return getattr(self, event)()
        raise ValueError('Unknown event: %s' % event)

    def onchangestate(self, transition):
        self.transfer.state = transition.dst
        self.application.events.fire(transition.event, self)

    def state(self):
        return state.describe(self.current)

    """
    Transfer flow management methods come from state machine
    events (start(), stop(), remove(), etc). Agent implementations
    should respond to these events by adding state-change handlers
    to their TransferFlow subclasses (onstart(), onstop(), etc).
    """

    """
    Notifies the transfer that its the settings have been updated on the
    underlying transfer object (bandwidth throttling, etc) and the agent
    should update its settings.
    """
    def update(self):
        pass

    """
    Copy the transfer files the specified directory
    """
    def fetch(self, directory):
        raise NotImplementedError('Must be defined by agent')

    """
    Shutdown the transfer process and unregister from the owning agent.
    After calling shutdown, this object is dead and a new transfer flow
    must be created with TransferManager.provision_transfer()
    """
    def shutdown(self):
        raise NotImplementedError('Must be defined by agent')

class SimpleDownloadFlow(TransferFlow):

    def __init__(self, transfer, application):

        super(DownloadFlow, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start download
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.DOWNLOADING},
                # Progress updated
                {'src': state.DOWNLOADING, 'name': event.UPDATED, 'dst': state.DOWNLOADING},
                # Download paused
                {'src': state.DOWNLOADING, 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Download resumed
                {'src': state.STOPPED, 'name': event.ENQUEUE, 'dst': state.QUEUED},
                {'src': [ state.STOPPED, state.FAILED ], 'name': event.START, 'dst': state.INITIALIZING},
                # Download completed/failed
                {'src': state.DOWNLOADING, 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.DOWNLOADING, 'name': event.COMPLETE, 'dst': state.COPYING},
                # Fetch files from agent
                {'src': state.COPYING, 'name': event.FETCH_FAILED, 'dst': state.PENDING_COPY},
                {'src': state.COPYING, 'name': event.STOP, 'dst': state.PENDING_COPY},
                {'src': state.PENDING_COPY, 'name': event.START, 'dst': state.COPYING},
                # Completed
                {'src': state.COPYING, 'name': event.FETCHED, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': state.DOWNLOADING, 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [ state.QUEUED, state.FAILED, state.COMPLETED,
                    state.PENDING_COPY], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })

class PeerDownloadFlow(TransferFlow):

    def __init__(self, transfer, application):

        super(DownloadFlow, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start download
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.DOWNLOADING},
                # Progress updated
                {'src': state.DOWNLOADING, 'name': event.UPDATED, 'dst': state.DOWNLOADING},
                # Download paused
                {'src': state.DOWNLOADING, 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Download resumed
                {'src': state.STOPPED, 'name': event.ENQUEUE, 'dst': state.QUEUED},
                {'src': [ state.STOPPED, state.FAILED ], 'name': event.START, 'dst': state.INITIALIZING},
                # Download completed/failed
                {'src': state.DOWNLOADING, 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.DOWNLOADING, 'name': event.COMPLETE, 'dst': state.COPYING},
                # Fetch files from agent
                {'src': state.COPYING, 'name': event.FETCH_FAILED, 'dst': state.PENDING_COPY},
                {'src': state.COPYING, 'name': event.STOP, 'dst': state.PENDING_COPY},
                {'src': state.PENDING_COPY, 'name': event.START, 'dst': state.COPYING},
                {'src': state.COPYING, 'name': event.FETCHED, 'dst': state.SEEDING},
                # Completed
                {'src': state.SEEDING, 'name': event.COMPLETE, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': [ state.DOWNLOADING, state.SEEDING ], 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [ state.QUEUED, state.FAILED, state.COMPLETED,
                    state.PENDING_COPY], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })

class SimpleUploadFlow(TransferFlow):

    def __init__(self, transfer, application):

        super(UploadFlow, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start upload
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.SEEDING},
                # Progress updated
                {'src': state.SEEDING, 'name': event.UPDATED, 'dst': state.SEEDING},
                # Upload paused
                {'src': state.SEEDING, 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Upload completed/failed
                {'src': state.SEEDING, 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.SEEDING, 'name': event.COMPLETE, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': state.SEEDING, 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [ state.FAILED, state.COMPLETED ], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })
