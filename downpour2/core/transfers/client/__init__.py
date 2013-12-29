import abc
from downpour2.core import event
from downpour2.core.transfers import state, flow


class TransferClientFactory(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def client(self, transfer):
        return NotImplemented


class TransferClient(flow.Flow):
    """
    Transfer flow management methods come from state machine
    events (start(), stop(), remove(), etc). Agent implementations
    should respond to these events by adding state-change handlers
    to their TransferFlow subclasses (onstart(), onstop(), etc).
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, transfer, application, rules):
        super(TransferClient, self).__init__(rules)

        self.transfer = transfer
        self.application = application

        self.download_rate = 0
        self.upload_rate = 0
        self.max_connections = 0

    def fire(self, evt):
        if hasattr(self, evt):
            return getattr(self, evt)()
        raise ValueError('Unknown event: %s' % evt)

    def onchangestate(self, transition):
        self.transfer.state = transition.dst
        self.application.events.fire(transition.event, self)

    def state(self):
        return state.describe(self.current)

    @abc.abstractmethod
    def update(self):
        """
        Notifies the transfer that its the settings have been updated on the
        underlying transfer object (bandwidth throttling, etc) and the agent
        should update its settings.
        """

        return NotImplemented

    @abc.abstractmethod
    def shutdown(self):
        """
        Shutdown the transfer process and unregister from the owning agent.
        After calling shutdown, this object is dead and a new transfer flow
        must be created with TransferManager.provision_transfer()
        """

        return NotImplemented

    @abc.abstractproperty
    def files(self):
        """
        @return: [{'path': filename,
                 'size': size_in_bytes,
                 'progress': percent_progress},]
        """

        return NotImplemented


class DownloadClient(TransferClient):

    def __init__(self, transfer, application, rules):
        super(DownloadClient, self).__init__(transfer, application, rules)

    # noinspection PyUnusedLocal
    @abc.abstractmethod
    def fetch(self, directory):
        """
        Copy the transfer files the specified directory
        """

        return NotImplemented

    def onstop(self):
        self.transfer.downloadrate = 0


class SimpleDownloadClient(DownloadClient):

    def __init__(self, transfer, application):
        super(SimpleDownloadClient, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start download
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.DOWNLOADING},
                # Progress updated
                {'src': state.DOWNLOADING, 'name': event.UPDATED, 'dst': state.DOWNLOADING},
                # Download paused
                {'src': [state.INITIALIZING, state.STARTING, state.DOWNLOADING],
                 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Download resumed
                {'src': state.STOPPED, 'name': event.ENQUEUE, 'dst': state.QUEUED},
                {'src': [state.STOPPED, state.FAILED], 'name': event.START, 'dst': state.INITIALIZING},
                # Download completed/failed
                {'src': '*', 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.DOWNLOADING, 'name': event.COMPLETE, 'dst': state.COPYING},
                # Fetch files from agent
                {'src': state.COPYING, 'name': event.FETCH_FAILED, 'dst': state.PENDING_COPY},
                {'src': state.COPYING, 'name': event.STOP, 'dst': state.PENDING_COPY},
                {'src': state.PENDING_COPY, 'name': event.START, 'dst': state.COPYING},
                # Completed
                {'src': state.COPYING, 'name': event.FETCHED, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': state.DOWNLOADING, 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [state.QUEUED, state.FAILED, state.COMPLETED,
                         state.PENDING_COPY], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })


class PeerDownloadClient(DownloadClient):
    def __init__(self, transfer, application):
        super(PeerDownloadClient, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start download
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.DOWNLOADING},
                # Progress updated
                {'src': state.DOWNLOADING, 'name': event.UPDATED, 'dst': state.DOWNLOADING},
                # Download paused
                {'src': [state.INITIALIZING, state.STARTING, state.DOWNLOADING],
                 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Download resumed
                {'src': state.STOPPED, 'name': event.ENQUEUE, 'dst': state.QUEUED},
                {'src': [state.STOPPED, state.FAILED], 'name': event.START, 'dst': state.INITIALIZING},
                # Download completed/failed
                {'src': '*', 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.DOWNLOADING, 'name': event.COMPLETE, 'dst': state.COPYING},
                # Fetch files from agent
                {'src': state.COPYING, 'name': event.FETCH_FAILED, 'dst': state.PENDING_COPY},
                {'src': state.COPYING, 'name': event.STOP, 'dst': state.PENDING_COPY},
                {'src': state.PENDING_COPY, 'name': event.START, 'dst': state.COPYING},
                {'src': state.COPYING, 'name': event.FETCHED, 'dst': state.SEEDING},
                # Completed
                {'src': state.SEEDING, 'name': event.COMPLETE, 'dst': state.COMPLETED},
                {'src': state.SEEDING, 'name': event.STOP, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': [state.DOWNLOADING, state.SEEDING], 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [state.QUEUED, state.FAILED, state.COMPLETED,
                         state.PENDING_COPY], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })


class SimpleUploadClient(TransferClient):
    def __init__(self, transfer, application):
        super(SimpleUploadClient, self).__init__(transfer, application, {
            'initial': state.QUEUED,
            'events': [
                # Start upload
                {'src': state.QUEUED, 'name': event.START, 'dst': state.INITIALIZING},
                {'src': state.INITIALIZING, 'name': event.INITIALIZED, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.SEEDING},
                # Progress updated
                {'src': state.SEEDING, 'name': event.UPDATED, 'dst': state.SEEDING},
                # Upload paused
                {'src': [state.INITIALIZING, state.STARTING, state.SEEDING],
                 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Upload completed/failed
                {'src': '*', 'name': event.FAILED, 'dst': state.FAILED},
                {'src': state.SEEDING, 'name': event.COMPLETE, 'dst': state.COMPLETED},
                # Remove from queue
                {'src': state.SEEDING, 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [state.FAILED, state.COMPLETED], 'name': event.REMOVE, 'dst': state.REMOVED},
            ]
        })
