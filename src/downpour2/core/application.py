import os, pwd, grp, logging, atexit, traceback
from twisted.internet import reactor, defer
from downpour2.core import config, plugin, event, store, users

class Application:

    def __init__(self, options=None):

        self.config = config.Config(options)
        self.store = store.get_store(self.config)
        self.event_bus = event.EventBus()
        self.user_manager = users.UserManager(self.store)
        
        # Logging configuration
        logging.basicConfig(
            level=getattr(logging, self.config.value(('downpour', 'log'),
                'info').upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.plugins = []

        # Load plugins
        for pn in self.config.value(('downpour', 'plugins'), '').split(','):
            try:
                p = self.get_class(pn)(self)
                if isinstance(p, plugins.Plugin):
                    self.plugins.append(p)
                    p.setup(self.config.section(pn));
            except Exception as e:
                print 'Plugin loading failed for %s: %s' % (pn, e)
                traceback.print_exc()

    def get_class(self, kls):
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)            
        return m

    def start(self):

        logging.info('Downpour started')

        self.state = list(self.store.find(store.models.State))
        self.settings = list(self.store.find(store.models.Setting))

        # Start plugins
        dfl = [ plugin.start() for plugin in self.plugins ]
        self.wait_for_deferred(dfl)

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
        dfl = [ plugin.stop() for plugin in self.plugins ]
        self.wait_for_deferred(dfl)

        # Stop reactor
        if reactor.running:
            reactor.stop()

        logging.info('Downpour stopped')

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
                logging.error('Could not set user or group: %s' % e)
        if 'umask' in self.config.values['downpour']:
            old_umask = os.umask(self.config.values['downpour']['umask'])

    def set_state(self, name, value):
        state = None
        for s in self.state:
            if s.name == name:
                state = s
                break
        if not state:
            state = store.models.State()
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
            setting = store.models.Setting()
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
