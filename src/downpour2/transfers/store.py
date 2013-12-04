import os
from downpour2.core.store import schema
from downpour2.transfers import patches

def update_store(store):
    TransferSchema().upgrade(store)

class TransferSchema(schema.Schema):

    create_statements = [

        "CREATE TABLE downloads (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "feed_id INTEGER," +
            "url TEXT," +
            "filename TEXT," +
            "media_type TEXT," +
            "mime_type TEXT," +
            "description TEXT," +
            "metadata BLOB," +
            "info_hash BLOB," +
            "resume_data BLOB," +
            "active BOOLEAN," +
            "status INTEGER," +
            "status_message TEXT," +
            "progress REAL," +
            "size REAL," +
            "downloaded REAL," +
            "uploaded REAL," +
            "added INTEGER," +
            "started INTEGER," +
            "completed INTEGER," +
            "deleted BOOLEAN," +
            "imported BOOLEAN," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,"
            "FOREIGN KEY(feed_id) REFERENCES feeds(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE INDEX downloads_completed on downloads(completed)",
        "CREATE INDEX downloads_deleted on downloads(deleted)"

    ]

    drop_statements = [
        "DROP TABLE downloads"
    ]

    delete_statements = [
        "DELETE FROM downloads"
    ]

    def __init__(self):
        super(TransferSchema, self).__init__(TransferSchema.create_statements,
            TransferSchema.drop_statements, TransferSchema.delete_statements, patches)

class Download(object):

    __storm_table__ = 'downloads'

    id = Int(primary=True)
    user_id = Int()
    feed_id = Int()
    url = Unicode()
    filename = Unicode()
    media_type = Unicode()
    mime_type = Unicode()
    description = Unicode()
    metadata = RawStr()
    info_hash = RawStr()
    resume_data = RawStr()
    active = Bool()
    status = Int()
    status_message = Unicode()
    progress = Float()
    size = Int()
    downloaded = Int()
    uploaded = Int()
    added = Int()
    started = Int()
    completed = Int()
    deleted = Bool()
    imported = Bool()

    user = Reference(user_id, User.id)
    feed = Reference(feed_id, Feed.id)

    # Non-persistent fields
    health = 0
    uploadrate = 0
    downloadrate = 0
    connections = 0
    elapsed = 0
    timeleft = 0
    importing = False

