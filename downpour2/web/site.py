import json
import pkg_resources
from twisted.web import static
from downpour2.core import VERSION
from downpour2.core.util import ObjectEncoder
from downpour2.web import common, transfers, account


class SiteRoot(common.Resource):

    def __init__(self, plugin):

        super(SiteRoot, self).__init__(plugin.application, plugin.environment)

        self.putChild('', self)
        self.putChild('app', AppServices(plugin.application, plugin.environment, plugin))
        self.putChild('media', MediaPath(pkg_resources.resource_filename("downpour2.web", "/media")))
        self.putChild('resources', MediaPath(pkg_resources.resource_filename("downpour2.web", "/resources")))
        self.putChild('transfers', transfers.Root(plugin.application, plugin.environment))
        self.putChild('account', account.Root(plugin.application, plugin.environment))

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

        self.putChild('state', State(application, environment))
        self.putChild('host', Host(application, environment))
        self.putChild('angular-downpour.js', InitJS(application, environment, plugin))


class State(common.Resource):
    """
    Angular module initialization and application bootstrapping.
    """

    def __init__(self, application, environment):

        super(State, self).__init__(application, environment)

        self.putChild('', self)

    def render_GET(self, request):

        return json.dumps({
            'version': VERSION,
            'paused': self.application.paused
        }, cls=ObjectEncoder, indent=4)


class Host(common.Resource):

    def __init__(self, application, environment):
        super(Host, self).__init__(application, environment)
        self.putChild('', self)

    def render_GET(self, request):
        user = self.get_user(request);
        if user is None:
            return self.render_json(self.application.transfer_manager.status)
        else:
            return self.render_json(self.application.transfer_manager.user(self.get_user(request).id).status)


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
