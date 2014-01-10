import json
import random
from downpour2.core.transfers import state, agent
from downpour2.web import common


class DemoStatus(common.AuthenticatedResource):
    def __init__(self, application, environment):
        super(DemoStatus, self).__init__(application, environment)
        self.putChild('', self)

    def render_GET(self, request):
        local_status = self.application.transfer_manager.status

        status = agent.AgentStatus()
        status.version = local_status.version
        status.paused = False
        status.host = local_status.host
        status.interface = local_status.interface
        status.address = local_status.address
        status.active_downloads = 6
        status.queued_downloads = 2
        status.active_uploads = 3
        status.progress = 77.3
        status.connections = 197
        status.diskfree = 684 * 1024 * 1024 * 1024
        status.diskfreepct = 68.4
        status.downloadrate = 2.3 * 1024 * 1024
        status.uploadrate = 92.6 * 1024

        transfers = [
            # Downloads
            [u'Elementary.S02E13.HDTV.x264-LOL.mp4', u'video/tv', state.DOWNLOADING, 78.0],
            [u'Community.S05E03.HDTV.x264-LOL.mp4', u'video/tv', state.DOWNLOADING, 35.4],
            [u'The.Colbert.Report.2014.01.08.Ishmael.Beah.HDTV.x264-LMAO.[VTV].mp4', u'video/tv', state.DOWNLOADING,
             98.2],
            [u'The.Colbert.Report.2014.01.07.John.Seigenthaler.HDTV.x264-LMAO.mp4', u'video/tv', state.DOWNLOADING,
             12.4],
            [u'Marvels.Agents.of.S.H.I.E.L.D.S01E11.REPACK.HDTV.x264-KILLERS.[VTV].mp4', u'video/tv', state.STARTING,
             23.4],
            [u'Justified.S05E01.HDTV.x264-EXCELLENCE.mp4', u'video/tv', state.INITIALIZING, 0.0],
            [u'NCIS.S11E12.HDTV.x264-LOL.mp4', u'video/tv', state.QUEUED, 0.0],
            [u'Person.of.Interest.S03E12.HDTV.x264-LOL.mp4', u'video/tv', state.QUEUED, 0.0],
            # Uploads / seeds
            [u'MythBusters.S13E01.Star.Wars.Revenge.Of.The.Myth.PROPER.HDTV.x264-YesTV[rarbg]', u'video/tv',
             state.SEEDING, 23.5],
            [u'Grimm.S03E09.HDTV.x264-LOL[rarbg]', u'video/tv', state.SEEDING, 100.0],
            [u'Community.S05E02.HDTV.x264-LOL.mp4', u'video/tv', state.SEEDING, 100.0]
        ]

        return json.dumps({
            'status': status,
            'transfers': [transfer(*t) for t in transfers]
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
