from jinja2 import PackageLoader
from downpour2.web.common import ModuleRoot


class FeedModule(ModuleRoot):

    def __init__(self, web):

        super(FeedModule, self).__init__(web, 'feeds', PackageLoader('downpour2.feeds.web', 'templates'))

        self.putChild('', self)

    def blocks(self):
        return self._blocks

    def render_GET(self, request):

        return self.render_template('feeds/index.html', request, {
            'title': 'Downpour'
        })
