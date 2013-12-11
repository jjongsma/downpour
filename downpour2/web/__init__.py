import os, math, urllib, logging
from datetime import datetime
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.web import server
from twisted.protocols.policies import ThrottlingFactory
from jinja2 import Environment, PackageLoader
from downpour2.core.plugin import Plugin
from downpour2.core import net, event
from downpour2.web import common
from downpour2.web.site import SiteRoot

class WebInterface(Plugin):

    def setup(self, config):

        self.LOG = logging.getLogger(__name__)

        self.config = self.application.config.section('http')

        templateLoader = PackageLoader('downpour2.web', 'templates')
        self.templateFactory = Environment(loader=templateLoader)
        templateDir = os.path.dirname(templateLoader.get_source(
                self.templateFactory, 'base.html')[1]);

        # Custom filters for templateFactory
        self.templateFactory.filters['intervalformat'] = self.intervalformat
        self.templateFactory.filters['timestampformat'] = self.timestampformat
        self.templateFactory.filters['urlencode'] = urllib.quote
        self.templateFactory.filters['workinglink'] = self.workinglink
        self.templateFactory.filters['librarylink'] = self.librarylink

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

        root = SiteRoot(self.application)
        site = server.Site(root)
        site.requestFactory = common.requestFactory(self)
        site.sessionFactory = common.sessionFactory(self)

        self.tryListen(port, site, net.get_interface(iface))

    def tryListen(self, port, site, iface):

        try:
            reactor.listenTCP(port, site, interface=iface)
            self.LOG.info('Web interface listening on %s:%d' % (iface, port))

        except CannotListenError as cle:
            # Can happen when wifi connection is not ready, just try later
            self.LOG.warn('%s (retrying bind in 30 seconds)' % cle)
            reactor.callLater(30.0, self.tryListen, port, site, iface)

    def intervalformat(self, seconds):

        if seconds == -1:
            return 'Infinite'

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        daystr = '';
        if days > 0:
            daystr = '%dd ' % days

        return '%s%d:%.2d:%.2d' % (daystr, hours, minutes, seconds)

    def workinglink(self, file, download):

        encfile = file.decode('utf8');
        realpath = self.application.manager.get_work_directory(download) + '/' + encfile

        if os.access(realpath, os.R_OK):
            return '<a target="_blank" href="/work/dldir%d/%s">%s</a>' % (download.id, encfile, encfile)
        else:
            return encfile

    def librarylink(self, file):

        if file.filename is None:
            return None

        user = file.user
        fileparts = file.filename.decode('utf8').split('/')
        parents = []

        if file.directory:
            parents.append(file.directory)

        linkparts = []

        for f in fileparts:
            linkparts.append(self.get_library_link(user, '/'.join(parents), f))
            parents.append(f)

        return ' / '.join(linkparts)

    def get_library_link(self, user, directory, path):

        manager = self.application.get_manager(user)
        userdir = manager.get_library_directory()

        if userdir:

            relpath = path

            if directory:
                relpath = '%s/%s' % (directory, path)

            realpath = os.path.normpath('%s/%s' % (userdir, relpath))

            if os.access(realpath, os.R_OK):

                if os.path.isdir(realpath):
                    return '<a href="/browse/%s/">%s</a>' % (relpath, path)
                else:
                    return '<a target="_blank" href="/browse/%s">%s</a>' % (relpath, path)

        return '%s' % path


    def timestampformat(self, timestamp, format):

        return datetime.fromtimestamp(timestamp).strftime(format)
