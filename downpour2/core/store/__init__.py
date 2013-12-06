import os
from storm.locals import *
from downpour2.core.store import schema, sqlitefk, patches

def get_store(config=None):

    db_path = os.path.expanduser(config.value(('downpour', 'state')))

    if not os.access(db_path, os.F_OK):
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir);

    database = create_database('sqlite:%s' % db_path)
    store = Store(database)

    CoreSchema().upgrade(store)

    return store;

class CoreSchema(schema.Schema):

    create_statements = [

        "CREATE TABLE state (" +
            "id INTEGER PRIMARY KEY," +
            "name TEXT," +
            "value TEXT" +
            ")",

        "CREATE TABLE settings (" +
            "id INTEGER PRIMARY KEY," +
            "name TEXT," +
            "value TEXT" +
            ")",

        "CREATE TABLE users (" +
            "id INTEGER PRIMARY KEY," +
            "username TEXT," +
            "password TEXT," +
            "email TEXT," +
            "directory TEXT," +
            "max_downloads INTEGER," +
            "max_rate INTEGER," +
            "share_enabled BOOLEAN," +
            "share_password TEXT," +
            "share_max_rate INTEGER," +
            "admin BOOLEAN" +
            ")",

        "CREATE TABLE options (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "value TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "INSERT INTO state(name, value) VALUES ('paused', '0')",

        # Initial admin user
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)"

    ]

    drop_statements = [
        "DROP TABLE state",
        "DROP TABLE settings",
        "DROP TABLE users",
        "DROP TABLE options"
    ]

    delete_statements = [
        "DELETE FROM state",
        "DELETE FROM settings",
        "DELETE FROM users",
        "DELETE FROM options",
        "INSERT INTO state(name, value) VALUES ('paused', '0')",
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)"
    ]

    def __init__(self):
        super(CoreSchema, self).__init__(CoreSchema.create_statements,
            CoreSchema.drop_statements, CoreSchema.delete_statements, patches)

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
