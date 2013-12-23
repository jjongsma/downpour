import os
from storm.locals import *
from downpour2.core.store import schema, User
from downpour2.transfers import patches

def update_store(store):
    TransferSchema().upgrade(store, checkTable='transfers')

class TransferSchema(schema.Schema):

    create_statements = [

        "CREATE TABLE transfers (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "url TEXT," +
            "filename TEXT," +
            "media_type TEXT," +
            "mime_type TEXT," +
            "description TEXT," +
            "metadata BLOB," +
            "info_hash BLOB," +
            "resume_data BLOB," +
            "priority INTEGER," +
            "bandwidth REAL," +
            "seed_ratio REAL," +
            "seed_until INTEGER," +
            "state TEXT," +
            "status TEXT," +
            "progress REAL," +
            "size REAL," +
            "downloaded REAL," +
            "uploaded REAL," +
            "added INTEGER," +
            "started INTEGER," +
            "completed INTEGER," +
            "removed BOOLEAN," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE INDEX transfers_completed on transfers(completed)",
        "CREATE INDEX transfers_removed on transfers(removed)"

    ]

    drop_statements = [
        "DROP TABLE transfers"
    ]

    delete_statements = [
        "DELETE FROM transfers"
    ]

    def __init__(self):
        super(TransferSchema, self).__init__(TransferSchema.create_statements,
            TransferSchema.drop_statements, TransferSchema.delete_statements, patches)

class Transfer(object):

    __storm_table__ = 'transfers'

    id = Int(primary=True)
    user_id = Int()
    url = Unicode()
    filename = Unicode()
    media_type = Unicode()
    mime_type = Unicode()
    description = Unicode()
    ## Torrent only - put somewhere else?
    metadata = RawStr()
    info_hash = RawStr()
    resume_data = RawStr()
    ## End torrent only
    priority = Int()
    bandwidth = Float()
    seed_ratio = Float()
    seed_until = Int()
    state = Int()
    status = Unicode()
    progress = Float()
    size = Int()
    downloaded = Int()
    uploaded = Int()
    added = Int()
    started = Int()
    completed = Int()
    removed = Bool()

    user = Reference(user_id, User.id)

    # Non-persistent fields
    health = 0
    uploadrate = 0
    downloadrate = 0
    connections = 0
    elapsed = 0
    timeleft = 0
