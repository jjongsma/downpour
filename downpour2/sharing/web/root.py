from jinja2 import PackageLoader
from downpour2.web.common import ModuleRoot


class SharingModule(ModuleRoot):

    def __init__(self, web):

        super(SharingModule, self).__init__(web, 'sharing', PackageLoader('downpour2.sharing.web', 'templates'))

        self.putChild('', self)

    def blocks(self):
        return self._blocks

    def render_GET(self, request):

        return self.render_template('sharing/index.html', request, {
            'title': 'Downpour'
        })
