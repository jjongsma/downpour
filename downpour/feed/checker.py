from downpour.core import models, organizer
from twisted.internet import threads
import feedparser, logging
from time import time, mktime, localtime
from datetime import datetime
from dateutil.parser import parse as parsedate
from storm import expr
import os, re

def check_feeds(manager):
    now = time()
    feeds = manager.store.find(models.Feed)
    toupdate = [f for f in feeds if (f.last_check is None or (f.update_frequency*60) + f.last_check < now)]
    if len(toupdate):
        update_feeds(toupdate, manager.application)

def update_feeds(feeds, application):
    if len(feeds):
        f = feeds.pop(0)
        modified = None
        if not f.modified is None:
            modified = localtime(f.modified)
        d = threads.deferToThread(feedparser.parse, f.url, etag=f.etag,
                modified=modified)
        manager = application.get_manager(f.user)
        d.addCallback(feed_parsed, feeds, manager, f)
        d.addErrback(feed_parse_failed, feeds, manager, f)

def feed_parsed(parsed, feeds, manager, feed):

    logging.debug('Updating feed "%s" (%s)' % (feed.name, feed.url))

    # Update etag/lastmod for future requests
    feed.last_error = None
    feed.last_check = time()
    if 'modified' in parsed:
        feed.modified = mktime(parsed.modified)
    if 'etag' in parsed:
        feed.etag = unicode(parsed.etag)
    manager.store.commit()

    # Check entries for new downloads
    items = parsed.entries
    if feed.save_priority == '1':
        items.reverse()

    has_new = False
    item_count = 0
    latest_season = 1
    latest_episode = 1
    seen_items = []

    # Prime previously-seen item map to avoid duplicate downloads
    pastitems = manager.store.find(models.FeedItem,
        models.FeedItem.feed_id == feed.id)
    for pi in pastitems:
        epdef = get_episode_definition(pi)
        seen_items.append(epdef)
        if epdef['s'] and int(epdef['s']) > latest_season:
            latest_season = int(epdef['s'])
            latest_episode = 1
        if epdef['s'] and int(epdef['s']) == latest_season:
            if epdef['e'] and int(epdef['e']) > latest_episode:
                latest_episode = int(epdef['e'])

    for e in items:
        do_update = False
        updated = mktime(e.updated_parsed)
        season = 0

        item = manager.store.find(models.FeedItem,
            models.FeedItem.feed_id == feed.id,
            models.FeedItem.guid == e.id).one()

        # Check for enclosures
        link = e.link
        size = 0
        mimetype = None
        if 'enclosures' in e and len(e.enclosures):
            link = e.enclosures[0].href
            size = int(e.enclosures[0].length)
            mimetype = e.enclosures[0].type

        # New item
        if not item:
            do_update = True
            item = models.FeedItem()
            item.feed_id = feed.id
            item.guid = e.id
            item.removed = False
            manager.store.add(item)
            manager.application.fire_event('feed_item_added', item)

        if do_update or item.updated != updated:
            # Updated with new download link, re-add
            if item.link != e.link:
                do_update = True
            item.updated = updated
            item.title = e.title
            item.link = link
            if 'content' in e:
                item.content = e.content[0].value

        if not feed.active:
            do_update = False

        if do_update:
            # Check existing library for matching episode
            ed = get_episode_definition(item)
            if seen(ed, seen_items):
                # Prevent downloading duplicate items
                do_update = False
            else:
                seen_items.append(ed)
                pattern = feed.rename_pattern
                if not pattern:
                    lib = manager.get_library(media_type=feed.media_type)
                    if lib:
                        pattern = lib.pattern
                if not pattern:
                    pattern = '%p'
                if ed['e'] or ed['d']:
                    if ed['s'] and feed.queue_size < 0:
                        season = int(ed['s'])
                        if season > latest_season:
                            latest_season = season
                        elif season > 0 and season < (latest_season + feed.queue_size):
                            do_update = False
                    destfile = organizer.pattern_replace(pattern, ed)
                    destdir = manager.get_full_path(os.path.dirname(destfile),
                        feed.media_type)
                    if do_update and os.access(destdir, os.R_OK):
                        for e in os.listdir(destdir):
                            ed2 = organizer.get_metadata('%s/%s' % (destdir, e), feed)
                            if ed['z'] == feed.name:
                                # Match season/episode
                                if ed['e'] and \
                                        ed['e'] == ed2['e'] and \
                                        ed['s'] == ed2['s']:
                                    do_update = False
                                    break
                                # Match date
                                elif ed['d'] and \
                                        ed['d'] == ed2['d']:
                                    do_update = False
                                    break

        if do_update:
            has_new = True
            d = models.Download()
            d.feed_id = feed.id
            d.user_id = feed.user_id
            d.url = item.link
            d.size = size
            d.mime_type = mimetype
            d.description = item.title
            d.media_type = feed.media_type
            item.download = d
            manager.add_download(d)

        item_count += 1
        if feed.queue_size > 0 and item_count >= feed.queue_size:
            break;

    if has_new:
        manager.application.fire_event('feed_updated', feed)
        if 'modified' in parsed:
            feed.last_update = mktime(parsed.modified)
        else:
            feed.last_update = time()

    manager.store.commit()

    # Process the next feed
    if len(feeds):
        update_feeds(feeds, manager.application)

# Remove old feed downloads after a successful download
def clean_download_feed(d, app):

    if d.feed and d.feed.queue_size != 0:

        manager = app.get_manager(d.user)

        feed = d.feed

        items = manager.store.find(models.FeedItem,
            models.FeedItem.feed_id == feed.id,
            models.FeedItem.removed == False
            ).order_by(expr.Desc(models.FeedItem.updated))

        remove = []

        if feed.queue_size > 0:
            episodect = 0
            last_season = 0
            last_date = ''
            last_episode = 0
            for i in items:
                if i.download:
                    ed = get_episode_definition(i)
                    if ed['s'] is not None and ed['e'] is not None:
                        if last_season != int(ed['s']) and last_episode != int(ed['e']):
                            episodect = episodect + 1
                            if episodect > feed.queue_size:
                                remove.append(i)
                        else:
                            last_season = int(ed['s'])
                            last_episode = int(ed['e'])
                            i.removed = True
                    elif ed['d'] is not None:
                        if last_date != ed['d']:
                            episodect = episodect + 1
                            if episodect > feed.queue_size:
                                remove.append(i)
                        else:
                            last_date = ed['d']
                            i.removed = True
                    else:
                        episodect = episodect + 1
                        if episodect > feed.queue_size:
                            remove.append(i)
                else:
                    i.removed = True

        elif feed.queue_size < 0:
            for i in items:
                if i.download:
                    ed = get_episode_definition(i)
                    if (ed['s']):
                        season = int(ed['s'])
                        if season > 0 and season < (latest_season + (feed.queue_size + 1)):
                            remove.append(i)
                else:
                    i.removed = True

        for i in remove:
            manager.application.fire_event('feed_item_removed', i)
            logging.debug('Removing old feed item %d (%s)' % (i.id, i.title))
            for f in i.download.files:
                realdir = '/'.join(
                    (manager.get_library_directory(), f.directory))
                realpath = '/'.join((realdir, f.filename))
                if organizer.remove_file(realpath, True):
                    i.download.files.remove(f)
                    manager.application.fire_event('library_file_removed', realpath, i.download)
            i.removed = True

        manager.store.commit()

def seen(m, items):
    for i in items:
        if m['e']:
            if m['e'] == i['e'] and m['s'] == i['s']:
                return True
        elif m['d']:
            if m['d'] == i['d']:
                return True
    return False

def get_episode_definition(item):
    ed = { 'd': None, 's': None, 'e': None, 'z': item.feed.name }
    rl = (
        re.compile(r's(?P<s>[0-9]{1,2})\W?e(?P<e>[0-9]{1,2})', re.IGNORECASE),
        re.compile(r'(?P<s>[0-9]{1,2})x(?P<e>[0-9]{1,2})', re.IGNORECASE),
        re.compile(r'(?P<d>[0-9\-\.]{8,})', re.IGNORECASE)
    )
    for r in rl:
        match = r.search(item.link)
        if match:
            ed.update(match.groupdict())
        else:
            match = r.search(item.title)
            if match:
                ed.update(match.groupdict())
    if ed['d']:
        try:
            ed['d'] = parsedate(ed['d']).strftime('%Y-%m-%d')
        except Exception:
            ed['d'] = None
    return ed

def feed_parse_failed(failure, feeds, manager, feed):
    #print failure
    feed.last_update = time()
    feed.last_error = unicode(failure.getErrorMessage())
    manager.store.commit()

    if len(feeds):
        update_feeds(feeds, manager.application)
