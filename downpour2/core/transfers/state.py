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

    def __init__(self, state, name, style='default', progress=False, transferring=False):

        self.state = state
        self.name = name
        self.style = style
        self.progress = progress
        self.transferring = transferring


__definitions__ = {
    QUEUED: State(QUEUED, 'Queued'),
    INITIALIZING: State(INITIALIZING, 'Initializing', 'default', False, True),
    STARTING: State(STARTING, 'Starting', 'default', True, True),
    DOWNLOADING: State(DOWNLOADING, 'Downloading', 'default', True, True),
    COPYING: State(COPYING, 'Copying'),
    PENDING_COPY: State(PENDING_COPY, 'Copy Failed', 'blocked'),
    COMPLETED: State(COMPLETED, 'Completed'),
    SEEDING: State(SEEDING, 'Seeding', 'secondary', True, True),
    STOPPING: State(STOPPING, 'Stopping', 'stopped'),
    STOPPED: State(STOPPED, 'Stopped', 'stopped'),
    FAILED: State(FAILED, 'Failed', 'stopped'),
    REMOVING: State(REMOVING, 'Removing'),
    REMOVED: State(REMOVED, 'Removed')
}


def describe(state):
    return __definitions__[state]
