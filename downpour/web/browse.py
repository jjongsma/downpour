from downpour.web import common, auth
from twisted.web import static, server
import os, shutil, urllib, cgi

class Root(common.AuthenticatedResource):

    def __init__(self, *args, **kwargs):
        common.AuthenticatedResource.__init__(self, *args, **kwargs)

    def getChild(self, path, request):
        if not self.is_logged_in(request):
            return self
        manager = self.get_manager(request)
        filepath = manager.get_library_directory()
        return File(str(filepath)).getChild(path, request)

    def render_GET(self, request):
        if 'd' in request.args:
            relpath = request.args['d'][0]

            if relpath == '/' or relpath == '':
                return 'Cannot delete library root'

            path = relpath

            if path[len(path)-1] == '/':
                path = path[:len(path)-1]
            redirect = os.path.dirname(path)

            manager = self.get_manager(request)
            path = '%s%s' % (manager.get_library_directory(), path)
            if os.path.isdir(path):
                context = {
                    'title': 'Confirm Directory Removal',
                    'path': relpath,
                    'redirect': 'browse%s' % redirect
                    }
                return self.render_template('browse/confirmdelete.html', request, context)
            else:
                manager.application.fire_event('library_file_removed', path)
                os.remove(path)

            request.redirect('browse%s' % redirect)
            request.finish()
            return server.NOT_DONE_YET
        else:
            return 'No action specified'

    def render_POST(self, request):
        if 'd' in request.args:
            path = request.args['d'][0]

            if path == '/' or path == '':
                return 'Cannot delete library root'

            if path[len(path)-1] == '/':
                path = path[:len(path)-1]
            redirect = os.path.dirname(path)

            manager = self.get_manager(request)
            path = '%s%s' % (manager.get_library_directory(), path)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                manager.application.fire_event('library_file_removed', path)
                os.remove(path)

            request.redirect('browse%s' % redirect)
            request.finish()
            return server.NOT_DONE_YET
        else:
            return 'No action specified'

class File(static.File):

    def __init__(self, *args, **kwargs):
        static.File.__init__(self, *args, **kwargs)

    def directoryListing(self):
        lister = DirectoryIndex(self.path,
            self.listNames(),
            self.contentTypes,
            self.contentEncodings,
            self.defaultType)
        return lister

class DirectoryIndex(static.DirectoryLister, common.Resource):

    def __init__(self, *args, **kwargs):
        static.DirectoryLister.__init__(self, *args, **kwargs)
        self.path = self.path.decode('utf8')

    def render(self, request):
        directory = os.listdir(self.path)
        directory.sort()

        manager = self.get_manager(request)
        relPath = self.path[len(manager.get_library_directory()):]
        dirs, files = self.getFilesAndDirectories(directory)
        context = {
            'title': 'My Media: %s/' % relPath,
            'path': relPath,
            'directories': dirs,
            'files': files
            }

        return self.render_template('browse/directory.html', request, context)

    def getFilesAndDirectories(self, directory):
        files = []
        dirs = []
        for path in directory:
            url = urllib.quote(path.encode('utf8'), "/")
            escapedPath = cgi.escape(path)
            if os.path.isdir(os.path.join(self.path, path)):
                url = url + '/'
                dirs.append({'text': escapedPath + "/", 'href': url,
                             'size': '', 'type': '[Directory]',
                             'encoding': ''})
            else:
                mimetype, encoding = static.getTypeAndEncoding(path, self.contentTypes,
                                                        self.contentEncodings,
                                                        self.defaultType)
                try:
                    size = os.stat(os.path.join(self.path, path)).st_size
                except OSError:
                    continue
                files.append({
                    'text': escapedPath, "href": url,
                    'type': '[%s]' % mimetype,
                    'encoding': (encoding and '[%s]' % encoding or ''),
                    'size': static.formatFileSize(size)})
        return dirs, files
