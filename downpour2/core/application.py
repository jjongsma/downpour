import os, pwd, grp, logging, atexit, traceback
from twisted.internet import reactor, defer
from downpour2.core import config, plugin, event, store, users

class Application:

    default_plugins = [
        plugin.LIBRARY,
        plugin.TRANSFERS,
        plugin.FEEDS,
        plugin.SHARING,
        plugin.WEB ]

    def __init__(self, options=None):

        self.config = config.Config(options)

        # Logging configuration
        logging.basicConfig(
            level=getattr(logging, self.config.value(('downpour', 'log'),
                'info').upper(), logging.INFO),
            format='%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d - %(message)s')

        self.LOG = logging.getLogger(__name__);

        self.store = store.get_store(self.config)
        self.event_bus = event.EventBus()
        self.user_manager = users.UserManager(self.store)
        
        self.plugins = {}

        # Load plugins
        toload = [section for section in self.config.keys() if section.find('.') > -1]
        for pn in set(Application.default_plugins + toload):
            try:
                p = self.get_class(pn)(self)
                try:
                    if isinstance(p, plugin.Plugin):
                        self.plugins[pn] = p
                        p.setup(self.config.get(pn, {}))
                    else:
                        self.LOG.error('Not a Plugin subclass: %s' % pn)
                except Exception as e:
                    self.LOG.error('setup() failed for %s: %s' % (pn, e))
                    traceback.print_exc()
            except Exception as e:
                self.LOG.debug('Plugin not found: %s' % pn)

    def plugin(self, name):
        if name in self.plugins:
            return self.plugins[name]
        return None

    def get_class(self, kls):
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)            
        return m

    def start(self):

        self.LOG.info('Downpour started')

        self.state = list(self.store.find(store.State))
        self.settings = list(self.store.find(store.Setting))

        # Start plugins
        dfl = []
        for name in self.plugins:
            plugin = self.plugins[name]
            try:
                dfr = plugin.start()
                if dfr is not None:
                    dfl.append(dfr)
            except Exception as e:
                self.LOG.error('Plugin.start() failed for %s.%s: %s'
                    % (plugin.__module__, plugin.__class__.__name__, e))
                traceback.print_exc()
        self.wait_for_deferred(defer.DeferredList(dfl, consumeErrors=1))

        self.event_bus.fire(event.DOWNPOUR_STARTED)

        # Shutdown handler
        atexit.register(self.stop)

    def pause(self):
        self.set_state(u'paused', u'1');
        self.event_bus.fire(DOWNPOUR_PAUSED)

    def resume(self):
        self.set_state(u'paused', u'0');
        self.event_bus.fire(DOWNPOUR_RESUMED)

    def stop(self):

        self.event_bus.fire(event.DOWNPOUR_SHUTDOWN)

        # Stop plugins
        dfl = []
        for name in self.plugins:
            plugin = self.plugins[name]
            try:
                dfr = plugin.stop()
                if dfr is not None:
                    dfl.append(dfr)
            except Exception as e:
                self.LOG.error('Plugin.stop() failed for %s.%s: %s'
                    % (plugin.__module__, plugin.__class__.__name__, e))
                traceback.print_exc()
        self.wait_for_deferred(defer.DeferredList(dfl, consumeErrors=1))

        # Stop reactor
        if reactor.running:
            reactor.stop()

        self.LOG.info('Downpour stopped')

    @defer.inlineCallbacks
    def wait_for_deferred(self, dfr):
        result = yield dfr
        defer.returnValue(result)

    def drop_privileges(self, pidfile=None):
        if 'user' in self.config.values['downpour'] and os.getuid() == 0:
            try:
                user = self.config.values['downpour']['user']
                group = self.config.values['downpour']['group']
                if not pidfile is None:
                    os.chown(pidfile, pwd.getpwnam(user)[2], grp.getgrnam(group)[2])
                os.setgid(grp.getgrnam(group)[2])
                os.setuid(pwd.getpwnam(user)[2])
            except OSError as e:
                self.LOG.error('Could not set user or group: %s' % e)
        if 'umask' in self.config.values['downpour']:
            old_umask = os.umask(self.config.values['downpour']['umask'])

    def set_state(self, name, value):
        state = None
        for s in self.state:
            if s.name == name:
                state = s
                break
        if not state:
            state = store.State()
            state.name = name
            self.state.append(state)
            self.store.add(state)
        state.value = unicode(value)
        self.store.commit()

    def get_state(self, name, default=None):
        for s in self.state:
            if s.name == name:
                return s.value
        return default

    def set_setting(self, name, value):
        setting = None
        for s in self.settings:
            if s.name == name:
                setting = s
                break
        if not setting:
            setting = store.Setting()
            setting.name = name
            self.settings.append(setting)
            self.store.add(setting)
        setting.value = unicode(value)
        self.store.commit()

    def get_setting(self, name, default=None):
        for s in self.settings:
            if s.name == name:
                return s.value
        return default

    def is_paused(self):
        return self.get_state(u'paused', u'0') == u'1'

    def run(self, pidfile=None):

        # Drop privileges after plugin setup in case of privileged port usage
        self.drop_privileges(pidfile)

        # Start server
        reactor.callWhenRunning(self.start)
        reactor.run()
