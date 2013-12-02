from downpour2.core.store import patches
from storm.schema.schema import Schema

class DownpourSchema(Schema):

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

        "CREATE TABLE remote_shares (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "address TEXT," +
            "username TEXT," +
            "password TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE TABLE options (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "value TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE TABLE libraries (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "media_type TEXT," +
            "directory TEXT," +
            "pattern TEXT," +
            "keepall BOOLEAN," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

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
        "CREATE INDEX downloads_deleted on downloads(deleted)",

        "CREATE TABLE feed_items (" +
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
            ")",

        "CREATE INDEX feed_items_updated on feed_items(updated)",
        "CREATE INDEX feed_items_removed on feed_items(removed)",

        "CREATE TABLE files (" +
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
            ")",

        "INSERT INTO state(name, value) VALUES ('paused', '0')",

        # Initial admin user
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)"

    ]

    drop_statements = [
        "DROP TABLE state",
        "DROP TABLE settings",
        "DROP TABLE users",
        "DROP TABLE remote_shares",
        "DROP TABLE options",
        "DROP TABLE libraries",
        "DROP TABLE feeds",
        "DROP TABLE downloads",
        "DROP TABLE feed_items",
        "DROP TABLE files"
    ]

    delete_statements = [
        "DELETE FROM state",
        "DELETE FROM settings",
        "DELETE FROM users",
        "DELETE FROM remote_shares",
        "DELETE FROM options",
        "DELETE FROM libraries",
        "DELETE FROM feeds",
        "DELETE FROM downloads",
        "DELETE FROM feed_items",
        "DELETE FROM files",
        "INSERT INTO state(name, value) VALUES ('paused', '0')",
        "INSERT INTO users(username, password, admin) VALUES ('admin', 'password', 1)"
    ]

    def __init__(self):
        super(DownpourSchema, self).__init__(DownpourSchema.create_statements,
            DownpourSchema.drop_statements, DownpourSchema.delete_statements, patches)
