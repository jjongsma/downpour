def apply(store):
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
