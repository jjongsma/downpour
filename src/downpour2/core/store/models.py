from storm.locals import *

class RemoteShare(object):

    __storm_table__ = 'remote_shares'

    id = Int(primary=True)
    user_id = Int()
    name = Unicode()
    address = Unicode()
    username = Unicode()
    password = Unicode()

    user = Reference(user_id, User.id)

class Library(object):

    __storm_table__ = 'libraries'

    id = Int(primary=True)
    user_id = Int()
    media_type = Unicode()
    directory = Unicode()
    pattern = Unicode()
    keepall = Bool()

    user = Reference(user_id, User.id)

class Feed(object):

    __storm_table__ = 'feeds'

    id = Int(primary=True)
    user_id = Int()
    name = Unicode()
    url = Unicode()
    media_type = Unicode()
    etag = Unicode()
    modified = Int()
    active = Bool()
    auto_clean = Bool()
    last_check = Int()
    last_update = Int()
    last_error = Unicode()
    update_frequency = Int()
    queue_size = Int()
    save_priority = Int()
    download_directory = Unicode()
    rename_pattern = Unicode()

    user = Reference(user_id, User.id)

class FeedItem(object):

    __storm_table__ = 'feed_items'

    id = Int(primary=True)
    feed_id = Int()
    download_id = Int()
    removed = Bool()
    guid = Unicode()
    title = Unicode()
    link = Unicode()
    updated = Int()
    content = Unicode()

    feed = Reference(feed_id, Feed.id)
    download = Reference(download_id, Download.id)

Feed.items = ReferenceSet(Feed.id, FeedItem.feed_id)

class File(object):

    __storm_table__ = 'files'

    id = Int(primary=True)
    user_id = Int()
    directory = Unicode()
    filename = Unicode()
    size = Int()
    media_type = Unicode()
    mime_type = Unicode()
    download_id = Int()
    original_filename = Unicode()
    description = Unicode()
    added = Int()

    user = Reference(user_id, User.id)
    download = Reference(download_id, Download.id)

Download.files = ReferenceSet(Download.id, File.download_id)
