import os
from storm.locals import *
from storm.properties import Int, Unicode, RawStr, Float, Bool
from storm.references import Reference
from downpour2.core.store import schema, sqlitefk, patches


def make_store(config=None):
    db_path = os.path.expanduser(config.value(('downpour', 'state')))

    if not os.access(db_path, os.F_OK):
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    database = create_database('sqlite:%s' % db_path)
    store = Store(database)

    CoreSchema().upgrade(store)

    return store


class CoreSchema(schema.Schema):
    create_statements = [

        "CREATE TABLE state (" +
        "   id INTEGER PRIMARY KEY," +
        "   name TEXT," +
        "   value TEXT" +
        ")",

        "CREATE TABLE settings (" +
        "   id INTEGER PRIMARY KEY," +
        "   name TEXT," +
        "   value TEXT" +
        ")",

        "CREATE TABLE users (" +
        "   id INTEGER PRIMARY KEY," +
        "   username TEXT," +
        "   password TEXT," +
        "   email TEXT," +
        "   directory TEXT," +
        "   max_downloads INTEGER," +
        "   max_rate INTEGER," +
        "   share_enabled BOOLEAN," +
        "   share_password TEXT," +
        "   share_max_rate INTEGER," +
        "   admin BOOLEAN" +
        ")",

        "CREATE TABLE options (" +
        "   id INTEGER PRIMARY KEY," +
        "   user_id INTEGER," +
        "   name TEXT," +
        "   value TEXT," +
        "   FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")",

        "CREATE TABLE alerts (" +
        "   id INTEGER PRIMARY KEY," +
        "   user_id INTEGER," +
        "   timestamp INTEGER," +
        "   title TEXT," +
        "   level TEXT," +
        "   description TEXT," +
        "   url TEXT," +
        "   viewed BOOLEAN," +
        "   FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")",

        "CREATE TABLE transfers (" +
        "   id INTEGER PRIMARY KEY," +
        "   user_id INTEGER," +
        "   remote_id INTEGER," +
        "   url TEXT," +
        "   filename TEXT," +
        "   media_type TEXT," +
        "   mime_type TEXT," +
        "   description TEXT," +
        "   metadata BLOB," +
        "   info_hash BLOB," +
        "   resume_data BLOB," +
        "   priority INTEGER," +
        "   bandwidth REAL," +
        "   seed_ratio REAL," +
        "   seed_until INTEGER," +
        "   state TEXT," +
        "   status TEXT," +
        "   progress REAL," +
        "   size REAL," +
        "   downloaded REAL," +
        "   uploaded REAL," +
        "   added INTEGER," +
        "   started INTEGER," +
        "   completed INTEGER," +
        "   removed BOOLEAN," +
        "   FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")",

        "CREATE INDEX transfers_completed on transfers(completed)",
        "CREATE INDEX transfers_removed on transfers(removed)",
        "CREATE INDEX transfers_remote_id on transfers(remote_id)",

        # Initial admin user
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)"

    ]

    drop_statements = [
        "DROP TABLE state",
        "DROP TABLE settings",
        "DROP TABLE users",
        "DROP TABLE options",
        "DROP TABLE transfers"
    ]

    delete_statements = [
        "DELETE FROM state",
        "DELETE FROM settings",
        "DELETE FROM users",
        "DELETE FROM options",
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)",
        "DELETE FROM transfers"
    ]

    def __init__(self):
        super(CoreSchema, self).__init__(
            CoreSchema.create_statements,
            CoreSchema.drop_statements,
            CoreSchema.delete_statements,
            patches)


class State(object):
    __storm_table__ = 'state'

    id = Int(primary=True)
    name = Unicode()
    value = Unicode()


class Setting(object):
    __storm_table__ = 'settings'

    id = Int(primary=True)
    name = Unicode()
    value = Unicode()


class User(object):
    __storm_table__ = 'users'

    id = Int(primary=True)
    username = Unicode()
    password = Unicode()
    email = Unicode()
    directory = Unicode()
    max_downloads = Int()
    max_rate = Int()
    share_enabled = Bool()
    share_password = Unicode()
    share_max_rate = Int()
    admin = Bool()


class Option(object):
    __storm_table__ = 'options'

    id = Int(primary=True)
    user_id = Int()
    name = Unicode()
    value = Unicode()

    user = Reference(user_id, User.id)


class Alert(object):
    __storm_table__ = 'alerts'

    id = Int(primary=True)
    user_id = Int()
    timestamp = Int()
    title = Unicode()
    level = Unicode()
    description = Unicode()
    url = Unicode()
    viewed = Bool()

    user = Reference(user_id, User.id)


class Transfer(object):
    __storm_table__ = 'transfers'

    id = Int(primary=True)
    user_id = Int()
    remote_id = Int()
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
    connection_limit = 0
    elapsed = 0
    timeleft = 0
    client = None


def cleanup(store):
    pass
