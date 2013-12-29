import os
import logging
import shutil
from time import time
from twisted.internet import defer
from urlparse import urlparse
from downpour.core import models, organizer
from downpour.download import Status
from downpour.download.throttling import ThrottledBucketFilter
from downpour.download.http import HTTPDownloadClient
from downpour.download.torrent import LibtorrentClient


class Manager(object):

    download_clients = []
    downloads = None
    feeds = None
    libraries = None

    client_mimetypes = {
        'application/x-bittorrent': LibtorrentClient
    }

    client_protocols = {
        'http': HTTPDownloadClient,
        'https': HTTPDownloadClient,
        'magnet': LibtorrentClient
    }

    def pause_download(self, id):
        d = self.get_download(id)
        dc = self.get_download_client(id)
        dfr = None
        if dc and dc.is_stoppable():
            logging.info(u'Pausing download %s (%s)' % (d.id, d.description))
            dfr = defer.maybeDeferred(dc.pause)
            dfr.addCallback(self.update_status, d, Status.STOPPED)
            dfr.addErrback(self.update_status, d, Status.STOPPED)
        else:
            dfr = defer.succeed(True)
        self.store.commit()
        return dfr

    def resume_download(self, id):
        d = self.get_download(id)
        try:
            dc = self.get_download_client(id)
            dfr = None
            if not self.paused and dc and dc.is_startable():
                logging.info(u'Resuming download %s (%s)' % (d.id, d.description))
                dfr = defer.maybeDeferred(dc.resume)
                if not d.started:
                    d.started = time()
            else:
                dfr = defer.succeed(True)
            self.store.commit()
            return dfr
        except Exception as e:
            d.status = Status.FAILED
            d.status_message = unicode(e)
            self.application.fire_event('download_failed', d, e)
            logging.error(u'Download failed: %s' % d.status_message)

    def remove_download(self, id, remove_files=True):
        d = self.get_download(id)
        dfr = self.stop_download(id)
        dfr.addCallback(self.remove_download_success, d, remove_files)
        dfr.addErrback(self.remove_download_success, d, remove_files)
        return dfr

    def remove_download_success(self, result, d, remove_files=True):
        if not d:
            return
        dc = self.get_download_client(d.id)
        if dc:
            dc.remove()
            Manager.download_clients.remove(dc)
        d.deleted = True
        self.store.commit()
        # Flush delete items out of local cache
        self.get_downloads(True)
        try:
            if remove_files:
                workdir = self.get_work_directory(d)
                if os.path.isdir(workdir):
                    shutil.rmtree(workdir)
        except Exception as e:
            logging.error(e)

        self.application.fire_event('download_removed', d)
        logging.info(u'Removed download %s (%s)' % (d.id, d.description))

    def remove_download_failed(self, failure, dc, d):
        d.status_message = unicode(failure.getErrorMessage())
        logging.error(u'Failed to stop download %s: %s' % (d.id, failure.getErrorMessage()))

    def get_download_client(self, id, create=False):
        d = self.get_download(id)
        for dc in Manager.download_clients:
            if hasattr(dc, 'download') and dc.download.id == id:
                return dc

        if create:
            try:
                clientdir = self.get_work_directory(d)
                client = None
                if d.mime_type and d.mime_type in self.client_mimetypes:
                    client = self.client_mimetypes[d.mime_type](d, self, clientdir)
                elif d.url:
                    protocol = urlparse(d.url).scheme
                    if protocol in Manager.client_protocols:
                        client = Manager.client_protocols[protocol](d, self, clientdir)
                Manager.download_clients.append(client);
                client.addCallback(self.download_complete, client, d)
                client.addErrback(self.download_failed, client, d)
                return client
            except:
                return None

    def download_complete(self, new_mimetype, dc, d):
        if new_mimetype:
            Manager.download_clients.remove(dc)
            ndc = self.get_download_client(d.id, True)
            if ndc and dc.__class__ != ndc.__class__:
                # New mimetype requires different download handler,
                # we just downloaded a metadata file
                logging.debug(u'Got metadata for %s (%s)' % (d.id, d.description))
                metafile = self.get_work_directory(d) + '/' + d.filename
                if os.access(metafile, os.R_OK):
                    f = open(metafile, 'rb')
                    d.metadata = f.read()
                    f.close()
                d.progress = 0
                self.start_download(d.id)
                return
        d.status = Status.COMPLETED
        d.active = False
        d.completed = time()
        d.status_message = None
        self.store.commit()
        self.application.fire_event('download_complete', d)
        logging.info(u'Finished downloading %s (%s)' % (d.id, d.description))
        # NOTE: if upload_ratio is > 0, this will not get run until
        # seeding is finished!
        self.process_download(d, dc)

    def process_download(self, d, dc):
        dfr = organizer.process_download(self.application.get_manager(d.user), d, dc)
        dfr.addCallback(self.process_download_complete, d)
        dfr.addErrback(self.process_download_failed, d)
        return dfr

    def process_download_complete(self, result, d):
        d.imported = True
        d.status_message = None
        if d.feed and d.feed.auto_clean:
            self.remove_download(d.id)
        self.application.fire_event('download_imported', d)
        logging.info(u'Imported %s (%s)' % (d.id, d.description))
        self.store.commit()

    def process_download_failed(self, failure, d):
        d.status_message = unicode(failure.getErrorMessage())
        self.application.fire_event('download_import_failed', d, failure.value)
        logging.error(u'Import failed for %s (%s)' % (d.id, d.description))
        logging.error(str(failure))
        self.store.commit()

    def download_failed(self, failure, dc, d):
        d.status = Status.FAILED
        d.active = False
        d.status_message = unicode(failure.getErrorMessage())
        self.store.commit()
        self.application.fire_event('download_failed', d, failure.value)
        logging.error(u'Download %s failed: %s' % (d.id, failure.getErrorMessage()))

    def start_download(self, id, force=False):
        d = self.get_download(id)
        try:
            dc = self.get_download_client(id, True)
            d.active = True
            d.status_message = None
            dfr = None
            if not self.paused and dc and (dc.is_startable() or force):
                self.application.fire_event('download_started', d)
                logging.info(u'Starting download %s (%s)' % (d.id, d.description))
                dfr = defer.maybeDeferred(dc.start)
                dfr.addErrback(self.download_failed, dc, d)
                if not d.started:
                    d.started = time()
            else:
                dfr = defer.succeed(False)
            self.store.commit()
            return dfr
        except Exception as e:
            d.status = Status.FAILED
            d.status_message = unicode(e)
            d.active = False
            self.application.fire_event('download_failed', d, e)
            logging.error(u'Download failed: %s' % d.status_message)

    def commit_store(self, result):
        self.store.commit()

    def stop_download(self, id):
        d = self.get_download(id)
        d.active = False
        dc = self.get_download_client(id)
        dfr = None
        if dc and dc.is_stoppable():
            logging.info(u'Stopping download %s (%s)' % (d.id, d.description))
            dfr = defer.maybeDeferred(dc.stop)
            dfr.addCallback(self.update_status, d, Status.STOPPED)
            dfr.addErrback(self.update_status, d, Status.STOPPED)
        else:
            dfr = defer.succeed(False)
        self.store.commit()
        return dfr

    def add_feed(self, f):
        self.store.add(f)
        self.store.commit()
        self.application.fire_event('feed_added', f)
        logging.info(u'Added new feed ' + f.url)
        return f.id

    def check_feed_success(self, parsed, feed):
        if not feed.name or not len(feed.name):
            feed.name = parsed.feed.title
        self.store.commit()
        logging.debug(u'Retrieved feed %s' % feed.name)

    def check_feed_failure(self, failure, feed):
        feed.last_error = unicode(failure.getErrorMessage())
        self.store.commit()
        logging.error(u'Feed retrieval failed: %s' % feed.name)

    def get_feeds(self):
        raise NotImplementedError('Manager must be subclassed')

    def get_feed(self, id):
        for f in self.get_feeds():
            if f.id == id:
                return f
        raise Exception('Feed not found')

    def remove_feed(self, id):
        f = self.get_feed(id)
        # Delete from database
        self.store.remove(f)
        self.store.commit()
        self.application.fire_event('feed_removed', f)
        logging.info(u'Removed feed %s (%s)' % (f.id, f.name))
        return True

    def get_library(self, id=None, media_type=None):
        for l in self.get_libraries():
            if id and l.id == id:
                return l
            elif media_type and l.media_type == media_type:
                return l
        return None

    def get_libraries(self):
        raise NotImplementedError('Manager must be subclassed')

    def get_option(self, name, default=None):
        return self.application.get_option(name, default);

    def get_setting(self, name, default=None):
        return self.application.get_setting(name, default);

    def get_user_directory(self):
        return os.path.expanduser(self.get_option(('downpour', 'user_directory'), '~/Downloads'))

    def get_upload_rate_filter(self):
        # Fallthrough to GlobalManager instance, since bandwidth is shared
        # among all users
        return self.application.manager.get_upload_rate_filter()

    def get_download_rate_filter(self):
        # Fallthrough to GlobalManager instance, since bandwidth is shared
        # among all users
        return self.application.manager.get_download_rate_filter()


class GlobalManager(Manager):

    upload_rate_filter = None
    download_rate_filter = None

    def get_feeds(self):
        if self.feeds is None:
            self.feeds = list(self.store.find(models.Feed).order_by(models.Feed.name))
        return self.feeds

    def get_upload_rate_filter(self):
        max_ulrate = int(self.get_setting('upload_rate', 0)) * 1024
        if not self.upload_rate_filter:
            self.upload_rate_filter = ThrottledBucketFilter(max_ulrate)
        else:
            self.upload_rate_filter.rate = max_ulrate
        return self.upload_rate_filter

    def get_download_rate_filter(self):
        max_dlrate = int(self.get_setting('download_rate', 0)) * 1024
        if not self.download_rate_filter:
            self.download_rate_filter = ThrottledBucketFilter(max_dlrate)
        else:
            self.download_rate_filter.rate = max_dlrate
        return self.download_rate_filter


class UserManager(Manager):

    def add_feed(self, f):
        f.user = self.user
        return Manager.add_feed(self, f)

    def get_feeds(self):
        if self.user.admin:
            return list(self.store.find(models.Feed
                ).order_by(models.Feed.name))
        elif self.feeds is None:
            return list(self.store.find(models.Feed,
                models.Feed.user_id == self.user.id
                ).order_by(models.Feed.name))
        return self.feeds

    def get_libraries(self):
        if self.libraries is None:
            self.libraries = list(self.store.find(models.Library,
                models.Library.user_id == self.user.id
                ).order_by(models.Library.media_type))
        return self.libraries

    def get_library_directory(self):
        userdir = self.user.directory
        if not userdir:
            userdir = '%s/%s' % (self.get_user_directory(), self.user.username)
        userdir = os.path.expanduser(userdir)
        if userdir[0] != '/':
            userdir = '%s/%s' % (os.getcwd(), userdir)
        if not os.path.exists(userdir):
            os.mkdir(userdir)
        return userdir

    def get_full_path(self, path, media_type=None):
        parts = [self.get_library_directory()]
        if media_type:
            libraries = self.get_libraries()
            for l in libraries:
                if l.media_type == media_type:
                    parts.append(l.directory)
                    break
        parts.append(path)
        return os.path.expanduser('/'.join(parts))
