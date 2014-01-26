import json
import pkg_resources
from twisted.web import static
from downpour2.core import VERSION
from downpour2.web import common, transfers
from downpour2.web.common import ObjectEncoder


class SiteRoot(common.Resource):

    def __init__(self, plugin):

        super(SiteRoot, self).__init__(plugin.application, plugin.environment)

        self.putChild('', self)
        self.putChild('app', AppServices(plugin.application, plugin.environment, plugin))
        self.putChild('media', MediaPath(pkg_resources.resource_filename("downpour2.web", "/media")))
        self.putChild('resources', MediaPath(pkg_resources.resource_filename("downpour2.web", "/resources")))
        self.putChild('transfers', transfers.Root(plugin.application, plugin.environment))
        # self.putChild('account', account.Root(application, environment))

    def add_child(self, path, resource):

        if path in self.children:
            raise ValueError('Module path "%s" is already registered' % path)

        self.putChild(path, resource)

    def render_GET(self, request):

        return self.render_template('core/app.html', request, {
            'title': 'Downpour'
        })


class AppServices(common.Resource):
    """
    Return core app settings and configuration as JSON
    """

    def __init__(self, application, environment, plugin):

        super(AppServices, self).__init__(application, environment)

        self.putChild('', self)
        self.putChild('config', ConfigJS(application, environment))
        self.putChild('angular-downpour.js', InitJS(application, environment, plugin))

    def render_GET(self, request):

        return "{}"


class ConfigJS(common.Resource):
    """
    Angular module initialization and application bootstrapping.
    """

    def __init__(self, application, environment):

        super(ConfigJS, self).__init__(application, environment)

        self.putChild('', self)

    def render_GET(self, request):

        return json.dumps({
            'version': VERSION,
            'paused': self.application.paused,
            'user': self.get_user(request),
            'notifications': ['Test']
        }, cls=ObjectEncoder, indent=4)


class InitJS(common.Resource):
    """
    Angular module initialization and application bootstrapping.
    """

    def __init__(self, application, environment, plugin):

        super(InitJS, self).__init__(application, environment)

        self.plugin = plugin

        self.putChild('', self)

    def render_GET(self, request):

        return self.render_template('core/angular-downpour.js', request, {
            'modules': self.plugin.modules.values()
        }, 'text/javascript')


class MediaPath(static.File):

    def directoryListing(self):
        return self.childNotFound
