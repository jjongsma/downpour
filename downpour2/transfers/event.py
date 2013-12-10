from fysom import Fysom
import mimetypes, logging

# Upload / download
ADDED = 'transfer_added'
ENQUEUE = 'transfer_enqueue'
START = 'transfer_start'
INITIALIZED = 'transfer_initialized'
STARTED = 'transfer_started'
COMPLETE = 'transfer_complete'
STOP = 'transfer_stop'
STOPPED = 'transfer_stopped'
FAILED = 'transfer_failed'
REMOVE = 'transfer_remove'

# Download only
FETCHED = 'transfer_fetched'
FETCH_FAILED = 'transfer_fetch_failed'
IMPORTED = 'transfer_imported'
IMPORT_FAILED = 'transfer_import_failed'
SEEDED = 'transfer_seed_complete'

class TransferFlow(Fysom):

    def __init__(self, transfer, application, rules):

        super(TransferFlow, self).__init__(rules)

        self.transfer = transfer
        self.application = application

    def onchangestate(self, e):

        self.transfer.state = e.dst
        self.application.store.commit()

        # Specific state transition handlers
        transition = 'on%sto%s' % (e.src, e.dst)
        if hasattr(self, transition) and callable(getattr(self, transition)):
            getattr(self, transition)(e)

        self.application.events.fire(e.event, self.transfer)

class DownloadFlow(TransferFlow):

    def __init__(self, transfer, application):

        super(DownloadFlow, self).__init__(transfer, application, {
            'initial': State.QUEUED,
            'events': [
                # Start download
                {'src': State.QUEUED, 'name': START, 'dst': State.INITIALIZING},
                {'src': State.INITIALIZING, 'name': INITIALIZED, 'dst': State.STARTING},
                {'src': State.STARTING, 'name': STARTED, 'dst': State.TRANSFERRING},
                # Download paused
                {'src': State.TRANSFERRING, 'name': STOP, 'dst': State.STOPPING},
                {'src': State.STOPPING, 'name': STOPPED, 'dst': State.STOPPED},
                # Download resumed
                {'src': State.STOPPED, 'name': ENQUEUE, 'dst': State.QUEUED},
                {'src': [ State.STOPPED, State.FAILED ], 'name': START, 'dst': State.INITIALIZING},
                # Download completed/failed
                {'src': State.TRANSFERRING, 'name': FAILED, 'dst': State.FAILED},
                {'src': State.TRANSFERRING, 'name': COMPLETE, 'dst': State.COPYING},
                # Fetch files from agent
                {'src': State.COPYING, 'name': FETCH_FAILED, 'dst': State.PENDING_COPY},
                {'src': State.COPYING, 'name': STOP, 'dst': State.PENDING_COPY},
                {'src': State.PENDING_COPY, 'name': START, 'dst': State.COPYING},
                {'src': State.COPYING, 'name': FETCHED, 'dst': State.IMPORTING},
                # Import to library
                {'src': State.IMPORTING, 'name': IMPORT_FAILED, 'dst': State.PENDING_IMPORT},
                {'src': State.IMPORTING, 'name': STOP, 'dst': State.PENDING_IMPORT},
                {'src': State.PENDING_IMPORT, 'name': START, 'dst': State.IMPORTING},
                {'src': State.IMPORTING, 'name': IMPORTED, 'dst': State.SEEDING},
                # Completed
                {'src': State.SEEDING, 'name': SEEDED, 'dst': State.COMPLETED},
                # Remove from queue
                {'src': [ State.TRANSFERRING, State.SEEDING ], 'name': REMOVE, 'dst': State.REMOVING},
                {'src': State.REMOVING, 'name': STOPPED, 'dst': State.REMOVED},
                {'src': [ State.QUEUED, State.FAILED, State.COMPLETED, State.PENDING_COPY,
                    State.PENDING_IMPORT ], 'name': REMOVE, 'dst': State.REMOVED},
            ]
        }); 

class UploadFlow(TransferFlow):

    def __init__(self, transfer, application):

        super(UploadFlow, self).__init__(transfer, application, {
            'initial': State.QUEUED,
            'events': [
                # Start upload
                {'src': State.QUEUED, 'name': START, 'dst': State.INITIALIZING},
                {'src': State.INITIALIZING, 'name': INITIALIZED, 'dst': State.STARTING},
                {'src': State.STARTING, 'name': STARTED, 'dst': State.TRANSFERRING},
                # Upload paused
                {'src': State.TRANSFERRING, 'name': STOP, 'dst': State.STOPPING},
                {'src': State.STOPPING, 'name': STOPPED, 'dst': State.STOPPED},
                # Upload completed/failed
                {'src': State.TRANSFERRING, 'name': FAILED, 'dst': State.FAILED},
                {'src': State.TRANSFERRING, 'name': COMPLETE, 'dst': State.COMPLETED},
                # Remove from queue
                {'src': State.TRANSFERRING, 'name': REMOVE, 'dst': State.REMOVING},
                {'src': State.REMOVING, 'name': STOPPED, 'dst': State.REMOVED},
                {'src': [ State.FAILED, State.COMPLETED ], 'name': REMOVE, 'dst': State.REMOVED},
            ]
        }); 

class State:

    QUEUED = 'queued'
    INITIALIZING = 'initializing'
    STARTING = 'starting'
    TRANSFERRING = 'transferring'
    COPYING = 'copying'
    PENDING_COPY = 'pendingcopy'
    IMPORTING = 'importing'
    PENDING_IMPORT = 'pendingimport'
    COMPLETED = 'completed'
    SEEDING = 'seeding'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    FAILED = 'failed'
    REMOVING = 'removing'
    REMOVED = 'removed'
