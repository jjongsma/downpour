from storm.locals import *
from downpour2.core.store import schema, User, Transfer
from downpour2.feeds import patches

def update_store(store):
    FeedSchema().upgrade(store, checkTable='feeds')

class FeedSchema(schema.Schema):

    create_statements = [

        "CREATE TABLE feeds (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "url TEXT," +
            "media_type TEXT," +
            "etag TEXT," +
            "modified INTEGER," +
            "active BOOLEAN," +
            "auto_clean BOOLEAN," +
            "last_update INTEGER," +
            "last_check INTEGER," +
            "last_error TEXT," +
            "update_frequency INTEGER," +
            "queue_size INTEGER," +
            "save_priority INTEGER," +
            "download_directory TEXT," +
            "rename_pattern TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE TABLE feed_items (" +
            "id INTEGER PRIMARY KEY," +
            "feed_id INTEGER," +
            "transfer_id INTEGER," +
            "guid TEXT," +
            "title TEXT," +
            "link TEXT," +
            "updated INTEGER," +
            "content TEXT," +
            "removed BOOLEAN," +
            "FOREIGN KEY(feed_id) REFERENCES feeds(id) ON DELETE CASCADE ON UPDATE CASCADE,"
            "FOREIGN KEY(transfer_id) REFERENCES transfers(id) ON DELETE SET NULL ON UPDATE CASCADE"
            ")",

        "CREATE INDEX feed_items_updated on feed_items(updated)",
        "CREATE INDEX feed_items_removed on feed_items(removed)"

    ]

    drop_statements = [
        "DROP TABLE feed_items",
        "DROP TABLE feeds"
    ]

    delete_statements = [
        "DELETE FROM feed_items",
        "DELETE FROM feeds"
    ]

    def __init__(self):
        super(FeedSchema, self).__init__(FeedSchema.create_statements,
            FeedSchema.drop_statements, FeedSchema.delete_statements, patches)

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
    transfer_id = Int()
    removed = Bool()
    guid = Unicode()
    title = Unicode()
    link = Unicode()
    updated = Int()
    content = Unicode()

    feed = Reference(feed_id, Feed.id)
    transfer = Reference(transfer_id, Transfer.id)

Feed.items = ReferenceSet(Feed.id, FeedItem.feed_id)
