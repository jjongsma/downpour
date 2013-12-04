from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
import sys, os
sys.path.insert(0, 'src')
from downpour2.core import VERSION

setup(name="Downpour",
    version=VERSION,
    license="GPLv2",
    description="Downpour is a web-based BitTorrent client",
    long_description="""\
    Downpour was designed with home media servers in mind.  It supports
    auto-downloading from RSS feeds and automatic importing and renaming
    of downloads into a media library.
    """,
    author="Jeremy Jongsma",
    author_email="jeremy@jongsma.org",
    url="http://home.jongsma.org/software/downpour/",
    packages=find_packages('src', exclude=['*.tests','*.tests.*']),
    package_data={'downpour2.web': ['templates/*.html', 'templates/*/*.html', 'templates/media/*/*']},
    include_package_data=True,
    # Not zip-safe until /media/ handler is rewritten
    zip_safe=False,
    #scripts=['bin/downpourd', 'bin/downpour-torrent-handler'],
    #data_files=[
    #    ('/usr/share/applications', ['bin/downpour-torrent-handler.desktop']),
    #    ('/usr/share/icons/hicolor/16x16/apps', ['graphics/icons/16x16/apps/downpour.png']),
    #    ('/usr/share/icons/hicolor/22x22/apps', ['graphics/icons/22x22/apps/downpour.png']),
    #    ('/usr/share/icons/hicolor/24x24/apps', ['graphics/icons/24x24/apps/downpour.png']),
    #    ('/usr/share/icons/hicolor/32x32/apps', ['graphics/icons/32x32/apps/downpour.png']),
    #    ('/usr/share/icons/hicolor/48x48/apps', ['graphics/icons/48x48/apps/downpour.png']),
    #    ('/usr/share/icons/hicolor/scalable/apps', ['graphics/icons/scalable/apps/downpour.svg'])
    #    ],
    #install_requires=['Twisted-Core>=9.0', 'Twisted-Web>=9.0', 'storm>=0.14', 'jinja2==2.5', 'FeedParser>=4.1', 'python-dateutil==1.5']
    install_requires=['Twisted>=13.0', 'storm>=0.20', 'jinja2>=2.7', 'FeedParser>=5.1', 'python-dateutil>=2.2']
)
