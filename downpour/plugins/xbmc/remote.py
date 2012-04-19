from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from downpour.core import VERSION
import json, base64

# Limted remote control to facilitate updating after downloads
# complete, but is very easy to expand using call()/call_http()
# methods.
#
# To add additional methods, see available method reference at:
# - http://wiki.xbmc.org/index.php?title=JSON_RPC
# - http://wiki.xbmc.org/index.php?title=Web_Server_HTTP_API
class XBMCRemote:

    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password

    """
    RPC methods
    """

    # Update media libraries (scan for new files)
    def update(self, type=None):
        #if type == 'audio' or type is None:
        #    self.call_http('ExecBuiltIn(UpdateLibrary(music))')
        #if type == 'video' or type is None:
        #    self.call_http('ExecBuiltIn(UpdateLibrary(video))')
        if type == 'audio' or type is None:
            self.call('AudioLibrary.ScanForContent')
        if type == 'video' or type is None:
            self.call('VideoLibrary.ScanForContent')

    # Clean media libraries (remove missing files)
    # The preferred way to do this is to just configure XBMC to
    # clean on updated (in XBMC settings)
    def clean(self, type=None):
        if type == 'audio' or type is None:
            self.call_http('ExecBuiltIn(CleanLibrary(music))')
        if type == 'video' or type is None:
            self.call_http('ExecBuiltIn(CleanLibrary(video))')

    # Check status of media players (video, audio, pictures)
    def get_active_players(self):
        return self.call('Player.GetActivePlayers')

    """
    Supporting methods for building RPC calls
    """

    # call() is split into call_raw and create_request in order
    # to easily support batch requests (as defined in JSON-RPC 2.0),
    # but XBMC doesn't support batch requests until version 11
    def call(self, method, params=None):

        return self.call_raw(self.create_request(method, params))

    def create_request(self, method, params=None):

        request = { 'jsonrpc': '2.0', 'method': method, 'id': 0 }
        if params:
            request['params'] = params

        return request;

    def call_raw(self, payload):

        authHeaders = None
        if self.username:
            authHeaders = {'Authorization': 'Basic %s' % base64.b64encode(
                    '%s:%s' % (self.username, self.password)) }

        response = getPage('%s/jsonrpc' % self.server,
            agent='Downpour %s' % VERSION,
            headers={'Authorization': 'Basic %s' % base64.b64encode(
                '%s:%s' % (self.username, self.password)) },
            method='POST',
            postdata=json.dumps(payload))

        # Chain to a new deferred to do response parsing
        dfr = Deferred()
        response.addCallback(self.parse_json_response, dfr)
        response.addErrback(dfr.errback)

        return dfr

    def parse_json_response(self, result, dfr):

        parsed = json.loads(result)

        if type(parsed).__name__ == 'list':
            responses = {}
            for res in parsed:
                if 'error' in res:
                    responses[res['id']] = XBMCRemoteException(
                        parsed['error']['message'],
                        parsed['error']['code'])
                else:
                    responses[res['id']] = res['result']
            dfr.callback(responses)
        else:
            if 'error' in parsed:
                dfr.errback(Failure(
                    XBMCRemoteException(parsed['error']['message'],
                        parsed['error']['code'])))
            else:
                dfr.callback(parsed['result'])

    # Use deprecated HTTP API (some methods are not supported
    # in the JSON API yet)
    def call_http(self, method, multi=True, asdict=True):

        url = '%s/xbmcCmds/xbmcHttp?command=%s' % (self.server, method)

        authHeaders = None
        if self.username:
            authHeaders = {'Authorization': 'Basic %s' % base64.b64encode(
                '%s:%s' % (self.username, self.password)) }

        response = getPage(url,
            agent='Downpour %s' % VERSION,
            headers=authHeaders)

        # Chain to a new deferred to do response parsing
        dfr = Deferred()
        response.addCallback(self.parse_http_response, dfr, multi, asdict)
        response.addErrback(dfr.errback)

        return dfr

    def parse_http_response(self, result, dfr, multi=True, asdict=True):

        response = None

        lines = result.split('<li>')[1:]
        lines[len(lines)-1] = lines[len(lines)-1][:-8]
        if lines[0].find(':') == -1:
            asdict = False

        if asdict:
            response = {}
        else:
            response = []

        for l in lines:
            line = l.strip()
            if asdict:
                parts = l.strip().split(':', 1)
                response[parts[0]] = parts[1]
            else:
                response.append(line)

        if multi or asdict:
            dfr.callback(response)
        else:
            dfr.callback(response[0])

class XBMCRemoteException(Exception):

    def __init__(self, message, code):
        self.message = message
        self.code = code

    def __str__(self):
        return self.message
