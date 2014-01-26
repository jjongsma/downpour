import urllib
import logging
from datetime import datetime
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.web import server
from jinja2 import Environment, PackageLoader, PrefixLoader
from downpour.web import auth
from downpour2.core import net, plugin
from downpour2.web import common, site


class WebInterface(plugin.Plugin):

    def __init__(self, app):

        super(WebInterface, self).__init__(app)

        self.log = logging.getLogger(__name__)
        self.template_loader = PackageLoader('downpour2.web', 'templates')

        self.modules = {}
        self.stylesheets = []
        self.scripts = []
        self.blocks = {}

        # Template loader
        self.environment = Environment(loader=PrefixLoader({
            'core': self.template_loader
        }))

        # Custom filters for templateFactory
        self.environment.filters.update({
            'intervalformat': interval_format,
            'timestampformat': timestamp_format,
            'urlencode': urllib.quote
        })

        # Block renderer for plugin content injection
        self.environment.globals.update({
            'stylesheets': self.stylesheets,
            'scripts': self.scripts,
            'pluginblock': self.render_block
        })

        self.site_root = site.SiteRoot(self)

    def register_module(self, module):
        """
        @param module: The module to register
        @ptype module: downpour2.web.common.ModuleRoot
        """

        self.modules[module.namespace] = module
        self.site_root.add_child(module.namespace, module)
        self.stylesheets.extend(module.stylesheets)
        self.scripts.extend(module.scripts)

        for block, fnlist in module.blocks.iteritems():
            if is_sequence(fnlist):
                for fn in fnlist:
                    self.register_block(block, fn)
            else:
                self.register_block(block, fnlist)

    def register_block(self, block, fn):
        if block not in self.blocks:
            self.blocks[block] = []
        self.blocks[block].append(fn)

    def render_block(self, block, request=None):
        out = ''
        if block in self.blocks:
            for fn in self.blocks[block]:
                out += fn(request)
        return out

    def make_environment(self, path, loader):
        return self.environment.overlay(loader=PrefixLoader({
            'core': self.template_loader,
            path: loader
        }))

    def setup(self, config):
        self.config = self.application.config.section('http')

    def start(self):

        # Listen for HTTP connections
        port = 6280
        iface = None

        if self.config is not None:
            if 'port' in self.config:
                port = int(self.config['port'])
            if 'interface' in self.config:
                iface = self.config['interface']

        if iface is None:
            iface = '0.0.0.0'

        handler = server.Site(self.site_root)
        handler.sessionFactory = lambda *args, **kwargs: Session(*args, **kwargs)

        self.try_listen(port, handler, net.get_interface_ip(iface))

    def try_listen(self, port, handler, iface):

        try:
            reactor.listenTCP(port, handler, interface=iface)
            self.log.info('Web interface listening on %s:%d' % (iface, port))

        except CannotListenError as cle:
            # Can happen when connection is not ready yet after boot, keep trying
            self.log.warn('%s (retrying bind in 30 seconds)' % cle)
            reactor.callLater(30.0, self.try_listen, port, handler, iface)


def is_sequence(item):
    return (not hasattr(item, "strip") and
            hasattr(item, "__getitem__") or
            hasattr(item, "__iter__"))


def interval_format(seconds):

    if seconds == -1:
        return 'Infinite'

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    daystr = ''
    if days > 0:
        daystr = '%dd ' % days

    return '%s%d:%.2d:%.2d' % (daystr, hours, minutes, seconds)


def timestamp_format(timestamp, fmt):
    return datetime.fromtimestamp(timestamp).strftime(fmt)


class Session(server.Session, object):

    def __init__(self, *args, **kwargs):
        server.Session.__init__(self, *args, **kwargs)
        self.setAdapter(auth.IAccount, auth.Account)
