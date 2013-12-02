def apply(store):
    store.execute("CREATE INDEX downloads_completed on downloads(completed)")
    store.execute("CREATE INDEX downloads_deleted on downloads(deleted)")
    store.execute("CREATE INDEX feed_items_updated on feed_items(updated)")
    store.execute("CREATE INDEX feed_items_removed on feed_items(removed)")
