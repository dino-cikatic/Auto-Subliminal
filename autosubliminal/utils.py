# coding=utf-8

import cgi
import codecs
import ctypes
import datetime
import logging
import os
import platform
import re
import stat
import subprocess
import threading
import time
from functools import wraps

import requests
from six import PY2, text_type, binary_type

import autosubliminal

log = logging.getLogger(__name__)

_lock = threading.Lock()

# Copied from ConfigParser
_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}

LOG_PARSER = re.compile('^((?P<date>\d{4}\-\d{2}\-\d{2}) (?P<time>\d{2}:\d{2}:\d{2},\d{3}) (?P<loglevel>\w+))',
                        re.IGNORECASE)


def today():
    """
    Helper to get today as datetime.
    We made this a function, otherwise we can't mock built-in datetime.datetime.today in our tests!
    """
    return datetime.datetime.today()


def add_event_message(event_type):
    """
    Add an event message. The event type decides the event to handle.
    Possible values for event type are:
    - HOME_PAGE_RELOAD
    """
    event = {'event_type': event_type}
    message_dict = {'message_type': 'event', 'event': event}
    autosubliminal.MESSAGEQUEUE.append(message_dict)


def add_notification_message(notification_message, notification_type='info', sticky=False):
    """
    Add a notification message with a specific notification type.
    Possible values for notification type are (to be in sync with PNotify jquery plugin):
    - info (blue)
    - success (green)
    - notice (orange)
    - error (red)
    Sticky indicates that it will be shown at a fixed inline location and it will not fade.
    """
    notification = {'notification_message': notification_message,
                    'notification_type': notification_type,
                    'sticky': sticky}
    message_dict = {'message_type': 'notification', 'notification': notification}
    autosubliminal.MESSAGEQUEUE.append(message_dict)


def run_cmd(cmd, communicate=True):
    log.debug('Running cmd: %r', cmd)
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    if communicate:
        # Return stdout, stderr
        return process.communicate()


def connect_url(url):
    """
    Connect to a certain url.
    Use our user agent and timeout by default.
    """
    log.debug('Connecting to url: %s', url)
    try:
        return requests.get(url, headers={'User-Agent': autosubliminal.USERAGENT}, timeout=autosubliminal.TIMEOUT)
    except Exception as e:
        # Replaces log.exception() because we want it to be logged in debug
        log.debug('Could not connect to url: %s', url, exc_info=True)
        # Throw again the exception
        raise e


def wait_for_internet_connection():
    """
    Function that blocks the process until there is internet connection.
    """

    # Internal check for internet connection
    def _check_internet_connection(url):
        try:
            connect_url(url)
            return True
        except Exception:
            return False

    log.debug('Checking internet connection')
    while not _check_internet_connection(autosubliminal.VERSIONURL):
        log.debug('Waiting for internet connection')
        time.sleep(5)


# Based on ConfigParser.getboolean
def getboolean(value):
    v = text_type(value)
    if v.lower() not in _boolean_states:
        raise ValueError('Not a boolean: %s' % v)
    return _boolean_states[v.lower()]


def safe_text(obj, default_value=None):
    """
    Return the object converted to text.
    When not possible return the default value.
    """
    try:
        return text_type(obj)
    except Exception:
        return default_value


def safe_uppercase(obj, default_value=None):
    """
    Return the object converted to uppercase.
    When not possible return the default value.
    """
    try:
        return obj.upper()
    except Exception:
        return default_value


def safe_trim(obj, default_value=None):
    """
    Return the object trimmed with leading and trailing spaces, tabs and newlines.
    When not possible return the default value.
    """
    try:
        return obj.strip(' \n\r\t')
    except Exception:
        return default_value


def sanitize(string_value, ignore_characters=None):
    """Sanitize a string to strip special characters.
    Copied from https://github.com/Diaoul/subliminal/blob/master/subliminal/utils.py
    """
    ignore_characters = ignore_characters or set()
    # Only deal with strings
    if string_value is None:
        return
    # Replace some characters with one space
    characters = {'-', ':', '(', ')', '.'} - ignore_characters
    if characters:
        string_value = re.sub(r'[%s]' % re.escape(''.join(characters)), ' ', string_value)
    # Remove some characters
    characters = {'\''} - ignore_characters
    if characters:
        string_value = re.sub(r'[%s]' % re.escape(''.join(characters)), '', string_value)
    # Replace multiple spaces with one
    string_value = re.sub(r'\s+', ' ', string_value)
    # Strip and lower case
    return string_value.strip().lower()


def mapping_string_to_dict(mapping_string=None):
    """
    Return a dict from a string for the name mappings (key = value).
    """
    mapping_string = mapping_string.split('\r\n')
    mapping_info_list = []

    for mapping in mapping_string:
        if mapping:
            mapping_info = []
            for x in mapping.split('='):
                if x[-1:] == ' ':
                    x = x[:-1]
                elif x[:1] == ' ':
                    x = x[1:]
                mapping_info.append(x)
            mapping_info = tuple(mapping_info)
            mapping_info_list.append(mapping_info)
    return dict(mapping_info_list)


def get_show_name_mapping(show_name):
    """
    Get the tvdb show name mapping for a show.
    @param show_name: The show name to get the tvdb id for
    @return: The tvdb show id or None
    @rtype: int
    """
    show_name_sanitized = sanitize(show_name)
    for x in autosubliminal.SHOWNAMEMAPPING:
        if show_name_sanitized == sanitize(x):
            log.debug('Found match in shownamemapping for %s', show_name)
            return int(autosubliminal.SHOWNAMEMAPPING[x])


def get_addic7ed_show_name_mapping(show_name):
    """
    Get the addic7ed show name mapping for a show.
    @param show_name: The show name to get the addic7ed id for
    @return: The addic7ed show id or None
    @rtype: int
    """
    show_name_sanitized = sanitize(show_name)
    for x in autosubliminal.ADDIC7EDSHOWNAMEMAPPING:
        if show_name_sanitized == sanitize(x):
            log.debug('Found match in addic7edshownamemapping for %s', show_name)
            return int(autosubliminal.ADDIC7EDSHOWNAMEMAPPING[x])


def get_alternative_show_name_mapping(show_name):
    """
    Get the list of alternative show names for a show.
    @param show_name: The show name to get the alternatives for.
    @return: A list of alternative show names or None.
    @rtype: list
    """
    show_name_sanitized = sanitize(show_name)
    for x in autosubliminal.ALTERNATIVESHOWNAMEMAPPING:
        if show_name_sanitized == sanitize(x):
            log.debug('Found match in alternativeshownamemapping for %s', show_name)
            alternatives = autosubliminal.ALTERNATIVESHOWNAMEMAPPING[x]
            return [sanitize(x) for x in alternatives.split(',')]  # Needs to return a list


def get_movie_name_mapping(title, year):
    """
    Get the imdb movie name mapping for a movie.
    @param title: The title of the movie.
    @param year:  The year of the movie.
    @return: The imdb id of the movie or None.
    @rtype: str
    """
    movie = title
    if year:
        movie += ' (' + text_type(year) + ')'
    movie_sanitized = sanitize(movie)
    for x in autosubliminal.MOVIENAMEMAPPING:
        if movie_sanitized == sanitize(x):
            log.debug('Found match in movienamemapping for %s', movie)
            return autosubliminal.MOVIENAMEMAPPING[x]


def get_alternative_movie_name_mapping(title, year):
    """
    Get the list of alternative movie titles (without year).
    @param title: The title of the movie.
    @param year: The year of the movie.
    @return: A list of alternative titles (without year) or None.
    @rtype: list
    """
    movie = title
    if year:
        movie += ' (' + text_type(year) + ')'
    movie_sanitized = sanitize(movie)
    for x in autosubliminal.ALTERNATIVEMOVIENAMEMAPPING:
        if movie_sanitized == sanitize(x):
            log.debug('Found match in alternativemovienamemapping for %s', movie)
            alternatives = autosubliminal.ALTERNATIVEMOVIENAMEMAPPING[x]
            return [sanitize(x) for x in alternatives.split(',')]  # Needs to return a list


def skip_show(show_name, season, episode):
    show_name_sanitized = sanitize(show_name)
    for x in autosubliminal.SKIPSHOW:
        if show_name_sanitized == sanitize(x):
            log.debug('Found match in skipshow for %s', show_name)
            for s in autosubliminal.SKIPSHOW[x].split(','):
                if s == '00':
                    log.debug('Found all season match in skipshow, skipping all seasons for %s', show_name)
                    return True
                elif int(s) == int(season):
                    log.debug('Found season match in skipshow, skipping season %s for %s', season, show_name)
                    return True


def skip_movie(title, year):
    movie = title
    if year:
        movie += ' (' + text_type(year) + ')'
    movie_sanitized = sanitize(movie)
    for x in autosubliminal.SKIPMOVIE:
        if movie_sanitized == sanitize(x):
            log.debug('Found match in skipmovie, skipping movie %s', movie)
            return True


def count_backup_logfiles():
    # Count the number of backup logfiles
    result = len([f for f in os.listdir('.') if os.path.isfile(f) and re.match(autosubliminal.LOGFILE + '.', f)])
    return result


def get_logfile(lognum=None):
    logfile = autosubliminal.LOGFILE
    if lognum:
        logfile += '.' + text_type(lognum)
    if os.path.isfile(logfile):
        return logfile
    return None


def display_logfile(loglevel='all', lognum=None):
    # Read log file data
    data = []
    previous_loglevel = loglevel
    logfile = get_logfile(lognum)
    if logfile:
        f = codecs.open(logfile, 'r', 'utf-8')
        data = f.readlines()
        f.close()
    # Log data
    log_data = []
    for x in data:
        try:
            matches = LOG_PARSER.search(x)
            match_dict = matches.groupdict() if matches else None
            if match_dict:
                # Check if the record matches the requested loglevel
                if (loglevel == 'all') or (match_dict['loglevel'] == loglevel.upper()):
                    log_data.append(x)
                # Store record loglevel as previous loglevel (needed for log records without match_dict)
                previous_loglevel = match_dict['loglevel']
            else:
                # When no match is found (f.e. traceback logging) assume it's the same loglevel as the previous record
                if (loglevel == 'all') or (previous_loglevel.upper() == loglevel.upper()):
                    log_data.append(x)
        except Exception:
            continue
    # If reversed order is needed, use reversed(log_data)
    if autosubliminal.LOGREVERSED:
        log_data = reversed(log_data)
    result = cgi.escape(''.join(log_data))
    return result


def display_list_single_line(list_object):
    """
    Return a single lined string (comma separated) containing all the values of the list.
    """
    s = ''
    for x in list_object:
        if s == '':
            s += x
        else:
            s += ',' + x
    return s


def display_list_multi_line(list_object):
    """
    Return a multi lined string containing all values of the list.
    """
    s = ''
    for x in list_object:
        if s == '':
            s += x
        else:
            s += '\n' + x
    return s


def display_mapping_dict(mapping_dict):
    """
    Return a multi lined string containing all mappings (key = value) from the mapping_dict.
    """
    s = ''
    for x in mapping_dict:
        if s == '':
            s += x + ' = ' + text_type(mapping_dict[x])
        else:
            s += '\n' + x + ' = ' + text_type(mapping_dict[x])
    return s


def display_item(item_dict, key, default_value='', uppercase=False):
    item = item_dict.get(key, default_value) or default_value
    item = safe_text(item, default_value)
    if uppercase:
        item = safe_uppercase(item, default_value)
    return item


def display_title(item_dict, default_value='N/A', uppercase=False):
    title = display_item(item_dict, 'title', default_value, False)
    year = display_item(item_dict, 'year', default_value, False)
    if not title == default_value and not year == default_value:
        title += ' (' + year + ')'
    if uppercase:
        title = safe_uppercase(title, default_value)
    return title


def display_name(item_dict, default_value='N/A', uppercase=False):
    name = display_title(item_dict, default_value, False)
    if 'type' in item_dict and item_dict['type'] == 'episode':
        season = display_item(item_dict, 'season', default_value, False)
        episode = display_item(item_dict, 'episode', default_value, False)
        if not season == default_value and not episode == default_value:
            name += ' S' + season.zfill(2) + 'E' + episode.zfill(2)
    if uppercase:
        name = safe_uppercase(name, default_value)
    return name


def display_timestamp(time_float, format='%d-%m-%Y %H:%M:%S', default_value='N/A'):
    if time_float > 0.0:
        return time.strftime(format, time.localtime(time_float))
    else:
        return default_value


def display_next_scheduler_run(scheduler):
    if not scheduler or scheduler.running:
        return 'Running...'
    else:
        return display_timestamp(scheduler.interval - (time.time() - scheduler.last_run), '%H:%M:%S')


def get_next_scheduler_run_in_ms(scheduler):
    if not scheduler or scheduler.running:
        return 0
    else:
        return (scheduler.last_run + scheduler.interval) * 1000


def convert_timestamp(timestamp_string, format_from='%Y-%m-%d %H:%M:%S', format_to='%d-%m-%Y %H:%M:%S'):
    return time.strftime(format_to, time.strptime(timestamp_string, format_from))


def get_wanted_queue_lock():
    with _lock:
        if autosubliminal.WANTEDQUEUELOCK:
            log.debug('Cannot get wanted queue lock, skipping')
            return False
        else:
            log.debug('Getting wanted queue lock')
            autosubliminal.WANTEDQUEUELOCK = True
            return True


def release_wanted_queue_lock():
    with _lock:
        if autosubliminal.WANTEDQUEUELOCK:
            log.debug('Releasing wanted queue lock')
            autosubliminal.WANTEDQUEUELOCK = False
        else:
            log.warning('Trying to release a wanted queue lock while there is no lock')


def release_wanted_queue_lock_on_exception(func):
    """
    Decorator to force the release of the wanted queue lock on unexpected exceptions.
    This should be used on every place where we do a get_wanted_queue_lock to release it also on unexpected exceptions.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            with _lock:
                if autosubliminal.WANTEDQUEUELOCK:
                    log.exception('Releasing wanted queue lock with force due to exception')
                    autosubliminal.WANTEDQUEUELOCK = False
            raise e

    return wrapper


def count_wanted_items(itemtype=None):
    size = 0
    if not itemtype:
        size = len(autosubliminal.WANTEDQUEUE)
    else:
        for item in autosubliminal.WANTEDQUEUE:
            if item['type'] == itemtype:
                size += 1
    return size


def get_file_size(path):
    try:
        byte_size = os.path.getsize(path)
    except Exception:
        # If size cannot be retrieved, it's most likely because the path doesn't exist anymore
        # Occurs when displaying gui when a sub check is running and files are already moved by a postprocessor script
        byte_size = 0
    return humanize_bytes(byte_size, 2)


def get_common_path(paths, separator=os.path.sep):
    """
    Get the common path between paths.
    This unlike the os.path.commonprefix version always returns path prefixes as it compares path component wise.
    See https://stackoverflow.com/questions/21498939/how-to-circumvent-the-fallacy-of-pythons-os-path-commonprefix
    """
    cp = []
    ls = [p.split(separator) for p in paths]
    ml = min(len(p) for p in ls)
    for i in list(range(ml)):
        s = set(p[i] for p in ls)
        if len(s) != 1:
            break
        cp.append(s.pop())
    return separator.join(cp) if cp else None


def get_root_path(video_path, separator=os.path.sep):
    """
    Get the root path of a video path.
    The root path must be one of the paths listed in autosubliminal.VIDEOPATHS
    """
    for path in autosubliminal.VIDEOPATHS:
        norm_path = os.path.normpath(path)
        if get_common_path([norm_path, video_path], separator) == norm_path:
            return path
    # Should not occur, but you just to make sure
    raise RuntimeError('Video %s not located in one of the configured VIDEOPATHS' % video_path)


# Thanks to: http://stackoverflow.com/questions/1088392/sorting-a-python-list-by-key-while-checking-for-string-or-float
def get_attr(name):
    def inner_func(o):
        try:
            rv = float(o[name])
        except ValueError:
            rv = o[name]
        return rv

    return inner_func


# Thanks to: http://code.activestate.com/recipes/577081-humanized-representation-of-a-number-of-bytes/
def humanize_bytes(bytes, precision=1):
    """
    Return a humanized string representation of a number of bytes.

    >>> humanize_bytes(1)
    '1 byte'
    >>> humanize_bytes(1024)
    '1.0 kB'
    >>> humanize_bytes(1024*123)
    '123.0 kB'
    >>> humanize_bytes(1024*12342)
    '12.1 MB'
    >>> humanize_bytes(1024*12342,2)
    '12.05 MB'
    >>> humanize_bytes(1024*1234,2)
    '1.21 MB'
    >>> humanize_bytes(1024*1234*1111,2)
    '1.31 GB'
    >>> humanize_bytes(1024*1234*1111,1)
    '1.3 GB'
    """
    abbrevs = (
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'bytes')
    )
    if bytes == 0:
        return '0 bytes'
    if bytes == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if bytes >= factor:
            break
    # Python 2.x uses integer division by default, so convert to float first
    return '%.*f %s' % (precision, float(bytes) / factor, suffix)


# Thanks to http://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python
def get_disk_space_details(directory):
    """Return folder/drive disk space details (free and total space)."""
    if platform.system() == 'Windows':
        total_bytes = ctypes.c_ulonglong(0)
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(directory), None, ctypes.pointer(total_bytes),
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value, total_bytes.value
    else:
        st = os.statvfs(directory)
        return st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize


def set_rw_and_remove(operation, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def u2b(unicode_string, encoding='utf-8'):
    """
    Convert a unicode string to a byte string.
    @param unicode_string: A unicode string
    @param encoding: The used encoding, defaults to utf-8
    @return: The byte string
    """
    try:
        return unicode_string.encode(encoding)
    except Exception:
        # Fallback to 'replace' and 'ignore' error mode
        try:
            return unicode_string.encode(encoding, 'replace')
        except Exception:
            return unicode_string.encode(encoding, 'ignore')


def b2u(byte_string, encoding='utf-8'):
    """
    Convert a byte string to a unicode string.
    @param btype_string: A byte string
    @param encoding: The used encoding, defaults to utf-8
    @return: The unicode string
    """
    try:
        return byte_string.decode(encoding)
    except Exception:
        # Fallback to 'replace' and 'ignore' error mode
        try:
            return byte_string.decode(encoding, 'replace')
        except Exception:
            return byte_string.decode(encoding, 'ignore')


def s2n(s, encoding='utf-8', validate=False):
    """
    Convert a string value to the native string representation.
    @param s: A string value
    @param encoding: The used encoding, defaults to utf-8
    @param validate: Indication if the provided native string must be validated against the provided encoding
    @return: The native string (based on python version)
    """
    if PY2:
        # In Python 2, the native string type is bytes
        if isinstance(s, text_type):  # unicode for Python 2
            return s.encode(encoding)
        elif validate:
            # Test if the provided native string can be represented with the provided encoding
            return s.decode(encoding).encode(encoding)
        else:
            return s
    else:
        # In Python 3, the native string type is unicode
        if isinstance(s, binary_type):  # bytes for Python 3
            return s.decode(encoding)
        elif validate:
            return s.encode(encoding).decode(encoding)
        else:
            return s
