from downpour.web import common, auth
from downpour.web.static import ThrottledFile
from downpour.core import models
from twisted.web import static, server
from datetime import datetime
import os, shutil, urllib, cgi, json, time, logging

class SharedResource(common.Resource):

    def render(self, request, *args):
        if not self.is_logged_in(request):
            request.setResponseCode(401)
            request.write('Authentication failed')
            request.finish()
            return server.NOT_DONE_YET
        return Resource.render(self, request, *args)

    def get_user(self, request):
        if 'username' in request.args and 'password' in request.args:
            user = request.application.get_store().find(models.User,
                models.User.username == unicode(request.args['username'][0])
                ).one()
            if user.share_password == unicode(request.args['password'][0]):
                return user
        return None

class Root(SharedResource):

    def __init__(self, *args, **kwargs):
        SharedResource.__init__(self, *args, **kwargs)

    def getChild(self, path, request):

        if not self.is_logged_in(request):
            return self

        manager = self.get_manager(request)
        rateFilter = manager.get_upload_rate_filter()

        filepath = manager.get_library_directory()
        rootFile = SharedFile(str(filepath), bucketFilter=rateFilter, relpath='',
                basepath=manager.get_library_directory(),
                link='http://%s:%s/share%%s?username=%s&password=%s' % (
                    request.getRequestHostname(),
                    request.getHost().port,
                    request.args['username'][0],
                    request.args['password'][0])
            )

        return rootFile.getChild(path, request)

class SharedFile(ThrottledFile):

    def __init__(self, path, bucketFilter=None, defaultType="text/html", ignoredExts=(),
            registry=None, allowExt=0, relpath='', basepath='', link=None):
        ThrottledFile.__init__(self, path, bucketFilter=bucketFilter, defaultType=defaultType,
            ignoredExts=ignoredExts, registry=registry, allowExt=allowExt)
        self.basepath = basepath
        self.relpath = relpath
        self.link = link

    def render_GET(self, request):
        # TODO: Add sharing monitoring
        logging.info('Sharing request from %s: GET %s' % (request.getClientIP(), request.path))
        return ThrottledFile.render_GET(self, request)

    def createSimilarFile(self, path):
        relpath = self.relpath
        if path:
            relpath = path[len(self.basepath)+1:]
        f = self.__class__(path, bucketFilter=self.bucketFilter,
            defaultType=self.defaultType, ignoredExts=self.ignoredExts,
            registry=self.registry, relpath=relpath, basepath=self.basepath, link=self.link)
        f.processors = self.processors
        f.indexNames = self.indexNames[:]
        f.childNotFound = self.childNotFound
        return f

    def directoryListing(self):
        lister = DirectoryIndex(
            self.path,
            self.listNames(),
            self.contentTypes,
            self.contentEncodings,
            self.defaultType)
        lister.relpath = self.relpath
        lister.link = self.link
        return lister

class DirectoryIndex(static.DirectoryLister, SharedResource):

    def __init__(self, *args, **kwargs):
        static.DirectoryLister.__init__(self, *args, **kwargs)
        self.path = self.path.decode('utf8')

    def render(self, request):

        manager = self.get_manager(request)

        if 'rss' in request.args:
            files = self.getFilesRecursive(self.path, self.relpath)
            timestamp = 0
            if len(files):
                timestamp = files[0]['modtime']
            return self.render_template('share/rss.html', request, {
                'timestamp': timestamp,
                'files': files
                })
        else:
            directory = os.listdir(self.path)
            directory.sort()
            dirs, files = self.getFilesAndDirectories(self.path, directory)
            dirs.extend(files)
            request.write(json.dumps(dirs, indent=4))
            request.finish()
            return server.NOT_DONE_YET

    def getFilesRecursive(self, directory, path = None):
        entries = os.listdir(directory)
        dirs, files = self.getFilesAndDirectories(directory, entries)
        for f in files:
            relpath = os.path.join(path, f['name'])
            if relpath[0] != '/':
                relpath = '/' + relpath
            f['url'] = self.link % urllib.quote(relpath)
        for d in dirs:
            subfiles = self.getFilesRecursive(
                '%s/%s' % (directory, d['name']),
                '%s/%s' % (path, d['name']))
            files.extend(subfiles)
            #for f in subfiles:
                #f['url'] = self.link % os.path.join(path, d['name'], f['name'])
                #files.append(f)
        files.sort(lambda x,y: -cmp(x['modtime'], y['modtime']))
        return files[:30]

    def getFilesAndDirectories(self, root, directory):
        files = []
        dirs = []
        for path in directory:
            url = urllib.quote(path.encode('utf8'), "/")
            escapedPath = cgi.escape(path)
            if os.path.isdir(os.path.join(root, path)):
                url = url + '/'
                dirs.append({
                    'name': path,
                    'text': escapedPath + "/",
                    'href': url,
                    'type': 'directory',
                    'size': '',
                    'encoding': ''})
            else:
                mimetype, encoding = static.getTypeAndEncoding(path, self.contentTypes,
                                                        self.contentEncodings,
                                                        self.defaultType)
                size = 0
                modtime = 0
                try:
                    fstat = os.stat(os.path.join(root, path))
                    size = fstat.st_size
                    modtime = time.mktime(datetime.utcfromtimestamp(fstat.st_ctime).timetuple())
                except OSError as e:
                    continue
                files.append({
                    'name': path,
                    'text': escapedPath,
                    "href": url,
                    'type': mimetype,
                    'size': size,
                    'modtime': modtime,
                    'encoding': (encoding and '%s' % encoding or '')})
        return dirs, files
