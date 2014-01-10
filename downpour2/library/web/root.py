import json
from jinja2 import PackageLoader
from downpour2.library.web.demo import DemoStatus
from downpour2.web import common
from downpour2.web.common import ModuleRoot


class LibraryModule(ModuleRoot):

    def __init__(self, web):

        super(LibraryModule, self).__init__(web, 'library', PackageLoader('downpour2.library.web', 'templates'))

        self._blocks = {
            'sidelink': web.link_renderer('/library/', 'Media Library'),
            'settinglink': web.link_renderer('/library/types', 'Media Types'),
            'homecolumn': lambda req: self.render_template('library/home-blocks.html', req, {})
        }

        self.putChild('', self)
        self.putChild('status', Status(self.application, self.environment))

    def blocks(self):
        return self._blocks

    def render_GET(self, request):

        return self.render_template('library/index.html', request, {
            'title': 'Downpour'
        })


class Status(common.AuthenticatedResource):

    def __init__(self, application, environment):
        super(Status, self).__init__(application, environment)
        self.putChild('', self)
        self.putChild('demo', DemoStatus(application, environment))

    def render_GET(self, request):
        agent = self.application.transfer_manager.user(self.get_user(request).id)
        return json.dumps({
            'status': agent.status,
            'transfers': agent.transfers
        }, cls=ObjectEncoder, indent=4)


class ObjectEncoder(json.JSONEncoder):

    def default(self, o):
        return o.__dict__
