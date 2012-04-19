from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implements
import json, base64, os

class DownpourRemote:

    def __init__(self, host='http://localhost:6280', username=None, password=None):

        self.host = host
        self.username = username
        self.password = password
        self.agent = Agent(reactor)

    def get_status(self):
        return self.json_request('status')

    def get_downloads(self):
        return self.json_request('downloads')

    def get_download(self, id):
        return self.json_request('downloads/%s' % id)

    def add_download(self, url, media_type=None):
        return self.json_request(
            'downloads/add', {
                'url': url,
                'media_type': media_type
            })

    def add_torrent(self, file, media_type=None):

        if not os.path.exists(file):
            raise Exception('Unable to find file %s' % self.file)

        f = open(file)
        metadata = f.read()
        f.close()

        return self.json_request(
            'downloads/addtorrent', {
                'metadata': base64.encodestring(metadata),
                'media_type': media_type
            })

    def stop_download(self, id):
        return self.json_request('downloads/%s/stop' % id)

    def start(self, id):
        return self.json_request('downloads/%s/start' % id)

    def restart_download(self, id):
        return self.json_request('downloads/%s/restart' % id)

    def remove_download(self, id):
        return self.json_request('downloads/%s/remove' % id)

    def update_download(self, id, media_type=None):
        return self.json_request('downloads/%s/update' % id, {
                'media_type': media_type
            })

    def get_feeds(self):
        return self.json_request('feeds')

    def get_feed(self, id):
        return self.json_request('feeds/%s' % id)

    def add_feed(self, name, url, media_type=None):
        return self.json_request(
            'feeds/add', {
                'name': name,
                'url': url,
                'media_type': media_type
            })

    def remove_feed(self, id):
        return self.json_request('feeds/%s/remove' % id)

    def json_request(self, path, params=None):

        request = self.agent.request('POST',
            '%s/remote/%s' % (self.host, path),
            Headers({'User-Agent': ['Downpour Remote']}),
            StringProducer(json.dumps({
                '_username': self.username,
                '_password': self.password,
                '_params': params
                })))
        
        return self.deferred_response(request)

    def deferred_response(self, request):

        responseDone = defer.Deferred()
        resultReady = defer.Deferred()

        def read_response(response):
            buffer = ResponseBuffer(responseDone)
            response.deliverBody(buffer)

        def parse_response(response):
            parsed = json.loads(response)
            resultReady.callback(parsed)

        request.addCallback(read_response)
        request.addErrback(resultReady.errback)

        responseDone.addCallback(parse_response)
        responseDone.addErrback(resultReady.errback)

        return resultReady

class StringProducer:
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class ResponseBuffer(Protocol):

    def __init__(self, finished):
        self.finished = finished
        self.body = b''

    def dataReceived(self, bytes):
        self.body = self.body + bytes

    def connectionLost(self, reason):
        self.finished.callback(unicode(self.body))
