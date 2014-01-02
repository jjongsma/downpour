from downpour.core import VERSION
from downpour.core.net import get_interface
from downpour.download import *
from twisted.internet import defer, task, reactor
from twisted.web import client
from twisted.python import failure
import libtorrent as lt
import os, marshal, math, sys, socket, logging, zlib, time

class LibtorrentManager:

    def __init__(self):
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.session.set_alert_mask(
            lt.alert.category_t.error_notification |
            lt.alert.category_t.storage_notification |
            lt.alert.category_t.status_notification |
            lt.alert.category_t.progress_notification |
            lt.alert.category_t.performance_warning)
        self.torrents = {}
        self.limits_updated = False

        settings = lt.session_settings()
        # TODO: set upload ratio settings, rate limits, etc
        settings.user_agent = 'Downpour/%s libtorrent/%d.%d' % (VERSION,
                            lt.version_major, lt.version_minor)
        # settings.share_ratio_limit = float(self.manager.get_setting('upload_ratio', 0))
        self.session.set_settings(settings)

        # Update torrent status
        self.status_update = task.LoopingCall(self.status_update)
        self.status_update.start(2.0)
        # Process generated alerts
        self.alert_monitor = task.LoopingCall(self.process_alerts)
        self.alert_monitor.start(2.0)
        # Update rate / connection limits
        self.limit_update = task.LoopingCall(self.limit_update)
        self.limit_update.start(5.0)

    def status_update(self):
        try:
            for t in self.torrents:
                self.torrents[t].update_status()
        except Exception as e:
            pass

    def limit_update(self):
        if self.limits_updated:
            dlrate = 0
            ulrate = 0
            conns = 0

            for t in self.torrents:
                dlrate += self.torrents[t].download_rate
                ulrate += self.torrents[t].upload_rate
                conns += self.torrents[t].max_connections

            if dlrate:
                self.session.set_download_rate_limit(dlrate)
            else:
                self.session.set_download_rate_limit(-1)

            if ulrate:
                self.session.set_upload_rate_limit(ulrate)
            else:
                self.session.set_upload_rate_limit(-1)

            if conns:
                self.session.set_max_connections(conns)
            else:
                self.session.set_max_connections(-1)

            self.limits_updated = False

    def process_alerts(self):
        sys.stdout.flush()
        alert = self.session.pop_alert()
        while alert:
            sys.stdout.flush()
            alert_type = str(type(alert)).split("'")[1].split(".")[-1]
            if not (hasattr(alert, 'handle') and self.dispatch_alert(alert, alert_type)):
                #logging.debug("GLOBAL: %s: %s" % (alert_type, alert.message()))
                pass
            alert = self.session.pop_alert()

    def dispatch_alert(self, alert, alert_type):
        if alert.handle.is_valid():
            ih = str(alert.handle.info_hash())
            if ih in self.torrents:
                return self.torrents[ih].handle_alert(alert, alert_type)
        return False

    # Pass calls through
    def add_magnet(self, client, url, params):
        handle = lt.add_magnet_uri(self.session, url, params)
        ih = str(handle.info_hash())
        if ih in self.torrents:
            raise Exception('Duplicate torrent')
        self.torrents[ih] = client
        return handle

    # Pass calls through
    def add_torrent(self, client, *args, **kwargs):
        handle = self.session.add_torrent(*args, **kwargs)
        ih = str(handle.info_hash())
        if ih in self.torrents:
            raise Exception('Duplicate torrent')
        self.torrents[ih] = client
        return handle

    def remove_torrent(self, t):
        if t.torrent and t.torrent.is_valid():
            ih = str(t.torrent.info_hash())
            if ih in self.torrents:
                self.session.remove_torrent(t.torrent, 1)
                del self.torrents[ih]

    # Set comm interface (useful for routing torrent traffic over VPN, etc)
    def listen(self, interface=None):
        ip = get_interface(interface)
        if not ip is None:
            self.session.listen_on(6881, 6891, ip)
        else:
            self.session.listen_on(6881, 6891)

# Single session manager
lt_manager = LibtorrentManager()

class LibtorrentClient(DownloadClient):
    
    capabilities = Capabilities.MULTICONN|Capabilities.UPLOAD

    def __init__(self, download, manager, directory):
        DownloadClient.__init__(self, download, manager, directory)
        if download.metadata:
            self.torrent_info = lt.torrent_info(lt.bdecode(self.download.metadata))
            download.description = unicode(self.torrent_info.name())
            if not download.size:
                download.size = self.torrent_info.total_size()
        else:
            self.torrent_info = None
        self.torrent = None
        self.rebinding = False
        self.dfm = {}
        self.autostop = True

    # Set comm interface (useful for routing torrent traffic over VPN, etc)
    def rebind(self, errorTriggered=False):

        if self.rebinding and errorTriggered:
            logging.debug('Skipped rebind(), already waiting')
            return
        
        interface = self.manager.get_option(('downpour', 'interface'))
        try:
            logging.debug('Rebinding torrent manager to interface %s' % interface);
            ip = get_interface(interface)
            if lt_manager.session.is_paused():
                lt_manager.session.resume()
            lt_manager.listen(interface)
            if not self.torrent is None and not ip is None:
                self.torrent.use_interface(ip)
            self.rebinding = False
        except IOError as e:
            if errorTriggered:
                logging.info('The specified network interface is not available: %s' % interface)
            self.rebinding = True
            lt_manager.session.pause()
            reactor.callLater(30.0, self.rebind)
            
    def start(self):
        # TODO: recheck listening interface; may need to rebind manager to renewed IP
        if 'state_changed_alert' in self.dfm:
            raise Exception('An operation is already in progress')
        self.dfm['state_changed_alert'] = defer.Deferred()
        if not self.torrent and not self.download.metadata:
            if self.download.url:
                # Don't try to re-fetch until an attempt is done
                if self.download.status != Status.LOADING:
                    if self.download.url.startswith('magnet:'):
                        params = { 'save_path': str(self.directory), 'auto_managed': True }
                        resdata = None
                        if self.download.resume_data:
                            params['resdata'] = marshal.loads(self.download.resume_data)
                        self.download.status = Status.LOADING
                        self.torrent = lt_manager.add_magnet(self, str(self.download.url), params)
                        self.dfm['metadata_received_alert'] = defer.Deferred()
                        self.dfm['metadata_received_alert'].addCallback(self.magnet_loaded)
                        self.dfm['metadata_failed_alert'] = defer.Deferred()
                        self.dfm['metadata_failed_alert'].addCallback(self.magnet_load_failed)
                        return self.dfm['state_changed_alert']
                    else:
                        self.download.status = Status.LOADING
                        self.download.status_message = u'Getting the torrent metadata'
                        client.getPage(str(self.download.url)).addCallback(self.fetch_torrent_success).addErrback(self.fetch_torrent_failure)
                return self.dfm['state_changed_alert']
            else:
                raise Exception('Torrent metadata missing and no source URL specified')
        else:
            return self.start_real()

    def start_real(self):
        if self.is_finished() and self.seed_requirement_met():
            # Restarting a finished torrent, don't autostop immediately
            self.autostop = False
        self.download.status = Status.STARTING
        self.download.status_message = None
        if not 'state_changed_alert' in self.dfm:
            self.dfm['state_changed_alert'] = defer.Deferred()
        if not self.torrent_info:
            self.torrent_info = lt.torrent_info(lt.bdecode(self.download.metadata))
            self.download.description = unicode(self.torrent_info.name())
        try:
            if not self.torrent:
                resdata = None
                if self.download.resume_data:
                    resdata = marshal.loads(self.download.resume_data)
                self.torrent = lt_manager.add_torrent(self, self.torrent_info, self.directory, resume_data=resdata)
                self.torrent.auto_managed(True)
            self.rebind()
        except Exception as e:
            dfr = self.dfm['state_changed_alert']
            del self.dfm['state_changed_alert']
            if self.torrent:
                self.torrent.auto_managed(False)
                self.torrent.pause()
                self.torrent.save_resume_data()
            dfr.errback(failure.Failure(e))
            return dfr
        self.torrent.resume()
        return self.dfm['state_changed_alert']

    def stop(self):
        if self.is_running():
            if self.download.status == Status.SEEDING:
                self.download.status = Status.COMPLETED
            if self.download.status != Status.COMPLETED:
                self.download.status = Status.STOPPING
            self.dfm['torrent_paused_alert'] = defer.Deferred()
            self.dfm['save_resume_data_alert'] = defer.Deferred()
            dl = defer.DeferredList((self.dfm['torrent_paused_alert'],
                                    self.dfm['save_resume_data_alert']),
                                    consumeErrors=True)
            # Call errback if it doesn't complete in a timely fashion
            reactor.callLater(5.0, self.handle_timeout, 'torrent_paused_alert')
            reactor.callLater(5.0, self.handle_timeout, 'save_resume_data_alert')
            if self.torrent:
                self.torrent.auto_managed(False)
                self.torrent.pause()
                self.torrent.save_resume_data()
            return dl
        else:
            return defer.succeed(True)

    def handle_timeout(self, alert_type):
        if alert_type in self.dfm:
            self.dfm[alert_type].errback(failure.Failure(defer.TimeoutError(alert_type)))
            del self.dfm[alert_type]

    def handle_alert(self, alert, alert_type):
        # logging.debug("TORRENT: %s: %s, %s" % (alert_type, alert.what(), alert.message()))
        if alert_type == 'torrent_resumed_alert':
            alert_type = 'state_changed_alert'
        if alert_type == 'torrent_finished_alert':
            self.download.status = Status.COMPLETED
            #self.download.status_message = None
            self.check_finished()
        elif alert_type == 'torrent_paused_alert':
            if alert.handle.is_valid():
                error = alert.handle.status().error
                if error:
                    self.torrent.auto_managed(False)
                    self.download.active = False
                    self.download.status = Status.FAILED
                    self.download.status_message = error
                    self.errback(failure.Failure(Exception(error)))
            self.update_status()
        elif alert_type == 'save_resume_data_alert':
            self.download.resume_data = marshal.dumps(alert.resume_data)
        elif alert_type == 'save_resume_data_failed_alert':
            self.download.resume_data = None
        elif alert_type == 'state_changed_alert':
            self.update_status()
        elif alert_type == 'tracker_error_alert':
            logging.debug("TORRENT: %s: %s, %s" % (alert_type, alert.what(), alert.message()))
            if 'Cannot assign requested address' in alert.message():
                self.rebind(True)
            self.update_status()

        elif alert_type == 'scrape_failed_alert':
            logging.debug("TORRENT: %s: %s, %s" % (alert_type, alert.what(), alert.message()))
            # Only alert I can find that provides warning of a network interface going down
            if 'Cannot assign requested address' in alert.message():
                self.rebind(True)

        if alert_type in self.dfm:
            self.dfm[alert_type].callback(self)
            del self.dfm[alert_type]

        return True

    def remove(self):
        self.dfm['state_changed_alert'] = defer.Deferred()
        if self.torrent:
            lt_manager.remove_torrent(self)
            self.torrent = None
        return self.dfm['state_changed_alert']

    def set_download_rate(self, rate):
        if rate != self.download_rate:
            lt_manager.limits_updated = True
        self.download_rate = rate

    def set_upload_rate(self, rate):
        if rate != self.upload_rate:
            lt_manager.limits_updated = True
        self.upload_rate = rate

    def set_max_connections(self, limit):
        if limit != self.max_connections:
            lt_manager.limits_updated = True
        self.max_connections = limit

    def get_files(self):
        files = []
        if self.torrent_info:
            fileprogress = None
            fileentries = self.torrent_info.files()
            if self.torrent:
                fileprogress = self.torrent.file_progress()
            for idx in range(0, len(fileentries)):
                file = fileentries[idx]
                progress = 0
                if fileprogress:
                    progress = (float(fileprogress[idx]) / file.size) * 100
                else:
                    dfile = '%s/%s' % (self.directory, file.path)
                    if os.access(dfile, os.R_OK):
                        dsize = os.path.getsize(dfile)
                        progress = (float(dsize) / file.size) * 100
                files.append({'path': file.path,
                              'size': file.size,
                              'progress': progress})
        files.sort(lambda x,y: cmp(x['path'], y['path']))
        return files

    def magnet_loaded(self, client):
        del self.dfm['metadata_failed_alert']
        if self.torrent.has_metadata():
            if self.download.status == Status.LOADING:
                self.download.status = Status.QUEUED
            self.torrent_info = self.torrent.get_torrent_info()
            self.download.status_message = None
            self.download.description = unicode(self.torrent_info.name())
            self.start_real()
        else:
            self.magnet_load_failed();

    def magnet_load_failed(self, failure):
        del self.dfm['metadata_received_alert']
        self.torrent.auto_managed(False)
        self.download.active = False
        self.download.status = Status.FAILED
        self.download.status_message = 'Failed to get metadata from magnet link'
        self.errback(failure.Failure(Exception(error)))

    def fetch_torrent_failure(self, failure):
        self.download.status = Status.FAILED
        self.download.status_message = unicode(failure.getErrorMessage())
        if 'state_changed_alert' in self.dfm:
            self.dfm['state_changed_alert'].errback(failure)
            del self.dfm['state_changed_alert']
    
    def fetch_torrent_success(self, data):
        if data:
            try:
                # Twisted doesn't give us encoding headers, so just try and see
                data = zlib.decompress(data, 15 + 32)
            except Exception as e:
                pass
            self.download.metadata = data
            self.download.status = Status.QUEUED
            self.download.status_message = None
            self.torrent_info = lt.torrent_info(lt.bdecode(self.download.metadata))
            self.download.description = unicode(self.torrent_info.name())
            self.start_real()

    def update_status(self):
        if self.torrent and self.torrent.is_valid():
            status = self.torrent.status()
            paused = self.torrent.is_paused()
            self.download.size = status.total_wanted
            self.download.downloaded = int(status.total_wanted_done)
            self.download.downloadrate = float(status.download_payload_rate)
            self.download.uploaded = int(status.all_time_upload)
            self.download.uploadrate = float(status.upload_payload_rate)
            self.download.elapsed = status.active_time
            self.download.connections = status.num_connections
            self.download.progress = status.progress * 100
            self.download.status_message = unicode(status.error)

            if self.download.downloaded > 0:
                ulratio = float(self.manager.get_setting('upload_ratio', 0))
                currratio = self.download.uploaded / self.download.downloaded
                uploadtarget = self.download.size * ulratio
                if uploadtarget > 0:
                    self.download.seed_progress = self.download.uploaded / uploadtarget
                else:
                    self.download.seed_progress = 100
            else:
                self.download.seed_progress = 0

            if self.download.downloadrate:
                if self.is_running() and self.download.progress == 100:
                    if self.autostop:
                        toupload = uploadtarget - self.download.uploaded
                        self.download.timeleft = toupload / self.download.downloadrate
                    else:
                        self.download.timeleft = -1
                else:
                    self.download.timeleft = (self.download.size - self.download.downloaded) / self.download.downloadrate
            else:
                self.download.timeleft = -1

            states = [Status.STARTING,
                      Status.STARTING,
                      Status.STARTING,
                      Status.RUNNING,
                      Status.COMPLETED,
                      Status.SEEDING,
                      Status.STARTING]

            tstate = states[status.state]
            if tstate == Status.SEEDING:
                self.check_finished()
                if paused:
                    tstate = Status.COMPLETED
            if self.download.active and not self.manager.paused:
                self.download.status = tstate

            # Calculate torrent health
            if tstate == Status.SEEDING:
                self.download.health = 100
            else:
                # Health points: 1 seed = 1pt
                hp = status.num_seeds
                # 10 available seeds = 1 pt
                hp = hp + divmod(status.list_seeds, 20)[0]
                copies = math.floor(status.distributed_copies - status.num_seeds)
                if copies > 0:
                    # Non-seed distributed copy = 1 pt
                    hp = hp + copies
                    # 10 peers = 1 pt
                    hp = hp + divmod(status.num_peers, 10)[0]
                    # 100 available peers = 1 pt
                    hp = hp + divmod(status.list_peers, 100)[0]
                # 50kb/s or more = 1 pt
                if status.download_payload_rate > 50:
                    hp = hp + 1
                # 5 points = 100% healthy
                health = hp * 20
                if health > 100:
                    health = 100
                self.download.health = health

    def check_finished(self):
        if self.autostop and self.seed_requirement_met():
            self.autostop = False
            self.stop()
            self.callback()

    def seed_requirement_met(self):
        ulratio = float(self.manager.get_setting('upload_ratio', 0))
        return (self.download.uploaded / self.download.downloaded) >= ulratio

    def get_extended_status(self, name):
        if self.torrent.is_valid():
            status = self.torrent.status()
            if hasattr(status, name):
                return getattr(status, name)
        return None
