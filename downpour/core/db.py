from downpour.core import models, sqlitefk, VERSION
from storm.locals import *
import logging
#import sys
#from storm.tracer import debug
#debug(True, stream=sys.stdout)

def initialize_db(store):

    store.execute("CREATE TABLE state (" +
        "id INTEGER PRIMARY KEY," +
        "name TEXT," +
        "value TEXT" +
        ")")

    store.execute("CREATE TABLE settings (" +
        "id INTEGER PRIMARY KEY," +
        "name TEXT," +
        "value TEXT" +
        ")")

    store.execute("CREATE TABLE users (" +
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
        ")")

    store.execute("CREATE TABLE remote_shares (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "name TEXT," +
        "address TEXT," +
        "username TEXT," +
        "password TEXT," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE options (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "name TEXT," +
        "value TEXT," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE libraries (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "media_type TEXT," +
        "directory TEXT," +
        "pattern TEXT," +
        "keepall BOOLEAN," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("CREATE TABLE feeds (" +
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
        ")")

    store.execute("CREATE TABLE downloads (" +
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
        ")")

    store.execute("CREATE INDEX downloads_completed on downloads(completed)")
    store.execute("CREATE INDEX downloads_deleted on downloads(deleted)")

    store.execute("CREATE TABLE feed_items (" +
        "id INTEGER PRIMARY KEY," +
        "feed_id INTEGER," +
        "download_id INTEGER," +
        "guid TEXT," +
        "title TEXT," +
        "link TEXT," +
        "updated INTEGER," +
        "content TEXT," +
        "removed BOOLEAN," +
        "FOREIGN KEY(feed_id) REFERENCES feeds(id) ON DELETE CASCADE ON UPDATE CASCADE,"
        "FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE SET NULL ON UPDATE CASCADE"
        ")")

    store.execute("CREATE INDEX feed_items_updated on feed_items(updated)")
    store.execute("CREATE INDEX feed_items_removed on feed_items(removed)")

    store.execute("CREATE TABLE files (" +
        "id INTEGER PRIMARY KEY," +
        "user_id INTEGER," +
        "directory TEXT," +
        "filename TEXT," +
        "size INTEGER," +
        "media_type TEXT," +
        "mime_type TEXT," +
        "download_id INTEGER," +
        "original_filename TEXT," +
        "description TEXT," +
        "added INTEGER," +
        "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,"
        "FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE CASCADE ON UPDATE CASCADE"
        ")")

    store.execute("INSERT INTO state(name, value) VALUES ('schema_version', '%s')" % VERSION)
    store.execute("INSERT INTO state(name, value) VALUES ('paused', '0')")

    # Initial admin user
    store.execute("INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)")
    store.execute("INSERT INTO users(username, password, admin) VALUES ('user', 'password', 0)")

    store.commit()

def upgrade_database(application):
    version = application.get_store().find(models.State,
        models.State.name == u'schema_version').one().value
    if version != VERSION and VERSION in schema_upgraders:
        return schema_upgraders[VERSION](application, version)
    return False

def upgrade_to_0_2_1(application, version):
    upgraded = True
    if version != '0.2':
        upgraded = upgrade_to_0_2(application, version)
    if upgraded:
        logging.info('Upgrading database from v0.2 to v0.2.1')
        store = application.get_store()
        store.execute("ALTER TABLE users ADD COLUMN share_enabled BOOLEAN")
        store.execute("ALTER TABLE users ADD COLUMN share_password TEXT")
        store.execute("ALTER TABLE users ADD COLUMN share_max_rate INTEGER")
        store.execute("CREATE TABLE remote_shares (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "address TEXT," +
            "username TEXT," +
            "password TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")")

        store.execute("UPDATE STATE SET value = '0.2.1' WHERE name = 'schema_version'")
    return upgraded

def upgrade_to_0_2(application, version):
    upgraded = True
    if version != '0.1.1':
        upgraded = upgrade_to_0_1_1(application, version)
    if upgraded:
        logging.info('Upgrading database from v0.1.1 to v0.2')
        store = application.get_store()
        store.execute("CREATE INDEX downloads_completed on downloads(completed)")
        store.execute("CREATE INDEX downloads_deleted on downloads(deleted)")
        store.execute("CREATE INDEX feed_items_updated on feed_items(updated)")
        store.execute("CREATE INDEX feed_items_removed on feed_items(removed)")
        store.execute("UPDATE STATE SET value = '0.2' WHERE name = 'schema_version'")
    return upgraded

def upgrade_to_0_1_1(application, version):
    upgraded = True
    if version != '0.1.1pre':
        upgraded = upgrade_to_0_1_1pre(application, version)
    if upgraded:
        logging.info('Upgrading database from v0.1.1pre to v0.1.1')
        application.get_store().execute("UPDATE STATE SET value = '0.1.1' WHERE name = 'schema_version'")
        pass
    return upgraded

def upgrade_to_0_1_1pre(application, version):
    if version != '0.1':
        return False
    logging.info('Upgrading database from v0.1 to v0.1.1pre')
    application.get_store().execute("UPDATE STATE SET value = '0.1.1pre' WHERE name = 'schema_version'")
    return True

# Add new upgraders to this dict
schema_upgraders = {
    '0.2.1': upgrade_to_0_2_1,
    '0.2': upgrade_to_0_2,
    '0.1.1': upgrade_to_0_1_1,
    '0.1.1pre': upgrade_to_0_1_1pre
}
