from downpour.download import Status
from downpour.core import models
from twisted.internet import defer, threads
from time import time
from datetime import datetime
from dateutil.parser import parse as parsedate
import logging, os, re, mimetypes, shutil

mediatypes = {
    'audio/music': 'Music',
    'audio/podcast': 'Podcasts',
    'audio/other': 'Other Audio',
    'video/movie': 'Movies',
    'video/tv': 'TV Series',
    'video/other': 'Other Video',
    'image/photos': 'Photos',
    'image/other': 'Other Images'
}

media_mimetypes = {
    'audio/music': ['audio/'],
    'audio/podcast': ['audio/'],
    'audio/other': ['audio/'],
    'video/movie': ['video/'],
    'video/tv': ['video/'],
    'video/other': ['video/'],
    'image/photos': ['image/'],
    'image/other': ['image/']
}

extra_mimetypes = {
    'mkv': 'video/x-matroska',
    'mka': 'audio/x-matroska',
}

match_patterns = {
    'audio/music': [
        # Artist - Album/Number - Track Name.ext
        re.compile(r'(?P<a>[^/]+?)[ _]*-[ _]*(?P<b>[^/]+)/(?P<t>[0-9]+)[ _]*-[ _]*(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
        # Artist - Album/Track Name.ext
        re.compile(r'(?P<a>[^/]+?)[ _]*-[ _]*(?P<b>[^/]+)/(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
        # Artist/Album/Number - Track Name.ext
        re.compile(r'(?P<a>[^/]+)/(?P<b>[^/]+)/(?P<t>[0-9]+)[ _]*-[ _]*(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
        # Artist/Album/Track Name.ext
        re.compile(r'(?P<a>[^/]+)/(?P<b>[^/]+)/(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
        # Artist - Track Name.ext
        re.compile(r'(?P<a>[^/]+?)[ _]*-[ _]*(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
        # Track Name.ext
        re.compile(r'(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
    ],
    'audio/podcast': [
        # TODO I don't use podcasts, need to look up examples
    ],
    'audio/other': [
    ],
    'video/movie': [
        # Movie Name (2009).avi
        # Movie.Name.2009.mp4
        # Movie.Name[2009].DVDRIP.XviD.avi
        re.compile(r'(?P<n>[^/]+?)\W?[\W\S](?P<y>[0-9]{4})[^/]*\.(?P<x>\w+)$', re.IGNORECASE),
        # Movie.Name.DVDRIP.XviD.avi
        re.compile(r'(?P<n>[^/]+)\Wdvdrip[^/]*\.(?P<x>\w+)$', re.IGNORECASE),
        re.compile(r'(?P<n>[^/]+)\Wb[rd]rip[^/]*\.(?P<x>\w+)$', re.IGNORECASE),
        # Movie Name.avi
        re.compile(r'(?P<n>[^/]+)\.(?P<x>\w+)$', re.IGNORECASE),
    ],
    'video/tv': [
        # s01e01.avi
        #re.compile(r's(?P<s>\d{1,2})\W?e(?P<e>\d{1,2}).*\.(?P<x>\w+)$', re.IGNORECASE),
        # 01x01.avi
        #re.compile(r'(?P<s>\d{1,2})x(?P<e>\d{1,2}).*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show Name - Episode Title s01.e01.Episode.Title.avi
        re.compile(r'(?P<z>[\w \.]+?)\W*-\W*(?P<n>[\w \.]+?)\W*s(?P<s>\d{1,2})\W?e(?P<e>\d{1,2}).*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show.Name.s01.e01.Episode.Title.avi
        # Show.Name.s01e01.Episode.Title.avi
        # Show_Name.s01e01_Episode_Title.avi
        # Show Name - s01e01 - Episode Title.avi
        re.compile(r'(?P<z>[\w -\.]+?)\W*s(?P<s>\d{1,2})\W?e(?P<e>\d{1,2})\W*(?P<n>[\w -\.]*\w)?.*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show.Name.01x01.Episode.Title.avi
        # Show_Name_01x01_Episode_Title.avi
        # Show Name - 01x01 - Episode Title.avi
        re.compile(r'(?P<z>[\w -\.]+?)\W*(?P<s>\d{1,2})x(?P<e>\d{1,2})\W*(?P<n>[\w -\.]*\w)?.*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show Name - s01e01.avi
        #re.compile(r'(?P<z>[\w -\.]+?)\W*s(?P<s>\d{1,2})\W?e(?P<e>\d{1,2}).*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show Name - 01x01.avi
        #re.compile(r'(?P<z>[\w -\.]+?)\W*(?P<s>\d{1,2})x(?P<e>\d{1,2}).*\.(?P<x>\w+)$', re.IGNORECASE),
    ],
    'video/other': [
        # Show Name - Title - Date.ext
        re.compile(r'(?P<z>[\w \.]+?)\W*-\W*(?P<n>[\w \.]+?)\W*(?P<D>[0-9-\.]{3,}[0-9]).*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show Name - Date - Title.ext
        re.compile(r'(?P<z>[\w -\.]+?)\W*(?P<D>[0-9-\.]{3,}[0-9])\W*(?P<n>[\w -\.]*\w)?.*\.(?P<x>\w+)$', re.IGNORECASE),
        # Show Name - Title.ext
        re.compile(r'(?P<z>[\w \.]+?)\W*-\W*(?P<n>[\w \.]+?).*\.(?P<x>\w+)$', re.IGNORECASE),
        # Title.ext
        re.compile(r'(?P<n>.*)\.(?P<x>\w+)$', re.IGNORECASE),
    ],
    'image/photos': [
    ],
    'image/other': [
    ]
}

rename_patterns = {
    'audio/music': [
        '%a/%b/%t - %n.%x',
        '%a/%b - %n.%x',
        '%a/%n.%x',
        '%a - %b/%t - %n.%x',
        '%a - %b - %n.%x',
        '%a - %n.%x'
    ],
    'audio/podcast': [
        '%z/%e - %n - %D.%x',
        '%z/%z %y-%m-%d %n.%x',
        '%z/%Z.%y.%m.%d.%N.%x',
        '%z/%z - %n.%x',
        '%z/%Z.%N.%x',
        '%n/%n.%x',
        '%n/%N.%x',
    ],
    'audio/other': [
    ],
    'video/movie': [
        '%n (%y).%x',
        '%N(%y).%x',
        '%n.%x',
        '%N.%x'
    ],
    'video/tv': [
        '%z/Season %S/%z S%sE%e %n.%x',
        '%z/Season %S/%Z.s%s.e%e.%N.%x',
        '%z/%z S%sE%e %n.%x',
        '%z/%Z.s%s.e%e.%N.%x',
        '%z/S%sE%e %n.%x',
        '%z/s%s.e%e.%N.%x'
    ],
    'video/other': [
        '%z/%z - %y-%m-%d - %n.%x',
        '%z/%Z.%y.%m.%d.%N.%x',
        '%z/%z - %n.%x',
        '%z/%Z.%N.%x',
        '%z/%n.%x',
        '%z/%N.%x',
        '%n.%x',
        '%N.%x',
    ],
    'image/photos': [
        '%y/%m/%f.%x',
        '%y/%m/%d/%f.%x'
    ],
    'image/other': [
    ]
}

stopwords = [
    # Any three-letter (or more) acronym (HDTV, LOL, etc)
    re.compile(r'\W[A-Z]{3,}\b.*'),
    # DVDRIP/BDRIP tags
    re.compile(r'\Wdvdrip\b.*', re.IGNORECASE),
    re.compile(r'\Wb[rd]rip\b.*', re.IGNORECASE),
    # XviD tags
    re.compile(r'\Wxvid\b.*', re.IGNORECASE),
    # UNRATED
    re.compile(r'\Wunrated\b.*', re.IGNORECASE),
    # 1080p/720p
    re.compile(r'\[0-9]{3,4}p\b.*', re.IGNORECASE),
]

# Post-process downloads to organize them into media libraries
# This should be _very_ fault-tolerant; it can be run multiple
# times (if a user changes which library they want a download
# to be assigned to, etc) and should handle updating previously
# processed downloads gracefully
def process_download(manager, download, client):

    dfr = defer.succeed(True)

    library = None
    libraries = get_media_libraries(manager.get_libraries())
    if download.media_type:
        library = libraries[download.media_type]
    if not library:
        library = models.Library()
        library.directory = None
        library.pattern = u'%p'
        library.keepall = True

    if download.imported:
        # Already imported
        dfr = import_files(download, manager, library, firstRun=False)
    else:
        # New download
        for file in client.get_files():
            f = models.File()
            f.user = download.user
            f.download = download
            f.directory = None
            f.filename = file['path'].decode('utf8')
            f.size = file['size']
            f.media_type = download.media_type
            f.original_filename = file['path'].decode('utf8')
            f.added = time()
            download.files.add(f)
        dfr = import_files(download, manager, library, firstRun=True)

    manager.store.commit()

    return dfr

# Copy media into library
def import_files(download, manager, library, firstRun=True):

    fmap = {}
    dl = []

    targetdir = manager.get_library_directory()
    if library.directory:
        targetdir = '%s/%s' % (targetdir, library.directory)

    for file in download.files:

        fullpath = file.filename
        if firstRun:
            fullpath = '%s/%s' % (manager.get_work_directory(download), file.filename)
        else:
            if file.directory:
                fullpath = '%s/%s/%s' % (manager.get_library_directory(), \
                    file.directory, fullpath)
            else:
                fullpath = '%s/%s' % (manager.get_library_directory(), fullpath)

        # Skip unrecognized media files
        if not library.keepall:
            mimetype = mimetypes.guess_type(file.filename)[0]
            if not mimetype and file.filename.rfind('.') > -1:
                ext = file.filename[file.filename.rfind('.') + 1:]
                if ext in extra_mimetypes:
                    mimetype = extra_mimetypes[ext]
            matches = sum([1 for m in media_mimetypes[download.media_type] \
                    if mimetype and mimetype.startswith(m)])
            if matches == 0:
                download.files.remove(file)
                if not firstRun:
                    os.remove(fullpath)
                    dir = os.path.dirname(fullpath)
                    while os.path.exists(dir) and not len(os.listdir(dir)):
                        os.rmdir(dir)
                        dir = os.path.dirname(dir)
                continue

        # Map filename to desired renaming pattern
        metadata = get_metadata(file.original_filename, download, fullpath)
        dest = pattern_replace(library.pattern, metadata)
        if dest:
            while dest.find('//') > -1:
                dest = dest.replace('//', '/')
        else:
            continue

        # Move file on disk
        dfr = None
        targetfile = '%s/%s' % (targetdir, dest)
        if not firstRun:
            dfr = threads.deferToThread(move_file, \
                fullpath, targetfile, trim_empty_dirs=True)
            dfr.addCallback(manager.application.event_callback, 'library_file_removed', fullpath, download)
            dfr.addCallback(manager.application.event_callback, 'library_file_added', targetfile, download)
        else:
            dfr = threads.deferToThread(copy_file, fullpath, targetfile)
            dfr.addCallback(manager.application.event_callback, 'library_file_added', targetfile, download)
        dfr.addCallback(file_op_complete, download, file, firstRun, \
            library.directory, unicode(dest), download.media_type)
        dl.append(dfr)

    return defer.DeferredList(dl)

# Update database
def file_op_complete(success, download, file, firstRun, newdir, newfile, newtype):
    if success:
        file.directory = newdir
        file.filename = newfile
        file.media_type = newtype
    elif firstRun:
        download.files.remove(file)

def get_metadata(path, source, filename=None):

    metadata = {'a': None, 'b': None, 'd': None, 'D': None,
        'e': None, 'E': None, 'f': None, 'm': None, 'n': None,
        'N': None, 'p': path, 's': None, 'S': None, 't': '1',
        'T': '01', 'x': None, 'y': None, 'z': None, 'Z': None}

    filename = os.path.basename(path)
    pos = filename.rfind('.')
    if pos > -1:
        metadata['f'] = filename[:pos]
        metadata['x'] = filename[pos+1:]
    else:
        metadata['f'] = filename
        
    # Parse metadata from filename
    if source and source.media_type:
        for m in match_patterns[source.media_type]:
            match = m.search(path)
            if match:
                metadata.update(match.groupdict())
                break;

    # Override with real metadata if file exists
    if filename and os.access(filename, os.R_OK):
        metadata.update(get_file_metadata(filename))

    # Source can be either feed or download
    name = None
    if hasattr(source, 'feed') and source.feed:
        name = source.feed.name
    elif hasattr(source, 'name'):
        name = source.name
    normalize_metadata(metadata, name)

    return metadata

# TODO Merge in real metadata from hachoir-metadata parser
def get_file_metadata(path):
    return {}

def normalize_metadata(metadata, name=None):

    if name:
        metadata['z'] = name
        metadata['Z'] = metadata['z'].replace(' ', '.')
    elif metadata['z']:
        metadata['z'] = metadata['z'].replace('.', ' ')
        metadata['z'] = metadata['z'].replace('_', ' ')
        metadata['Z'] = metadata['z'].replace(' ', '.')
    elif metadata['Z']:
        metadata['Z'] = metadata['Z'].replace(' ', '.')
        metadata['Z'] = metadata['Z'].replace('_', '.')
        metadata['z'] = metadata['Z'].replace('.', ' ')
    elif name:
        metadata['z'] = name
        metadata['Z'] = metadata['z'].replace(' ', '.')

    if metadata['n']:
        metadata['n'] = metadata['n'].replace('.', ' ')
        metadata['n'] = metadata['n'].replace('_', ' ')
        metadata['N'] = metadata['n'].replace(' ', '.')
    elif metadata['N']:
        metadata['N'] = metadata['N'].replace(' ', '.')
        metadata['N'] = metadata['N'].replace('_', '.')
        metadata['n'] = metadata['N'].replace('.', ' ')
    else:
        metadata['n'] = 'Unknown Title'
        metadata['N'] = 'Unknown.Title'

    for sw in stopwords:
        if metadata['z'] and sw.search(metadata['z']):
            metadata['z'] = sw.sub('', metadata['z'])
        if metadata['Z'] and sw.search(metadata['Z']):
            metadata['Z'] = sw.sub('', metadata['Z'])
        if metadata['n'] and sw.search(metadata['n']):
            metadata['n'] = sw.sub('', metadata['n'])
        if metadata['N'] and sw.search(metadata['N']):
            metadata['N'] = sw.sub('', metadata['N'])

    if metadata['e']:
        e = int(metadata['e'])
        metadata['e'] = '%02d' % e
        metadata['E'] = '%d' % e

    if metadata['s']:
        s = int(metadata['s'])
        metadata['s'] = '%02d' % s
        metadata['S'] = '%d' % s

    if metadata['D']:
        d = parsedate(metadata['D'])
        metadata['D'] = d.strftime('%Y-%m-%d')
        if not metadata['y']:
            metadata['y'] = d.strftime('%Y')
        if not metadata['m']:
            metadata['m'] = d.strftime('%m')
        if not metadata['d']:
            metadata['d'] = d.strftime('%d')
    elif metadata['y']:
        if not metadata['d']:
            metadata['d'] = '01'
        if not metadata['m']:
            metadata['m'] = '01'
        metadata['D'] = '%s-%s-%s' % (metadata['y'], metadata['m'], metadata['d'])

def pattern_replace(pattern, values):
    for m in values:
        if values[m] is None:
            pattern = pattern.replace('%' + m, '')
        else:
            pattern = pattern.replace('%' + m, values[m])
    return pattern

def move_file(src, dest, trim_empty_dirs=False): 
    try:
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)
        shutil.move(src, dest)
        if trim_empty_dirs:
            srcdir = os.path.dirname(src)
            while os.path.exists(srcdir) and not len(os.listdir(srcdir)):
                os.rmdir(srcdir)
                srcdir = os.path.dirname(srcdir)
        return True
    except Exception as e:
        return False

def remove_file(file, trim_empty_dirs=False):
    try:
        os.remove(file)
        if trim_empty_dirs:
            srcdir = os.path.dirname(file)
            while os.path.exists(srcdir) and not len(os.listdir(srcdir)):
                os.rmdir(srcdir)
                srcdir = os.path.dirname(srcdir)
        return True
    except Exception as e:
        return False

def copy_file(src, dest):
    try:
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)
        shutil.copy(src, dest)
        return True
    except Exception as e:
        return False

def move_files(filemap, trim_empty_dirs=False):
    for src in filemap:
        dest = filemap[src]
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)
        shutil.move(src, dest)
        srcdir = os.path.dirname(src)
        while os.path.exists(srcdir) and not len(os.listdir(srcdir)):
            os.rmdir(srcdir)
            srcdir = os.path.dirname(srcdir)

def copy_files(filemap):
    for src in filemap:
        dest = filemap[src]
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)
        shutil.copy(src, dest)

def get_media_types():
    return mediatypes

def get_media_libraries(userlibs):
    libraries = {}
    for t in mediatypes:
        for l in userlibs:
            if l.media_type == t:
                libraries[t] = l
        if not t in libraries:
            libraries[t] = None
    return libraries

def get_file_patterns():
    patterndesc = {}
    replacements = {
        'a': 'Artist',
        'b': 'Album',
        'd': '15',
        'D': '2009-10-15',
        'e': '03',
        'f': 'filename',
        'E': '3',
        'm': '10',
        'n': 'Media Title',
        'N': 'Media.Title',
        'p': 'filename.ext',
        's': '01',
        'S': '1',
        't': '05',
        'T': '5',
        'y': '2009',
        'z': 'Series Name',
        'Z': 'Series.Name',
        'x': 'ext',
        }
    for t in rename_patterns:
        patterndesc[t] = {}
        for p in rename_patterns[t]:
            patterndesc[t][p] = pattern_replace(p, replacements)
    return patterndesc
