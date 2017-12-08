Auto-Subliminal
===============

[![Travis CI build status](https://travis-ci.org/h3llrais3r/Auto-Subliminal.svg?branch=development)](https://travis-ci.org/h3llrais3r/Auto-Subliminal)
[![Coverage Status](https://coveralls.io/repos/github/h3llrais3r/Auto-Subliminal/badge.svg?branch=development)](https://coveralls.io/github/h3llrais3r/Auto-Subliminal?branch=development)
[![Requirements Status](https://requires.io/github/h3llrais3r/Auto-Subliminal/requirements.svg?branch=development)](https://requires.io/github/h3llrais3r/Auto-Subliminal/requirements/?branch=development)
[![License](https://img.shields.io/github/license/h3llrais3r/Auto-Subliminal.svg)](https://github.com/h3llrais3r/Auto-Subliminal/blob/master/LICENSE)

Thank you for choosing Auto-Subliminal! The automated python subtitle downloader.

This is a modified version of the discontinued Auto-Sub Alpha 0.5.8 project (https://code.google.com/p/auto-sub/).
It makes use of Subliminal (https://github.com/Diaoul/subliminal) for checking and downloading subtitles.

What it does
------------

 * Easy and straightforward script that scans your TV and MOVIE contents
 * If no SUBTITLE is found (externally or internally) it will attempt to download one by using Subliminal
 * Subliminal will attempt to match the correct version of the subtitle with the file located on the disk
 * Once every day it will do a full rescan of your local content
 * Support to search/save/delete a subtitle individually
 * Support to play a video remotely (need to register a custom protocol handler on your remote machine)

What it uses (see libraries.txt for versions)
---------------------------------------------

 * appdirs
 * babelfish
 * beautifulsoup4
 * charade
 * chardet
 * cheetah
 * cherrypy
 * click
 * dogpile.cache
 * dogpile.core
 * enum34
 * enzyme
 * futures
 * gitpython
 * gitdb
 * growl
 * guessit
 * html5lib
 * httplib2
 * imdbpy
 * langdetect
 * oauth2
 * pbr
 * pushbullet
 * pynma
 * pynmwp
 * pysrt
 * pythontwitter
 * python-dateutil
 * pytz
 * pyxdg
 * rarfile
 * rebulk
 * requests
 * simplejson
 * six
 * smmap
 * stevedore
 * subliminal
 * tvdb_api
 * tvdb_api_v2
 * websocket-client
 * ws4py

How to use
----------

 * Install python
 * Install python cheetah package manually or use the installer from Auto-Subliminal (python setup.py install)
 * Start the script: " python AutoSubliminal.py "
 * A web browser should now open
 * Go to the config menu, check the settings and make sure you set at least:
    * Root path: The location where AutoSubliminal.py is located
    * Video paths: The root folder(s) of your series and/or movies
    * Default language: Your primary subtitle language
    * Subliminal settings: Your minimal match score and used providers
 * Restart Auto-Subliminal

Enjoy your subtitles!
