from fysom import Fysom

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

class DownloadFlow(Fysom):

    def __init__(self, transfer, application):

        self.transfer = transfer
        self.application = application

        super(TransferFlow, self).__init__({
            'initial': State.QUEUED,
            'events': [
                # Start download
                {'name': START, 'src': State.QUEUED, 'dst': State.INITIALIZING},
                {'name': INITIALIZED, 'src': State.INITIALIZING, 'dst': State.STARTING},
                {'name': STARTED, 'src': State.STARTING, 'dst': State.TRANSFERRING},
                # Download paused
                {'name': STOP, 'src': State.TRANSFERRING, 'dst': State.STOPPING},
                {'name': STOPPED, 'src': State.STOPPING, 'dst': State.STOPPED},
                # Download resumed
                {'name': ENQUEUE, 'src': State.STOPPED, 'dst': State.QUEUED},
                {'name': START, 'src': [ State.STOPPED, State.FAILED ],
                    'dst': State.INITIALIZING},
                # Download completed/failed
                {'name': FAILED, 'src': State.TRANSFERRING, 'dst': State.FAILED},
                {'name': COMPLETE, 'src': State.TRANSFERRING, 'dst': State.COPYING},
                # Fetch files from agent
                {'name': FETCH_FAILED, 'src': State.COPYING, 'dst': State.PENDING_COPY},
                {'name': STOP, 'src': State.COPYING, 'dst': State.PENDING_COPY},
                {'name': START, 'src': State.PENDING_COPY, 'dst': State.COPYING},
                {'name': FETCHED, 'src': State.COPYING, 'dst': State.IMPORTING},
                # Import to library
                {'name': IMPORT_FAILED, 'src': State.IMPORTING, 'dst': State.PENDING_IMPORT},
                {'name': STOP, 'src': State.IMPORTING, 'dst': State.PENDING_IMPORT},
                {'name': START, 'src': State.PENDING_IMPORT, 'dst': State.IMPORTING},
                {'name': IMPORTED, 'src': State.IMPORTING, 'dst': State.SEEDING},
                # Completed
                {'name': SEEDED, 'src': State.SEEDING, 'dst': State.COMPLETED},
                # Remove from queue
                {'name': REMOVE, 'src': [ State.TRANSFERRING, State.SEEDING ],
                    'dst': State.REMOVING},
                {'name': STOPPED, 'src': State.REMOVING, 'dst': State.REMOVED},
                {'name': REMOVE, 'src': [ State.QUEUED, State.FAILED, State.COMPLETED,
                        State.PENDING_COPY, State.PENDING_IMPORT ], 
                    'dst': State.REMOVED},
            ]
        }); 

    def onstatechange(self, e):

        self.transfer.state = e.dst
        self.application.store.commit()

        # Specific state transition handlers
        transition = 'on%sto%s' % (e.src, e.dst)
        if hasattr(self, transition) and callable(getattr(self, transition)):
            getattr(self, transition)(e)

        self.application.event_bus.fire(e.event, self.transfer)

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
