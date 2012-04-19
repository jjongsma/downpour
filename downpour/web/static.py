from twisted.web.static import File
from twisted.web import http
from twisted.protocols.htb import Bucket, HierarchicalBucketFilter
from twisted.internet import abstract, interfaces, reactor
from zope.interface import implements
import logging

class ThrottledFile(File):

    def __init__(self, path, bucketFilter=None, defaultType="text/html", ignoredExts=(),
            registry=None, allowExt=0):
        File.__init__(self, path, defaultType, ignoredExts, registry, allowExt)
        self.bucketFilter = bucketFilter

    def makeProducer(self, request, fileForReading):
        """
            Make a L{ThrottledFileProducer} that will produce the body of this response.

            This method will also set the response code and Content-* headers.

            @param request: The L{Request} object.
            @param fileForReading: The file object containing the resource.
            @return: A L{ThrottledFileProducer}.  Calling C{.start()} on this will begin
            producing the response.
            """

        byteRange = request.getHeader('range')
        if byteRange is not None:
            try:
                parsedRanges = self._parseRangeHeader(byteRange)
                if len(parsedRanges) == 1:
                    offset, size = self._doSingleRangeRequest(
                        request, parsedRanges[0])
                    self._setContentHeaders(request, size)
                    return SingleRangeThrottledFileProducer(
                        request, fileForReading, offset, size, self.bucketFilter)
                else:
                    log.msg("Multiple ranges not supported: %r" % (byteRange,))
            except ValueError:
                log.msg("Ignoring malformed Range header: %r" % (byteRange,))

        self._setContentHeaders(request)
        request.setResponseCode(http.OK)
        return ThrottledFileProducer(request, fileForReading, self.bucketFilter)
        
    def createSimilarFile(self, path):
        f = self.__class__(path, bucketFilter=self.bucketFilter,
            defaultType=self.defaultType, ignoredExts=self.ignoredExts,
            registry=self.registry)
        f.processors = self.processors
        f.indexNames = self.indexNames[:]
        f.childNotFound = self.childNotFound
        return f

class ThrottledFileProducer(object):
    """
    Superclass for classes that implement the business of producing.

    @ivar request: The L{IRequest} to write the contents of the file to.
    @ivar fileObject: The file the contents of which to write to the request.
    """

    implements(interfaces.IPushProducer)

    bufferSize = abstract.FileDescriptor.bufferSize
    paused = True

    def __init__(self, request, fileObject, bucketFilter=None):
        """
        Initialize the instance.
        """
        self.request = request
        self.fileObject = fileObject
        self.bucketFilter = bucketFilter

    def start(self):
        """
        Subclasses should initialize the file position and set
        the expected byte range.
        """
        self.request.registerProducer(self, True)
        self.resumeProducing()

    def pauseProducing(self):
        self.paused = True

    def resumeProducing(self):
        if self.paused:
            self.paused = False
            self._doWrite()

    def _doWrite(self):
        if not self.paused:
            amount = self.bufferSize
            if self.bucketFilter:
                amount = self.bucketFilter.add(amount)
            if amount == 0:
                # Reached bandwidth limit, startup again in a second
                reactor.callLater(1, self._doWrite)
            else:
                data = self.getNextChunk(amount)
                if data:
                    self.request.write(data)
                    reactor.callLater(0, self._doWrite)
                else:
                    self.stopProducing()

    def getNextChunk(self, length):
        return self.fileObject.read(length)

    def stopProducing(self):
        """
        Stop producing data.

        L{IPushProducer.stopProducing} is called when our consumer has died,
        and subclasses also call this method when they are done producing
        data.
        """

        self.paused = True
        self.fileObject.close()

        if self.request:
            self.request.unregisterProducer()
            self.request.finish()
            self.request = None

class SingleRangeThrottledFileProducer(ThrottledFileProducer):
    """
    A L{ThrottledFileProducer} that writes a single chunk of a file to the request.
    """

    def __init__(self, request, fileObject, offset, size, bucketFilter=None):
        """
        Initialize the instance.

        @param request: See L{ThrottledFileProducer}.
        @param fileObject: See L{ThrottledFileProducer}.
        @param offset: The offset into the file of the chunk to be written.
        @param size: The size of the chunk to write.
        """
        ThrottledFileProducer.__init__(self, request, fileObject, bucketFilter)
        self.offset = offset
        self.size = size

    def start(self):
        self.fileObject.seek(self.offset)
        self.bytesWritten = 0
        self.request.registerProducer(self, 0)

    def getNextChunk(self, length):
        if self.bytesWritten < self.size:
            data = self.fileObject.read(
                min(length, self.size - self.bytesWritten))
            if data:
                self.bytesWritten += len(data)
                return data
        return None
