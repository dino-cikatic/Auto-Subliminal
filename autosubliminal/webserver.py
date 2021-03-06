# coding=utf-8

import json
import os
import re

import cherrypy
from requests_oauthlib.oauth1_session import OAuth1Session
from six import text_type

import autosubliminal
from autosubliminal import config, notifiers, runner, subchecker, utils
from autosubliminal.db import ImdbIdCache, LastDownloads, TvdbIdCache, WantedItems
from autosubliminal.templates.page import PageTemplate


def redirect(abspath, *args, **kwargs):
    assert abspath[0] == '/'
    raise cherrypy.HTTPRedirect(autosubliminal.WEBROOT + abspath, *args, **kwargs)


def redirect_referer(abspath, *args, **kwargs):
    referer = cherrypy.request.headers.get('Referer')
    if referer:
        raise cherrypy.HTTPRedirect(referer, *args, **kwargs)
    else:
        redirect(abspath)


class Home(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def index(self):
        return PageTemplate(filename='/home/home.mako').render()

    @cherrypy.expose(alias='updateWantedItem')
    @cherrypy.tools.json_out()
    def update_wanted_item(self, wanted_item_index, **kwargs):
        # Get wanted item
        wanted_item = autosubliminal.WANTEDQUEUE[int(wanted_item_index)]
        # Update all keys that are passed
        for key in kwargs if wanted_item else None:
            if key in wanted_item:
                wanted_item[key] = kwargs[key]
        # Only return updatable fields
        # These values will be shown in the view through jquery, so apply the display_item() on it!
        return {'displaytitle': utils.display_title(wanted_item),
                'title': utils.display_item(wanted_item, 'title'),
                'year': utils.display_item(wanted_item, 'year'),
                'season': utils.display_item(wanted_item, 'season'),
                'episode': utils.display_item(wanted_item, 'episode'),
                'source': utils.display_item(wanted_item, 'source', 'N/A', uppercase=True),
                'quality': utils.display_item(wanted_item, 'quality', 'N/A', uppercase=True),
                'codec': utils.display_item(wanted_item, 'codec', 'N/A', uppercase=True),
                'releasegrp': utils.display_item(wanted_item, 'releasegrp', 'N/A', uppercase=True)}

    @cherrypy.expose(alias='resetWantedItem')
    @cherrypy.tools.json_out()
    def reset_wanted_item(self, wanted_item_index, **kwargs):
        # Get wanted item
        wanted_item = autosubliminal.WANTEDQUEUE[int(wanted_item_index)]
        wanted_item_db = WantedItems().get_wanted_item(wanted_item['videopath'])
        for key in wanted_item_db:
            wanted_item[key] = wanted_item_db[key]
        # Only return updatable fields
        # These values represent the original values, so apply default display_item() on it!
        return {'displaytitle': utils.display_title(wanted_item),
                'title': utils.display_item(wanted_item, 'title'),
                'year': utils.display_item(wanted_item, 'year'),
                'season': utils.display_item(wanted_item, 'season'),
                'episode': utils.display_item(wanted_item, 'episode'),
                'source': utils.display_item(wanted_item, 'source', 'N/A'),
                'quality': utils.display_item(wanted_item, 'quality', 'N/A'),
                'codec': utils.display_item(wanted_item, 'codec', 'N/A'),
                'releasegrp': utils.display_item(wanted_item, 'releasegrp', 'N/A')}

    @cherrypy.expose(alias='searchId')
    def force_id_search(self, wanted_item_index):
        subchecker.force_id_search(wanted_item_index)
        redirect('/home')

    @cherrypy.expose(alias='skipShow')
    def skip_show(self, wanted_item_index, title, season=None):
        if not season:
            return PageTemplate(filename='/home/home-skipshow.mako').render(wanted_item_index=wanted_item_index,
                                                                            title=title)
        else:
            if not wanted_item_index:
                raise cherrypy.HTTPError(400, 'No wanted_item index supplied')
            if not title:
                raise cherrypy.HTTPError(400, 'No show supplied')
            # Check if season is a number to be sure
            if not season == '00':
                season = text_type(int(season))
            config_season = season
            # Check if already skipped
            title_sanitized = utils.sanitize(title)
            for x in autosubliminal.SKIPSHOW:
                if title_sanitized == utils.sanitize(x):
                    for s in autosubliminal.SKIPSHOW[x].split(','):
                        if s == season or s == '00':
                            utils.add_notification_message('Already skipped show %s season %s.' % (title, season))
                            redirect('/home')
                    # Not skipped yet, skip all or append season the seasons to skip
                    if season == '00':
                        config_season = '00'
                    else:
                        seasons = autosubliminal.SKIPSHOW[x].split(',')
                        seasons.append(season)
                        config_season = ','.join(sorted(seasons))
            # Skip show
            if subchecker.skip_show(wanted_item_index, season):
                config.write_config_property('skipshow', title, config_season)
                config.apply_skipshow()
                if season == '00':
                    utils.add_notification_message('Skipped show %s all seasons.' % title)
                else:
                    utils.add_notification_message('Skipped show %s season %s.' % (title, season))
            else:
                utils.add_notification_message('Could not skip show! Please check the log file!', 'error')

            redirect('/home')

    @cherrypy.expose(alias='skipMovie')
    def skip_movie(self, wanted_item_index, title, year):
        if not wanted_item_index:
            raise cherrypy.HTTPError(400, 'No wanted_item index supplied')
        if not title:
            raise cherrypy.HTTPError(400, 'No title supplied')
        movie = title
        if year:
            movie += ' (' + year + ')'
        # Check if already skipped
        movie_sanitized = utils.sanitize(movie)
        for x in autosubliminal.SKIPMOVIE:
            if movie_sanitized == utils.sanitize(x):
                utils.add_notification_message('Already skipped movie %s.' % movie)
                redirect('/home')
        # Skip movie
        if subchecker.skip_movie(wanted_item_index):
            config.write_config_property('skipmovie', movie, '00')
            config.apply_skipmovie()
            utils.add_notification_message('Skipped movie %s.' % movie)
        else:
            utils.add_notification_message('Could not skip movie! Please check the log file!', 'error')
        redirect('/home')

    @cherrypy.expose(alias='deleteVideo')
    def delete_video(self, wanted_item_index, confirmed=False, cleanup=False):
        if not confirmed:
            wanted_item = autosubliminal.WANTEDQUEUE[int(wanted_item_index)]
            video = wanted_item['videopath']
            return PageTemplate(filename='/home/home-deleteVideo.mako').render(wanted_item_index=wanted_item_index,
                                                                               video=video)
        else:
            # Delete video
            deleted = subchecker.delete_video(wanted_item_index, cleanup)
            if deleted:
                utils.add_notification_message('Video deleted from filesystem.')
            else:
                utils.add_notification_message('Video could not be deleted! Please check the log file!', 'error')
            redirect('/home')

    @cherrypy.expose(alias='searchSubtitle')
    def search_subtitle(self, wanted_item_index, lang):
        # Search subtitle
        subs, errormessage = subchecker.search_subtitle(wanted_item_index, lang)
        # Send response in html (store subs under subs key)
        return PageTemplate(filename='/home/home-manualsearch.mako').render(subs=subs, infomessage=None,
                                                                            errormessage=errormessage)

    @cherrypy.expose(alias='saveSubtitle')
    @cherrypy.tools.json_out()
    def save_subtitle(self, wanted_item_index, subtitle_index):
        # Save subtitle
        saved = subchecker.save_subtitle(wanted_item_index, subtitle_index)
        if saved:
            return {'result': saved, 'infomessage': 'Subtitle saved.', 'errormessage': None}
        else:
            return {'result': saved, 'infomessage': None,
                    'errormessage': 'Unable to save the subtitle! Please check the log file!'}

    @cherrypy.expose(alias='deleteSubtitle')
    @cherrypy.tools.json_out()
    def delete_subtitle(self, wanted_item_index):
        # Delete subtitle
        removed = subchecker.delete_subtitle(wanted_item_index)
        if removed:
            return {'result': removed, 'infomessage': 'Subtitle deleted.', 'errormessage': None}
        else:
            return {'result': removed, 'infomessage': None,
                    'errormessage': 'Unable to delete the subtitle! Please check the log file!'}

    @cherrypy.expose(alias='playVideo')
    @cherrypy.tools.json_out()
    def play_video(self, wanted_item_index):
        # Get wanted item
        wanted_item = autosubliminal.WANTEDQUEUE[int(wanted_item_index)]
        # Play video with default player
        video = wanted_item['videopath']
        try:
            utils.run_cmd(video, False)
            return {'result': True, 'infomessage': 'Playing video.', 'errormessage': None}
        except Exception:
            return {'result': False, 'infomessage': None,
                    'errormessage': 'Cannot play the video! Please check the log file!'}

    @cherrypy.expose(alias='postProcess')
    @cherrypy.tools.json_out()
    def post_process(self, wanted_item_index, subtitle_index=None):
        # Post process
        if subtitle_index:
            processed = subchecker.post_process(wanted_item_index, subtitle_index)
            if processed:
                return {'result': processed, 'infomessage:': None, 'errormessage': None, 'redirect': '/home'}
            else:
                return {'result': processed, 'infomessage': None,
                        'errormessage': 'Unable to handle post processing! Please check the log file!'}
        else:
            subchecker.post_process_no_subtitle(wanted_item_index)
            redirect('/home')


class Config(object):
    def __init__(self):
        # Create config sub tree (name of attribute defines name of path: f.e. general -> /config/general)
        self.general = self._ConfigGeneral()
        self.logging = self._ConfigLogging()
        self.webserver = self._ConfigWebServer()
        self.subliminal = self._ConfigSubliminal()
        self.namemapping = self._ConfigNameMapping()
        self.skipmapping = self._ConfigSkipMapping()
        self.notification = self._ConfigNotification()
        self.postprocessing = self._ConfigPostProcessing()

    @staticmethod
    def save_and_restart_if_needed(section=None):
        # Save to the configfile
        restart = config.write_config(section)

        # Check if restart is needed
        if restart:
            return {'restart': True}

        else:
            # For some reason the config needs to be read again, otherwise all pages get an error
            config.read_config()
            utils.add_notification_message('Config saved.')
            return {}

    @cherrypy.expose
    def index(self):
        # Redirect to general settings by default
        redirect('/config/general')

    class _ConfigGeneral(object):
        def __init__(self):
            self.template_file = '/config/config-general.mako'
            self.section = 'general'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, videopaths, defaultlanguage, defaultlanguagesuffix, additionallanguages, scandisk, checksub,
                 checkversion, checkversionautoupdate, scanembeddedsubs, skiphiddendirs, detectinvalidsublanguage,
                 detectedlanguageprobability, minvideofilesize, maxdbresults):
            # Set general variables
            autosubliminal.VIDEOPATHS = videopaths.split('\r\n')
            autosubliminal.DEFAULTLANGUAGE = defaultlanguage
            autosubliminal.DEFAULTLANGUAGESUFFIX = utils.getboolean(defaultlanguagesuffix)
            autosubliminal.ADDITIONALLANGUAGES = additionallanguages.split(',')
            autosubliminal.SCANDISKINTERVAL = int(scandisk)
            autosubliminal.CHECKSUBINTERVAL = int(checksub)
            autosubliminal.CHECKVERSIONINTERVAL = int(checkversion)
            autosubliminal.CHECKVERSIONAUTOUPDATE = utils.getboolean(checkversionautoupdate)
            autosubliminal.SCANEMBEDDEDSUBS = utils.getboolean(scanembeddedsubs)
            autosubliminal.SKIPHIDDENDIRS = utils.getboolean(skiphiddendirs)
            autosubliminal.DETECTINVALIDSUBLANGUAGE = utils.getboolean(detectinvalidsublanguage)
            autosubliminal.DETECTEDLANGUAGEPROBABILITY = float(detectedlanguageprobability)
            autosubliminal.MINVIDEOFILESIZE = int(minvideofilesize)
            autosubliminal.MAXDBRESULTS = int(maxdbresults)

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigLogging(object):
        def __init__(self):
            self.template_file = '/config/config-logging.mako'
            self.section = 'logging'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, logfile, loglevel, lognum, logsize, loghttpaccess, logexternallibs, logdetailedformat,
                 logreversed, loglevelconsole):
            # Set logfile variables
            autosubliminal.LOGFILE = logfile
            autosubliminal.LOGLEVEL = int(loglevel)
            autosubliminal.LOGNUM = int(lognum)
            autosubliminal.LOGSIZE = int(logsize)
            autosubliminal.LOGHTTPACCESS = utils.getboolean(loghttpaccess)
            autosubliminal.LOGEXTERNALLIBS = utils.getboolean(logexternallibs)
            autosubliminal.LOGDETAILEDFORMAT = utils.getboolean(logdetailedformat)
            autosubliminal.LOGREVERSED = utils.getboolean(logreversed)
            autosubliminal.LOGLEVELCONSOLE = int(loglevelconsole)

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigWebServer(object):
        def __init__(self):
            self.template_file = '/config/config-webserver.mako'
            self.section = 'webserver'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, webserverip, webserverport, webroot, username, password, launchbrowser):
            # Set webserver variables
            autosubliminal.WEBSERVERIP = webserverip
            autosubliminal.WEBSERVERPORT = int(webserverport)
            autosubliminal.WEBROOT = webroot
            autosubliminal.USERNAME = username
            autosubliminal.PASSWORD = password
            autosubliminal.LAUNCHBROWSER = utils.getboolean(launchbrowser)

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigSubliminal(object):
        def __init__(self):
            self.template_file = '/config/config-subliminal.mako'
            self.section = 'subliminal'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, subtitleutf8encoding, manualrefinevideo, refinevideo, preferhearingimpaired,
                 addic7edusername, addic7edpassword, opensubtitlesusername, opensubtitlespassword,
                 showmmsdefault=None, showmmssource=None, showmmsquality=None, showmmscodec=None,
                 showmmsreleasegroup=None,
                 moviemmsdefault=None, moviemmssource=None, moviemmsquality=None, moviemmscodec=None,
                 moviemmsreleasegroup=None,
                 subliminalproviders=None):
            # Set subliminal variables
            # Match options and showminmatchscore
            autosubliminal.SHOWMATCHSOURCE = False
            autosubliminal.SHOWMATCHQUALITY = False
            autosubliminal.SHOWMATCHCODEC = False
            autosubliminal.SHOWMATCHRELEASEGROUP = False
            autosubliminal.SHOWMINMATCHSCORE = 0
            # If not checked, the value will be default None, if checked, it will contain a value
            if showmmsdefault:
                # showmmsdefault is the minimal default score for a show (not editable, so no flag is needed)
                autosubliminal.SHOWMINMATCHSCORE += autosubliminal.SHOWMINMATCHSCOREDEFAULT
            if showmmssource:
                autosubliminal.SHOWMINMATCHSCORE += 7
                autosubliminal.SHOWMATCHSOURCE = True
            if showmmsquality:
                autosubliminal.SHOWMINMATCHSCORE += 2
                autosubliminal.SHOWMATCHQUALITY = True
            if showmmscodec:
                autosubliminal.SHOWMINMATCHSCORE += 2
                autosubliminal.SHOWMATCHCODEC = True
            if showmmsreleasegroup:
                autosubliminal.SHOWMINMATCHSCORE += 15
                autosubliminal.SHOWMATCHRELEASEGROUP = True
            # Match options and movieminmatchscore
            autosubliminal.MOVIEMATCHSOURCE = False
            autosubliminal.MOVIEMATCHQUALITY = False
            autosubliminal.MOVIEMATCHCODEC = False
            autosubliminal.MOVIEMATCHRELEASEGROUP = False
            autosubliminal.MOVIEMINMATCHSCORE = 0
            # If not checked, the value will be default None, if checked, it will contain a value
            if moviemmsdefault:
                # moviemmsdefault is the minimal default score for a movie (not editable, so no flag is needed)
                autosubliminal.MOVIEMINMATCHSCORE += autosubliminal.MOVIEMINMATCHSCOREDEFAULT
            if moviemmssource:
                autosubliminal.MOVIEMINMATCHSCORE += 7
                autosubliminal.MOVIEMATCHSOURCE = True
            if moviemmsquality:
                autosubliminal.MOVIEMINMATCHSCORE += 2
                autosubliminal.MOVIEMATCHQUALITY = True
            if moviemmscodec:
                autosubliminal.MOVIEMINMATCHSCORE += 2
                autosubliminal.MOVIEMATCHCODEC = True
            if moviemmsreleasegroup:
                autosubliminal.MOVIEMINMATCHSCORE += 15
                autosubliminal.MOVIEMATCHRELEASEGROUP = True
            # Subliminal providers
            if isinstance(subliminalproviders, list):
                autosubliminal.SUBLIMINALPROVIDERS = subliminalproviders
            else:
                autosubliminal.SUBLIMINALPROVIDERS = [subliminalproviders] if subliminalproviders else []
            # Subtitle utf8 encoding
            autosubliminal.SUBTITLEUTF8ENCODING = utils.getboolean(subtitleutf8encoding)
            # Refine video
            autosubliminal.MANUALREFINEVIDEO = utils.getboolean(manualrefinevideo)
            autosubliminal.REFINEVIDEO = utils.getboolean(refinevideo)
            # Hearing impaired
            autosubliminal.PREFERHEARINGIMPAIRED = utils.getboolean(preferhearingimpaired)
            # Addic7ed provider
            autosubliminal.ADDIC7EDUSERNAME = addic7edusername
            autosubliminal.ADDIC7EDPASSWORD = addic7edpassword
            # OpenSubtitles provider
            autosubliminal.OPENSUBTITLESUSERNAME = opensubtitlesusername
            autosubliminal.OPENSUBTITLESPASSWORD = opensubtitlespassword

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigNameMapping(object):
        def __init__(self):
            self.template_file = '/config/config-namemapping.mako'
            self.section = 'namemapping'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, shownamemapping, addic7edshownamemapping, alternativeshownamemapping, movienamemapping,
                 alternativemovienamemapping):
            # Set name mapping dicts
            autosubliminal.SHOWNAMEMAPPING = utils.mapping_string_to_dict(shownamemapping)
            autosubliminal.ADDIC7EDSHOWNAMEMAPPING = utils.mapping_string_to_dict(addic7edshownamemapping)
            autosubliminal.ALTERNATIVESHOWNAMEMAPPING = utils.mapping_string_to_dict(alternativeshownamemapping)
            autosubliminal.MOVIENAMEMAPPING = utils.mapping_string_to_dict(movienamemapping)
            autosubliminal.ALTERNATIVEMOVIENAMEMAPPING = utils.mapping_string_to_dict(alternativemovienamemapping)

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigSkipMapping(object):
        def __init__(self):
            self.template_file = '/config/config-skipmapping.mako'
            self.section = 'skipmapping'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, skipshow, skipmovie):
            # Set skip variables
            autosubliminal.SKIPSHOW = utils.mapping_string_to_dict(skipshow)
            autosubliminal.SKIPMOVIE = utils.mapping_string_to_dict(skipmovie)

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigNotification(object):
        def __init__(self):
            self.template_file = '/config/config-notification.mako'
            self.section = 'notification'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='test')
        @cherrypy.tools.json_out()
        def test(self, notify_lib):
            if notifiers.test_notifier(notify_lib):
                utils.add_notification_message('Test notification (%s) sent.' % notify_lib)
            else:
                utils.add_notification_message('Test notification (%s) failed! Please check the log file!' % notify_lib,
                                               'error')
            return {}

        @cherrypy.expose(alias='regTwitter')
        def reg_twitter(self, token_key=None, token_secret=None, token_pin=None):
            import autosubliminal.notifiers.twitter as twitter_notifier

            if not token_key and not token_secret:
                # Getting request token
                oauth_client = OAuth1Session(client_key=twitter_notifier.CONSUMER_KEY,
                                             client_secret=twitter_notifier.CONSUMER_SECRET)
                try:
                    response = oauth_client.fetch_request_token(twitter_notifier.REQUEST_TOKEN_URL)
                except Exception as e:
                    message = 'Something went wrong.../n' + e.message
                    return PageTemplate(filename='/general/message.mako').render(message=message)
                # Authorize
                url = oauth_client.authorization_url(twitter_notifier.AUTHORIZATION_URL)
                token_key = response.get('oauth_token')
                token_secret = response.get('oauth_token_secret')
                return PageTemplate(filename='/config/config-regtwitter.mako').render(url=url, token_key=token_key,
                                                                                      token_secret=token_secret)

            if token_key and token_secret and token_pin:
                # Getting access token
                oauth_client = OAuth1Session(client_key=twitter_notifier.CONSUMER_KEY,
                                             client_secret=twitter_notifier.CONSUMER_SECRET,
                                             resource_owner_key=token_key,
                                             resource_owner_secret=token_secret,
                                             verifier=token_pin)
                try:
                    response = oauth_client.fetch_access_token(twitter_notifier.ACCESS_TOKEN_URL)
                except Exception as e:
                    message = 'Something went wrong.../n' + e.message
                    return PageTemplate(filename='/general/message.mako').render(message=message)
                # Store access token
                autosubliminal.TWITTERKEY = response.get('oauth_token')
                autosubliminal.TWITTERSECRET = response.get('oauth_token_secret')
                # Render template
                message = 'Twitter is now set up, remember to save your config and remember to test twitter!' \
                          '<br><a href="' + autosubliminal.WEBROOT + '/config/notification">Return</a>'
                return PageTemplate(filename='/general/message.mako').render(message=message)

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, notify,
                 notifymail, mailsrv, mailfromaddr, mailtoaddr, mailusername, mailpassword, mailsubject,
                 mailencryption, mailauth,
                 notifytwitter, twitterkey, twittersecret,
                 notifypushalot, pushalotapi,
                 notifypushover, pushoverkey, pushoverapi, pushoverdevices,
                 notifynma, nmaapi, nmapriority,
                 notifygrowl, growlhost, growlport, growlpass, growlpriority,
                 notifyprowl, prowlapi, prowlpriority,
                 notifypushbullet, pushbulletapi,
                 notifytelegram, telegrambotapi, telegramchatid):
            # Set notify variables
            autosubliminal.NOTIFY = utils.getboolean(notify)
            autosubliminal.NOTIFYMAIL = utils.getboolean(notifymail)
            autosubliminal.MAILSRV = mailsrv
            autosubliminal.MAILFROMADDR = mailfromaddr
            autosubliminal.MAILTOADDR = mailtoaddr
            autosubliminal.MAILUSERNAME = mailusername
            autosubliminal.MAILPASSWORD = mailpassword
            autosubliminal.MAILSUBJECT = mailsubject
            autosubliminal.MAILENCRYPTION = mailencryption
            autosubliminal.MAILAUTH = mailauth
            autosubliminal.NOTIFYTWITTER = utils.getboolean(notifytwitter)
            autosubliminal.TWITTERKEY = twitterkey
            autosubliminal.TWITTERSECRET = twittersecret
            autosubliminal.NOTIFYPUSHALOT = utils.getboolean(notifypushalot)
            autosubliminal.PUSHALOTAPI = pushalotapi
            autosubliminal.NOTIFYPUSHOVER = utils.getboolean(notifypushover)
            autosubliminal.PUSHOVERKEY = pushoverkey
            autosubliminal.PUSHOVERAPI = pushoverapi
            autosubliminal.PUSHOVERDEVICES = pushoverdevices
            autosubliminal.NOTIFYNMA = utils.getboolean(notifynma)
            autosubliminal.NMAAPI = nmaapi
            autosubliminal.NMAPRIORITY = nmapriority
            autosubliminal.NOTIFYGROWL = utils.getboolean(notifygrowl)
            autosubliminal.GROWLHOST = growlhost
            autosubliminal.GROWLPORT = int(growlport)
            autosubliminal.GROWLPASS = growlpass
            autosubliminal.GROWLPRIORITY = int(growlpriority)
            autosubliminal.NOTIFYPROWL = utils.getboolean(notifyprowl)
            autosubliminal.PROWLAPI = prowlapi
            autosubliminal.PROWLPRIORITY = int(prowlpriority)
            autosubliminal.NOTIFYPUSHBULLET = utils.getboolean(notifypushbullet)
            autosubliminal.PUSHBULLETAPI = pushbulletapi
            autosubliminal.NOTIFYTELEGRAM = utils.getboolean(notifytelegram)
            autosubliminal.TELEGRAMBOTAPI = telegrambotapi
            autosubliminal.TELEGRAMCHATID = telegramchatid

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)

    class _ConfigPostProcessing(object):
        def __init__(self):
            self.template_file = '/config/config-postprocessing.mako'
            self.section = 'postprocessing'

        @cherrypy.expose
        def index(self):
            return PageTemplate(filename=self.template_file).render()

        @cherrypy.expose(alias='save')
        @cherrypy.tools.json_out()
        def save(self, postprocess, postprocessindividual, postprocessutf8encoding, showpostprocesscmd,
                 showpostprocesscmdargs, moviepostprocesscmd, moviepostprocesscmdargs):
            # Set postprocessing variables
            autosubliminal.POSTPROCESS = utils.getboolean(postprocess)
            autosubliminal.POSTPROCESSINDIVIDUAL = utils.getboolean(postprocessindividual)
            autosubliminal.POSTPROCESSUTF8ENCODING = utils.getboolean(postprocessutf8encoding)
            autosubliminal.SHOWPOSTPROCESSCMD = showpostprocesscmd
            autosubliminal.SHOWPOSTPROCESSCMDARGS = showpostprocesscmdargs
            autosubliminal.MOVIEPOSTPROCESSCMD = moviepostprocesscmd
            autosubliminal.MOVIEPOSTPROCESSCMDARGS = moviepostprocesscmdargs

            # Now save to the configfile and restart if needed
            return Config.save_and_restart_if_needed(self.section)


class Log(object):
    def __init__(self):
        self.template_file = '/log/log.mako'
        pass

    @cherrypy.expose
    def index(self):
        redirect('/log/viewLog')

    @cherrypy.expose(alias='viewLog')
    def view_log(self, loglevel='all', lognum=None):
        content = utils.display_logfile(loglevel, lognum)
        return PageTemplate(filename=self.template_file).render(loglevel=loglevel, lognum=lognum, content=content)

    @cherrypy.expose(alias='clearLog')
    def clear_log(self):
        # Clear log file (open it in write mode and pass)
        with open(autosubliminal.LOGFILE, 'w'):
            pass
        # Remove possible backup log files
        for f in [f for f in os.listdir('.') if os.path.isfile(f) and re.match(autosubliminal.LOGFILE + '.', f)]:
            os.remove(f)
        # Return to default log view
        content = utils.display_logfile()
        return PageTemplate(filename=self.template_file).render(loglevel='all', lognum=None, content=content)


class System(object):
    def __init__(self):
        pass

    @cherrypy.expose(alias='runNow')
    def run_now(self):
        # Run threads now (use delay to be sure that checksub is run after scandisk)
        autosubliminal.SCANDISK.run()
        autosubliminal.CHECKSUB.run(delay=1)
        utils.add_notification_message('Running everything...')
        redirect('/home')

    @cherrypy.expose
    def restart(self):
        runner.restart_app()
        message = 'Auto-Subliminal is restarting...'
        return PageTemplate(filename='/system/system-restart.mako').render(message=message)

    @cherrypy.expose
    def shutdown(self):
        runner.shutdown_app()
        message = 'Auto-Subliminal is shutting down...'
        return PageTemplate(filename='/general/message.mako').render(message=message)

    @cherrypy.expose(alias='info')
    def info(self):
        return PageTemplate(filename='/system/system-info.mako').render()

    @cherrypy.expose
    def status(self):
        return PageTemplate(filename='/system/system-status.mako').render()

    @cherrypy.expose(alias='scanDisk')
    def scan_disk(self):
        autosubliminal.SCANDISK.run()
        redirect_referer('/home')

    @cherrypy.expose(alias='checkSub')
    def check_sub(self):
        autosubliminal.CHECKSUB.run()
        redirect_referer('/home')

    @cherrypy.expose(alias='checkVersion')
    def check_version(self):
        autosubliminal.CHECKVERSION.run()
        redirect_referer('/home')

    @cherrypy.expose(alias='updateVersion')
    def update_version(self):
        autosubliminal.CHECKVERSION.process.update()
        runner.restart_app(exit=True)
        message = 'Auto-Subliminal is restarting...'
        return PageTemplate(filename='/system/system-restart.mako').render(message=message)

    @cherrypy.expose(alias='flushCache')
    def flush_cache(self):
        TvdbIdCache().flush_cache()
        ImdbIdCache().flush_cache()
        utils.add_notification_message('Flushed id cache database.')
        redirect('/home')

    @utils.release_wanted_queue_lock_on_exception
    @cherrypy.expose(alias='flushWantedItems')
    def flush_wanted_items(self):
        if utils.get_wanted_queue_lock():
            # Flush db and wanted queue
            WantedItems().flush_wanted_items()
            autosubliminal.WANTEDQUEUE = []
            utils.release_wanted_queue_lock()
            utils.add_notification_message(
                'Flushed wanted items database. Please launch system \'Scan Disk\'.')
        else:
            utils.add_notification_message('Cannot flush wanted items database when wanted queue is in use!', 'notice')
        redirect('/home')

    @cherrypy.expose(alias='flushLastDownloads')
    def flush_last_downloads(self):
        LastDownloads().flush_last_downloads()
        utils.add_notification_message('Flushed last downloads database.')
        redirect('/home')

    @cherrypy.expose(alias='isAlive')
    def is_alive(self, *args, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            return 'Error: Unsupported Request. Send jsonp request with "callback" variable in the query string.'
        cherrypy.response.headers['Cache-Control'] = 'max-age=0,no-cache,no-store'
        cherrypy.response.headers['Content-Type'] = 'text/javascript'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'x-requested-with'

        if autosubliminal.STARTED:
            return callback + '(' + json.dumps({'msg': 'True'}) + ');'
        else:
            return callback + '(' + json.dumps({'msg': 'False'}) + ');'

    @cherrypy.expose
    def message(self):
        # Handle message via websocket (no logic needed for now)
        # You can access the websocket handler class instance through:
        # handler = cherrypy.request.ws_handler
        pass


class WebServerRoot(object):
    def __init__(self):
        # Create root tree (name of attribute defines name of path: f.e. home -> /home)
        self.home = Home()
        self.config = Config()
        self.log = Log()
        self.system = System()

    @cherrypy.expose
    def index(self):
        redirect('/home')

    def error_page(status, message, traceback, version):
        # Parse status code (example status: '404 Not Found')
        match = re.search(r'^(\d{3}).*$', status)
        # Render template
        status_code = int(match.group(1)) if match else 500
        return PageTemplate(filename='/general/error.mako').render(status_code=status_code, status=status,
                                                                   message=message, traceback=traceback)

    _cp_config = {'error_page.default': error_page}
