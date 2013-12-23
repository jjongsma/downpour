QUEUED = 'queued'
INITIALIZING = 'initializing'
STARTING = 'starting'
DOWNLOADING = 'downloading'
COPYING = 'copying'
PENDING_COPY = 'pendingcopy'
COMPLETED = 'completed'
SEEDING = 'seeding'
STOPPING = 'stopping'
STOPPED = 'stopped'
FAILED = 'failed'
REMOVING = 'removing'
REMOVED = 'removed'

class State(object):

    def __init__(self, state, name, style = 'default', progress = False):

        self.state = state
        self.name = name
        self.style = style
        self.progress = progress

__definitions = {
    QUEUED: State(QUEUED, 'Queued'),
    INITIALIZING: State(INITIALIZING, 'Initializing'),
    STARTING: State(STARTING, 'Starting', 'default', True),
    DOWNLOADING: State(DOWNLOADING, 'Downloading', 'default', True),
    COPYING: State(COPYING, 'Copying'),
    PENDING_COPY: State(PENDING_COPY, 'Copy Failed', 'blocked'),
    COMPLETED: State(COMPLETED, 'Completed'),
    SEEDING: State(SEEDING, 'Seeding', 'secondary', True),
    STOPPING: State(STOPPING, 'Stopping'),
    STOPPED: State(STOPPED, 'Stopped'),
    FAILED: State(FAILED, 'Failed', 'failed'),
    REMOVING: State(REMOVING, 'Removing'),
    REMOVED: State(REMOVED, 'Removed')
}

def describe(state):
    return __definitions[state]
