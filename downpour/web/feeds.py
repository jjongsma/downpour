from downpour.web import common
from downpour.core import models, organizer
from downpour.feed import checker
from twisted.web import server

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self);
        self.putChild('add', Add())
        self.putChild('save', Save())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Detail(int(path))

    def render_GET(self, request):
        manager = self.get_manager(request)
        context = {
            'title': 'Feed Subscriptions',
            'mediatypes': organizer.get_media_types(),
            'feeds': manager.get_feeds()
        }
        return self.render_template('feeds/index.html', request, context)

class Add(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        manager = self.get_manager(request)

        feed = {
            'active': True,
            'media_type': 'video/tv',
            'update_frequency': 15,
            'queue_size': 0,
            'save_priority': 0 }

        if 'url' in request.args:
            feed['url'] = request.args['url'][0]
        if 'name' in request.args:
            feed['name'] = request.args['name'][0]

        context = {
            'title': 'Add Feed',
            'feed': feed,
            'mediatypes': organizer.get_media_types()
        }
        return self.render_template('feeds/form.html', request, context)

class Detail(common.AuthenticatedResource):

    def __init__(self, id):
        common.AuthenticatedResource.__init__(self)
        self.id = id

    def getChild(self, path, request):
        if (path == ''):
            return self
        manager = self.get_manager(request)
        if manager:
            feed = manager.get_feed(self.id)
            if (path == 'edit'):
                return Edit(feed)
            elif (path == 'save'):
                return Save(feed)
            elif (path == 'delete'):
                return Delete(feed)
            elif (path == 'inject'):
                return Inject(feed)
        else:
            return self

    def render_GET(self, request):
        manager = self.get_manager(request)
        feed = manager.get_feed(self.id)
        context = {'title': feed.name,
                   'feed': feed,
                   'mediatypes': organizer.get_media_types()
                   }
        return self.render_template('feeds/detail.html', request, context)

class Edit(common.AuthenticatedResource):

    def __init__(self, feed):
        common.AuthenticatedResource.__init__(self)
        self.feed = feed

    def render_GET(self, request):
        manager = self.get_manager(request)
        context = {
            'title': 'Edit Feed',
            'feed': self.feed,
            'mediatypes': organizer.get_media_types()
        }
        return self.render_template('feeds/form.html', request, context)

class Save(common.AuthenticatedResource):

    def __init__(self, feed=None):
        common.AuthenticatedResource.__init__(self)
        self.feed = feed

    def render_POST(self, request):
        manager = self.get_manager(request)
        converters = {
            'name': lambda v: unicode(v),
            'url': lambda v: unicode(v),
            'media_type': lambda v: unicode(v),
            'active': lambda v: v == '1',
            'auto_clean': lambda v: v == '1',
            'update_frequency': lambda v: int(v),
            'queue_size': lambda v: int(v),
            'save_priority': lambda v: int(v),
            'download_directory': lambda v: unicode(v),
            'rename_pattern': lambda v: unicode(v)
        }

        # Use specified model or create new for adding
        feed = self.feed
        if not feed:
            feed = models.Feed()
            feed.user = self.get_user(request)
            manager.store.add(feed)

        # Updated object from form
        for k in request.args:
            v = request.args[k][0]
            if hasattr(feed, k) and k in converters:
                setattr(feed, k, converters[k](request.args[k][0]))
        if not 'auto_clean' in request.args:
            feed.auto_clean = False
        if not 'active' in request.args:
            feed.active = False
        manager.store.commit()

        # Update immediately if requested
        if 'updatenow' in request.args:
            checker.update_feeds([feed], manager.application)

        request.redirect('/feeds')
        request.finish()
        return server.NOT_DONE_YET

class Delete(common.AuthenticatedResource):

    def __init__(self, feed):
        common.AuthenticatedResource.__init__(self)
        self.feed = feed

    def render_GET(self, request):
        manager = self.get_manager(request)
        manager.remove_feed(self.feed.id)
        request.redirect('/feeds')
        request.finish()
        return server.NOT_DONE_YET

class Inject(common.AuthenticatedResource):

    def __init__(self, feed):
        common.AuthenticatedResource.__init__(self)
        self.feed = feed

    def render_GET(self, request):
        if 'item' in request.args:
            itemid = int(request.args['item'][0])
            manager = self.get_manager(request)
            items = [i for i in self.feed.items if i.id == itemid];
            if len(items):
                item = items[0]
                d = models.Download()
                d.feed_id = self.feed.id
                d.user_id = self.feed.user_id
                d.url = item.link
                d.description = item.title
                d.media_type = self.feed.media_type
                item.download = d
                manager.add_download(d)
                item.removed = False
                manager.store.commit()
                request.redirect('/downloads')
                request.finish()
                return server.NOT_DONE_YET
            else:
                return common.NotFoundResource().render(request)
        else:
            return common.NotFoundResource().render(request)
