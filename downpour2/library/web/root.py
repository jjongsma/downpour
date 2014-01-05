from jinja2 import PackageLoader
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

    def blocks(self):
        return self._blocks

    def render_GET(self, request):

        return self.render_template('library/index.html', request, {
            'title': 'Downpour'
        })
