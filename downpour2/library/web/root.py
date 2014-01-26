import pkg_resources
from jinja2 import PackageLoader
from downpour2.web.common import ModuleRoot
from downpour2.web.site import MediaPath


class LibraryModule(ModuleRoot):

    def __init__(self, web):

        super(LibraryModule, self).__init__(web, 'library', PackageLoader('downpour2.library.web', 'templates'))

        self.putChild('', self)
        self.putChild('resources', MediaPath(pkg_resources.resource_filename('downpour2.library.web', '/resources')))

        self.scripts = ['/library/resources/js/library.js']
        self.stylesheets = ['/library/resources/css/library.css']

