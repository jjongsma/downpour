import os
import abc
from downpour2.core import event
from downpour2.core.transfers import state, flow


class TransferClientFactory(object):
    """
    Factory for creating transfer clients. TransferAgents use TransferClientFactory implementations
    to create new clients for different transfer types.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def client(self, transfer):
        return NotImplemented

    @abc.abstractmethod
    def accepts(self, transfer):
        return NotImplemented


class TransferClient(flow.Flow):
    """
    Base class for all transfer clients which implements state transitions as a state machine.

    Transfer flow management methods come from state machine events (start(), stop(), remove(),
    etc). Agent implementations should respond to these events by adding state-change handlers
    to their TransferFlow subclasses (onstarting(), onstopping(), etc).

    See specific client base classes for standard state transitions (SimpleDownloadClient,
    PeerDownloadClient, SimpleUploadClient)
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, transfer, application, rules):

        if transfer.state is None:
            transfer.state = state.QUEUED

        self.transfer = transfer
        self.application = application

        super(TransferClient, self).__init__(rules)

        self.download_rate = 0
        self.upload_rate = 0
        self.max_connections = 0

    def fire(self, evt):
        if hasattr(self, evt):
            return getattr(self, evt)()
        raise ValueError('Unknown event: %s' % evt)

    def onchangestate(self, transition):
        self.transfer.state = transition.dst
        self.application.store.commit()
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
    def directory(self):
        """
        The local directory where this transfer's files are located. For remote agents, this directory
        may be empty or missing until fetch() is called.
        """

        return NotImplemented

    @abc.abstractproperty
    def files(self):
        """
        Returns a list of files that are part of this download. For downloads, filenames should be
        relative paths that resolve within the destination directory after a fetch() call.

        @return: [{'path': filename,
                 'size': size_in_bytes,
                 'progress': percent_progress},]
        """

        return NotImplemented


class DownloadClient(TransferClient):
    """
    Base download client class that includes methods for copying files to a local directory on
    transfer completion.
    """

    def __init__(self, transfer, application, rules):
        super(DownloadClient, self).__init__(transfer, application, rules)

    # noinspection PyUnusedLocal
    @abc.abstractmethod
    def fetch(self, directory=None):
        """
        Copy the transfer files to the specified directory, or the default working directory if none is
        specified. For remote agents, this may take awhile and should properly update the transfer
        progress while a fetch is happening. After a successful copy, the filenames returned by files()
        should resolve to relative paths inside the directory.

        @param directory: The directory to copy the files to (or None for the default working directory)
        @return: The absolute directory path where fetched files can be accessed
        """

        return NotImplemented

    def onstop(self):
        self.transfer.downloadrate = 0

    @staticmethod
    def is_same_fs(file1, file2):
        """"
        Check if two files/directories are on the same filesystem. Useful for deciding whether to link
        or copy when fetching files after a download completes.
        """

        dev1 = os.stat(file1).st_dev
        dev2 = os.stat(file2).st_dev
        return dev1 == dev2


class SimpleDownloadClient(DownloadClient):
    """
    Simple download client base state engine.

    Normal transition flow (STATE -> handler -> NEXT_EVENT)

    state.QUEUED -> onqueued() -> event.START
      -> state.STARTING -> onstarting() -> event.STARTED
      -> state.DOWNLOADING -> ondownloading() -> event.COMPLETE
      -> state.COPYING -> oncopying() -> event.FETCHED
      -> state.COMPLETED -> oncompleted() -> event.REMOVE
      -> state.REMOVED -> onremoved()

    Exception transitions:

    state.DOWNLOADING -> event.STOP -> state.STOPPING -> onstopping() -> event.STOPPED -> event.STOPPED -> onstopped()
    state.COPYING -> event.FETCH_FAILED -> state.PENDING_COPY -> onpending_copy()
    state.* -> event.FAILED -> state.FAILED -> onfailed()
    """

    def __init__(self, transfer, application):
        super(SimpleDownloadClient, self).__init__(transfer, application, {
            'initial': {'state': transfer.state, 'defer': True},
            'events': [
                # Start download
                {'src': [state.QUEUED, state.STOPPED, state.FAILED], 'name': event.START, 'dst': state.STARTING},
                {'src': state.STARTING, 'name': event.STARTED, 'dst': state.DOWNLOADING},
                # Progress updated
                {'src': state.DOWNLOADING, 'name': event.UPDATED, 'dst': state.DOWNLOADING},
                # Download paused
                {'src': [state.STARTING, state.DOWNLOADING], 'name': event.STOP, 'dst': state.STOPPING},
                {'src': state.STOPPING, 'name': event.STOPPED, 'dst': state.STOPPED},
                # Download resumed
                {'src': state.STOPPED, 'name': event.ENQUEUE, 'dst': state.QUEUED},
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
                {'src': [state.STARTING, state.DOWNLOADING, state.COPYING],
                 'name': event.REMOVE, 'dst': state.REMOVING},
                {'src': state.REMOVING, 'name': event.STOPPED, 'dst': state.REMOVED},
                {'src': [state.QUEUED, state.FAILED, state.COMPLETED, state.PENDING_COPY],
                 'name': event.REMOVE, 'dst': state.REMOVED}
            ]
        })


class PeerDownloadClient(DownloadClient):
    """
    P2P download client base state engine, including seeding/upload states.

    Normal transition flow (STATE -> handler -> NEXT_EVENT)

    state.QUEUED -> onqueued() -> event.START
      -> state.STARTING -> onstarting() -> event.STARTED
      -> state.DOWNLOADING -> ondownloading() -> event.COMPLETE
      -> state.COPYING -> oncopying() -> event.FETCHED
      -> state.SEEDING -> onseeding() -> event.COMPLETE
      -> state.COMPLETED -> oncompleted() -> event.REMOVE
      -> state.REMOVED -> onremoved()

    Exception transitions:

    state.DOWNLOADING -> event.STOP -> state.STOPPING -> onstopping() -> event.STOPPED -> event.STOPPED -> onstopped()
    state.COPYING -> event.FETCH_FAILED -> state.PENDING_COPY -> onpending_copy()
    state.SEEDING -> event.STOP -> state.COMPLETED -> oncompleted()
    state.* -> event.FAILED -> state.FAILED -> onfailed()
    """

    def __init__(self, transfer, application):
        super(PeerDownloadClient, self).__init__(transfer, application, {
            'initial': {'state': transfer.state, 'defer': True},
            'events': [
                # Start download
                {'src': [state.QUEUED, state.STOPPED, state.FAILED], 'name': event.START, 'dst': state.STARTING},
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
                         state.PENDING_COPY], 'name': event.REMOVE, 'dst': state.REMOVED}
            ]
        })


class SimpleUploadClient(TransferClient):
    """
    Simple upload client base state engine.

    Normal transition flow (STATE -> handler -> NEXT_EVENT)

    state.STARTING -> onstarting() -> event.STARTED
      -> state.SEEDING -> onseeding() -> event.COMPLETE
      -> state.COMPLETED -> oncompleted() -> event.REMOVE
      -> state.REMOVED -> onremoved()

    Exception transitions:

    state.SEEDING -> event.STOP -> state.STOPPING -> onstopping() -> event.STOPPED -> state.STOPPED -> onstopped()
    state.* -> event.FAILED -> state.FAILED -> onfailed()
    """

    def __init__(self, transfer, application):
        super(SimpleUploadClient, self).__init__(transfer, application, {
            'initial': {'state': transfer.state, 'defer': True},
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
                {'src': [state.FAILED, state.COMPLETED], 'name': event.REMOVE, 'dst': state.REMOVED}
            ]
        })
