"""Channel preferences are keyed by SHA256; stream credentials are not persisted."""
import hashlib
import json
import os
from . import serviceapp, _

PATH = '/etc/enigma2/serviceapp-streams.json'
try:
    text_type = unicode
except NameError:
    text_type = str

def stream_identity(path):
    if not isinstance(path, text_type):
        path = path.decode('utf-8')
    return hashlib.sha256(path.split('#', 1)[0].encode('utf-8')).hexdigest()

def save_settings(identity, values):
    data = load_settings()
    if values:
        data[identity] = values
    else:
        data.pop(identity, None)
    temporary = PATH + '.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(data, handle)
        handle.flush()
        os.fsync(handle.fileno())
    # rename replaces atomically on Enigma's Linux; replace is Python 3 only.
    getattr(os, 'replace', os.rename)(temporary, PATH)
    serviceapp.stream_set_settings(identity, values)

def load_settings():
    try:
        with open(PATH) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (IOError, OSError, ValueError):
        return {}

def initialize():
    for identity, values in load_settings().items():
        try:
            serviceapp.stream_set_settings(identity, values)
        except (ValueError, TypeError):
            continue

def open_settings(session, **kwargs):
    from Components.ConfigList import ConfigListScreen
    from Components.config import ConfigSelection, ConfigText, getConfigListEntry
    from Components.ActionMap import ActionMap
    from Components.Sources.StaticText import StaticText
    from Components.Label import Label
    from Screens.Screen import Screen
    from Screens.MessageBox import MessageBox
    reference = session.nav.getCurrentlyPlayingServiceReference()
    path = reference and reference.getPath()
    if not path or not path.startswith(('http://', 'https://')):
        session.open(MessageBox, _('Select an HTTP IPTV stream first.'), type=MessageBox.TYPE_INFO)
        return
    identity = stream_identity(path)

    class StreamSettings(ConfigListScreen, Screen):
        def __init__(self, session):
            Screen.__init__(self, session)
            self.skinName = ['ServiceAppSettings', 'Setup']
            self.setup_title = _('ServiceApp: current stream')
            saved = load_settings().get(identity, {})
            self.elements = {}
            rows = []
            choices = (
                ('player', _('Player'), [('', _('Inherit')), ('exteplayer3', 'exteplayer3'), ('gstplayer', 'gstplayer')]),
                ('interface', _('GstPlayer interface'), [('', _('Inherit')), ('flags', _('Legacy flags')), ('openpli', _('OpenPLi positional'))]),
                ('profile', _('Playback profile'), [('', _('Inherit')), ('legacy', _('Legacy')), ('ts', _('TS')), ('hls', _('HLS')), ('vod', _('VOD'))]),
                ('live', _('Live stream recovery'), [('', _('Disabled / inherit')), ('1', _('Live: enable recovery')), ('0', _('VOD: disable recovery'))]),
                ('hls_explorer', _('HLS Explorer'), [('', _('Inherit')), ('0', _('Native player HLS')), ('1', _('Explore variants'))]),
                ('progressive', _('Progressive download'), [('', _('Inherit')), ('0', _('Disabled')), ('1', _('Enabled'))]),
                ('live_ts', _('Player Live TS mode'), [('', _('Inherit')), ('0', _('Disabled')), ('1', _('Enabled'))]),
            )
            for key, label, values in choices:
                element = ConfigSelection(default=saved.get('sapp_' + key, ''), choices=values)
                self.elements[key] = element
                rows.append(getConfigListEntry(label, element))
            for key, label in (
                    ('recovery_retries', _('Recovery attempts (0-9, default 5)')),
                    ('nice', _('Process nice (0-19)')), ('mpegts_program_id', _('TS program ID')),
                    ('ffmpeg_option', _('FFmpeg options (key=value;...)')),
                    ('buffer_size', _('Gst buffer size (KB)')), ('buffer_duration', _('Gst buffer duration (seconds)')),
                    ('ring_buffer_maxsize', _('Gst ring buffer (MB)')), ('download_buffer_path', _('Gst download template'))):
                element = ConfigText(default=saved.get('sapp_' + key, ''), fixed_size=False)
                self.elements[key] = element
                rows.append(getConfigListEntry(label, element))
            ConfigListScreen.__init__(self, rows, session=session)
            self['key_red'] = StaticText(_('Cancel'))
            self['key_green'] = StaticText(_('Save'))
            self['description'] = Label(_('Applies the next time this stream is opened. URL options override these preferences.'))
            self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {
                'cancel': self.close, 'red': self.close, 'green': self.save, 'ok': self.save}, -2)

        def save(self):
            values = {'sapp_' + key: element.value for key, element in self.elements.items() if element.value != ''}
            limits = {'recovery_retries': (0, 9), 'nice': (0, 19), 'mpegts_program_id': (0, 65535),
                      'buffer_size': (1024, 65536), 'buffer_duration': (0, 100), 'ring_buffer_maxsize': (0, 1024)}
            try:
                for key, bounds in limits.items():
                    value = values.get('sapp_' + key)
                    if value is not None and (not value.isdigit() or not bounds[0] <= int(value) <= bounds[1]):
                        raise ValueError(_('Invalid numeric setting: ') + key)
                from . import serviceapp_client
                if not serviceapp_client.validFFmpegOptions(values.get('sapp_ffmpeg_option', '')):
                    raise ValueError(_('Invalid FFmpeg options'))
                template = values.get('sapp_download_buffer_path', '')
                if template and (not template.startswith('/') or not template.endswith('XXXXXX') or '\x00' in template):
                    raise ValueError(_('Invalid download template'))
                save_settings(identity, values)
            except (IOError, OSError, ValueError) as error:
                self.session.open(MessageBox, str(error), type=MessageBox.TYPE_ERROR)
                return
            self.close()

    session.open(StreamSettings)
