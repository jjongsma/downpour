from twisted.internet import reactor
from twisted.web import server
from twisted.protocols.policies import ThrottlingFactory
from jinja2 import Environment, PackageLoader
from downpour.core.plugins import Plugin
from downpour.core.net import get_interface
from downpour.web.common import requestFactory, sessionFactory
from downpour.web.site import SiteRoot
from datetime import datetime
import os, math, urllib

class WebInterfacePlugin(Plugin):

    def setup(self, config):

        # Listen for HTTP connections
        port = 6280
        iface = None

        if config is not None:
            if 'port' in config:
                port = int(config['port'])
            if 'interface' in config:
                iface = config['interface']

        if iface is None:
            iface = '0.0.0.0'

        templateLoader = PackageLoader('downpour.web', 'templates')
        self.templateFactory = Environment(loader=templateLoader)
        templateDir = os.path.dirname(templateLoader.get_source(
                self.templateFactory, 'base.html')[1]);

        # Custom filters for templateFactory
        self.templateFactory.filters['progressbar'] = self.progressbar
        self.templateFactory.filters['healthmeter'] = self.healthmeter
        self.templateFactory.filters['intervalformat'] = self.intervalformat
        self.templateFactory.filters['timestampformat'] = self.timestampformat
        self.templateFactory.filters['urlencode'] = urllib.quote
        self.templateFactory.filters['workinglink'] = self.workinglink
        self.templateFactory.filters['librarylink'] = self.librarylink

        root = SiteRoot(templateDir + '/media', self.application)
        site = server.Site(root)
        site.requestFactory = requestFactory(self)
        site.sessionFactory = sessionFactory(self)

        reactor.listenTCP(port, site, interface=get_interface(iface))

    def progressbar(self, percentage, width=100, style=None, label=''):
        pixwidth = ''
        dimstyle = ''
        if type(width) == str and width.endswith('%'):
            pixwidth = str(int(math.ceil(percentage))) + '%'
            dimstyle = ' style="width: ' + str(width) + ';"'
        else:
            pixwidth = str(int(math.ceil((float(percentage)/100) * width))) + 'px'
            dimstyle = ' style="width: ' + str(width) + 'px;"'
        cssclass = ''
        if style:
            cssclass = ' ' + style
        if not percentage:
            percentage = 0
        phtml = '<div class="progressmeter"' + dimstyle + '>'
        phtml = phtml + '<div class="progress' + cssclass + '" style="width: ' + \
            str(pixwidth) + ';">&nbsp;</div>'
        phtml = phtml + '<div class="label" style="width: 100%">' + \
            str(round(percentage, 1)) + '% ' + label + '</div>'
        phtml = phtml + '</div>'
        return phtml

    def healthmeter(self, percentage, height=16):
        pixheight = int(math.ceil((float(percentage)/100) * height))
        dimstyle = ' style="height: ' + str(height) + 'px;"'
        if not percentage:
            percentage = 0
        cssclass = ' green'
        if percentage < 25:
            cssclass = ' red'
        elif percentage < 50:
            cssclass = ' yellow'
        phtml = '<div class="healthmeter' + cssclass + '"' + dimstyle + '>'
        phtml = phtml + '<div class="health' + cssclass + '" style="height: ' + \
            str(pixheight) + 'px;"></div>'
        phtml = phtml + '</div>'
        return phtml

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
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format)

    def urlencode(self, url):
        if url:
            #return url
            return urllib.urlencode(str(url))
