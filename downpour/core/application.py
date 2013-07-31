from twisted.internet import reactor, defer, protocol, task
from downpour.feed import checker
from downpour.core import db, plugins, manager, models
import sys, os, pwd, grp, logging, ConfigParser, atexit, traceback
from storm.locals import Store, create_database

class Application:

    options = {
        'config': ['/etc/downpour.cfg',
            os.path.expanduser('~/.config/downpour/downpour.cfg')],
        'downpour': {
            'state': os.path.expanduser('~/.config/downpour/downpour.db'),
            'log': 'info',
            'interface': '0.0.0.0',
            'plugins': 'downpour.web.WebInterfacePlugin'
        },
        'downpour.web.WebInterfacePlugin': {
            'port': 6280
        }
    }

    def __init__(self, options=None):

        self.store = None
        self.manager = None
        self.plugins = []

        # Not a comprehensive list, just adding as I need them
        self.listeners = {
            'downpour_started': [],
            'downpour_shutdown': [],
            'downpour_paused': [],
            'downpour_resumed': [],
            'download_added': [],
            'download_started': [],
            'download_stopped': [],
            'download_failed': [],
            'download_complete': [],
            'download_imported': [],
            'download_import_failed': [],
            'download_removed': [],
            'feed_added': [],
            'feed_updated': [],
            'feed_removed': [],
            'feed_item_added': [],
            'feed_item_removed': [],
            'library_file_added': [],
            'library_file_removed': []
        }

        # Load configuration from file
        config = Application.options['config']
        if options and options.has_key('config'):
            config.append(os.path.expanduser(options['config']))
        self.options['config'] = config
        cfgparser = ConfigParser.RawConfigParser()
        cfgparser.read(config)
        for section in cfgparser.sections():
            if not self.options.has_key(section):
                self.options[section] = {}
            for pair in cfgparser.items(section):
                self.options[section][pair[0]] = pair[1]

        # Override a limited set of options from command line
        if options:
            sections = {
                'log': self.options['downpour'],
                'interface': self.options['downpour'],
                'port': self.options['downpour.web.WebInterfacePlugin']
            }
            for key in options:
                if options[key] is not None and sections.has_key(key):
                    sections[key][key] = options[key]

        loglevels = {'debug': logging.DEBUG,
                    'info': logging.INFO,
                    'warn': logging.WARN,
                    'error': logging.ERROR,
                    'fatal': logging.FATAL}
        logging.basicConfig(
            level=loglevels[self.get_option(('downpour', 'log'), 'info')],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        if 'download' in options and 'work_directory' in options['download']:
            if not os.path.exists(options['download']['work_directory']):
                try:
                    os.makedirs(options['download']['work_directory'])
                except OSError as oe:
                    logging.error('Could not create working directory, downloading is impossible')
                    reactor.stop()

        # Load plugins
        if 'plugins' in self.options['downpour']:
            pl = self.options['downpour']['plugins'].split(',')
            for pn in pl:
                try:
                    p = self.get_class(pn)(self)
                    if isinstance(p, plugins.Plugin):
                        self.plugins.append(p)
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

        self.state = list(self.get_store().find(models.State))
        self.settings = list(self.get_store().find(models.Setting))
        self.manager = manager.GlobalManager(self)

        # Initialize plugins
        for plugin in self.plugins:
            pn = '%s.%s' % (plugin.__class__.__module__, plugin.__class__.__name__)
            if pn in self.options:
                plugin.setup(self.options[pn]);
            else:
                plugin.setup({});

        # Resume downloads from previous session
        logging.info('Resuming previous downloads')
        dl = [self.manager.start_download(d.id, True) \
            for d in self.manager.get_downloads() if d.active]
        self.wait_for_deferred(dl)

        # Start download queue checker
        self.queue_checker = task.LoopingCall(self.auto_queue).start(30, True)

        # Start RSS feed checker
        self.feed_checker = task.LoopingCall(checker.check_feeds, self.manager).start(60, True)
        self.add_event_listener('download_imported', checker.clean_download_feed, self)

        # Start plugins
        for plugin in self.plugins:
            plugin.start()

        self.fire_event('downpour_started')

        # Shutdown handler
        atexit.register(self.stop)

    def auto_queue(self):
        return self.manager.auto_queue()
    
    def pause(self):
        self.set_state(u'paused', u'1');
        return self.manager.pause();

    def resume(self):
        self.set_state(u'paused', u'0');
        return self.manager.resume();

    def stop(self):
        # Wait for all pause tasks to stop
        dfl = self.manager.pause()
        self.wait_for_deferred(dfl)

        self.fire_event('downpour_shutdown')

        # Stop plugins
        for plugin in self.plugins:
            plugin.stop()

        # Stop reactor
        if reactor.running:
            reactor.stop()

        logging.info('Downpour stopped')

    @defer.inlineCallbacks
    def wait_for_deferred(self, dfr):
        result = yield dfr
        defer.returnValue(result)

    def drop_privileges(self, pidfile=None):
        if 'user' in self.options['downpour'] and os.getuid() == 0:
            try:
                user = self.options['downpour']['user']
                group = self.options['downpour']['group']
                if not pidfile is None:
                    os.chown(pidfile, pwd.getpwnam(user)[2], grp.getgrnam(group)[2])
                os.setgid(grp.getgrnam(group)[2])
                os.setuid(pwd.getpwnam(user)[2])
            except OSError as e:
                logging.error('Could not set user or group: %s' % e)
        if 'umask' in self.options['downpour']:
            old_umask = os.umask(self.options['downpour']['umask'])

    def get_store(self):
        if not self.store:
            need_init = False
            db_path = os.path.expanduser(self.options['downpour']['state'])
            if not os.access(db_path, os.F_OK):
                db_dir = os.path.dirname(db_path)
                if not os.path.exists(db_dir):
                    os.makedirs(db_dir);
                need_init = True
            database = create_database('sqlite:%s' % db_path)
            self.store = Store(database)
            if need_init:
                db.initialize_db(self.store)
            db.upgrade_database(self)
        return self.store

    def get_user(self, username, password):
        user = self.get_store().find(models.User,
            models.User.username == username,
            models.User.password == password).one()
        return user

    def get_manager(self, user=None):
        if user:
            return manager.UserManager(self, user)
        return self.manager

    def get_option(self, option, default=None):
        if option[0] in self.options and option[1] in self.options[option[0]]:
            return self.options[option[0]][option[1]]
        return default

    def set_state(self, name, value):
        state = None
        for s in self.state:
            if s.name == name:
                state = s
                break
        if not state:
            state = models.State()
            state.name = name
            self.state.append(state)
            self.get_store().add(state)
        state.value = unicode(value)
        self.get_store().commit()

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
            setting = models.Setting()
            setting.name = name
            self.settings.append(setting)
            self.get_store().add(setting)
        setting.value = unicode(value)
        self.get_store().commit()

    def get_setting(self, name, default=None):
        for s in self.settings:
            if s.name == name:
                return s.value
        return default

    def is_paused(self):
        return self.get_state(u'paused', u'0') == u'1'

    def add_event_listener(self, event, listener, *args):
        if event in self.listeners:
            self.listeners[event].append([listener, args])

    def fire_event(self, event, *args):
        logging.debug('event: %s' % event)
        if event in self.listeners:
            for l in self.listeners[event]:
                try:
                    cargs = []
                    cargs.extend(args)
                    cargs.extend(l[1])
                    l[0](*cargs)
                except Exception as e:
                    logging.error('Caught error in event listener: %s' % e)
                    traceback.print_exc()
        else:
            raise ValueError('Unknown event "%s"' % event)

    def event_callback(self, result, event, *args):
        self.fire_event(event, *args)
        return result

    def run(self, pidfile=None):
        # Drop privileges after plugin setup in case of privileged port usage
        self.drop_privileges(pidfile)

        # Start server
        reactor.callWhenRunning(self.start)
        reactor.run()
