import json
import random
from downpour2.core.transfers import state
from downpour2.web import common


class DemoStatus(common.AuthenticatedResource):

    def __init__(self, application, environment):
        super(DemoStatus, self).__init__(application, environment)
        self.putChild('', self)

    def render_GET(self, request):

        importing = [
            # Transcoding/importing
            [u'Community.S05E01.HDTV.x264-LOL.mp4', u'video/tv', u'transcoding', 45.3],
            [u'Elementary.S02E12.720p.HDTV.X264-DIMENSION.mkv', u'video/tv', u'transcoding', 82.3],
            [u'The.Colbert.Report.2014.01.06.Kenneth.Roth.HDTV.x264-LMAO.[VTV].mp4', u'video/tv', u'importing', 75.3]
        ]

        recent = [
            # Recently completed
            [u'White.Collar.S05E05.HDTV.x264-2HD.mp4', u'video/tv', state.COMPLETED, 78.0],
            [u'The.Colbert.Report.2013.12.19.Ben.Stiller.720p.HDTV.x264-2HD[rarbg]', u'video/tv', state.COMPLETED, 78.0],
            [u'Hawaii Five-0 4x11 Pukana', u'video/tv', state.COMPLETED, 78.0],
            [u'Blue Bloods 4x11 Ties That Bind', u'video/tv', state.COMPLETED, 78.0]
        ]

        return json.dumps({
            'imports': [transfer(*t) for t in importing],
            'recent': [transfer(*t) for t in recent]
        }, cls=ObjectEncoder, indent=4)


def transfer(name, media_type, st, progress):

    t = {
        'description': name,
        'media_type': media_type,
        'state': st,
        'progress': progress
    }

    if t['state'] == state.DOWNLOADING:
        t['downloadrate'] = random.randint(200 * 1024, 2000 * 1024)
        t['uploadrate'] = random.randint(10 * 1024, 150 * 1024)
    elif t['state'] == state.SEEDING:
        t['downloadrate'] = 0
        t['uploadrate'] = random.randint(10 * 1024, 150 * 1024)
    else:
        t['downloadrate'] = 0
        t['uploadrate'] = 0

    return t


class ObjectEncoder(json.JSONEncoder):

    def default(self, o):
        return o.__dict__
