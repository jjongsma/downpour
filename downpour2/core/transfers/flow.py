from twisted.internet import defer

#
# Pulled from Fysom with some renovations for Deferred async state transitions with Twisted
#

WILDCARD = '*'


class FlowError(Exception):
    pass


class Flow(object):

    def __init__(self, cfg):

        self._apply(cfg)
        self._final = None
        self._map = {}

        self.current = None

    def can(self, event):
        return event in self._map and ((self.current in self._map[event]) or WILDCARD in self._map[event])

    def cannot(self, event):
        return not self.can(event)

    def is_finished(self):
        return self._final and (self.current == self._final)

    def _apply(self, cfg):

        init = cfg['initial'] if 'initial' in cfg else None
        if _is_base_string(init):
            init = {'state': init}

        self._final = cfg['final'] if 'final' in cfg else None

        events = cfg['events'] if 'events' in cfg else []
        callbacks = cfg['callbacks'] if 'callbacks' in cfg else {}
        tmap = {}
        self._map = tmap

        def add(evt):
            if 'src' in evt:
                src = [evt['src']] if _is_base_string(evt['src']) else evt['src']
            else:
                src = [WILDCARD]
            if evt['name'] not in tmap:
                tmap[evt['name']] = {}
            for s in src:
                tmap[evt['name']][s] = evt['dst']

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

            if not self.can(event):
                raise FlowError(
                    "event %s inappropriate in current state %s" % (event, self.current))

            src = self.current
            dst = ((src in self._map[event] and self._map[event][src]) or
                   WILDCARD in self._map[event] and self._map[event][WILDCARD])

            class Evt(object):
                pass

            e = Evt()
            e.fsm, e.event, e.src, e.dst = self, event, src, dst
            for k in kwargs:
                setattr(e, k, kwargs[k])

            setattr(e, 'args', args)

            dfr = defer.Deferred()

            current = self.current

            def _revert(f):
                self.current = current
                dfr.errback(f)

            def _after():
                defer.maybeDeferred(self._after_event, e).addCallbacks(
                    lambda x: dfr.callback(True), dfr.errback)

            def _enter():
                defer.maybeDeferred(self._enter_state, e).addCallbacks(_after, dfr.errback)

            def _change():
                self.current = dst
                defer.maybeDeferred(self._change_state, e).addCallbacks(_enter, dfr.errback)

            def _leave(allowed=True):
                if not allowed:
                    dfr.errback(FlowError('before event handler returned false'))
                else:
                    if self.current == dst:
                        _after()
                    else:
                        defer.maybeDeferred(self._leave_state, e).addCallbacks(_change, _revert)

            def _before():
                defer.maybeDeferred(self._before_event, e).addCallbacks(_leave, dfr.errback)

            _before()

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


def _is_base_string(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)
