"""Exercise config propagation and conditional GUI without an Enigma2 receiver."""
import importlib.util
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Element:
    def __init__(self, default=None, choices=None, **kwargs):
        self.value = default
        self.saved = default
        self.notifiers = []

    def addNotifier(self, fn, initial_call=True):
        self.notifiers.append(fn)
        if initial_call:
            fn(self)

    def removeNotifier(self, fn):
        self.notifiers.remove(fn)

    def save(self):
        self.saved = self.value

    def cancel(self):
        self.value = self.saved

    def isChanged(self):
        return self.saved != self.value


class Subsection:
    def dict(self):
        return vars(self)


class Screen:
    def __init__(self, session):
        self.session = session
        self.onLayoutFinish = []
        self.onClose = []
        self.widgets = {}

    def __getitem__(self, key):
        return self.widgets[key]

    def __setitem__(self, key, value):
        self.widgets[key] = value

    def close(self, *args):
        self.closed = True


class ConfigListScreen:
    def __init__(self, rows, session=None):
        widget = types.SimpleNamespace(list=rows)
        widget.l = types.SimpleNamespace(setList=lambda rows: None)
        self['config'] = widget


def module(name, **attrs):
    value = types.ModuleType(name)
    value.__dict__.update(attrs)
    sys.modules[name] = value
    return value


calls = []
config = Subsection()
config.plugins = Subsection()
module('Components')
module('Components.config', config=config, ConfigSubsection=Subsection,
       ConfigSubDict=dict, ConfigSelection=Element, ConfigBoolean=Element,
       ConfigInteger=lambda default, limits: Element(default), ConfigNothing=Element,
       ConfigText=Element, getConfigListEntry=lambda *args: args)
module('Components.ConfigList', ConfigListScreen=ConfigListScreen)
for name, attr in [('ActionMap', 'ActionMap'), ('Console', 'Console'), ('Label', 'Label')]:
    module('Components.' + name, **{attr: lambda *a, **kw: None})
module('Components.Sources')
module('Components.Sources.StaticText', StaticText=lambda *a: None)
module('Plugins')
module('Plugins.Plugin', PluginDescriptor=object)
module('Screens')
module('Screens.Screen', Screen=Screen)
module('Screens.InfoBar', InfoBar=object, MoviePlayer=Screen)
module('Screens.MessageBox', MessageBox=types.SimpleNamespace(TYPE_ERROR=1, TYPE_YESNO=2))
module('Tools')
module('Tools.BoundFunction', boundFunction=lambda fn, *a: fn)
module('enigma', eEnv=types.SimpleNamespace(resolve=lambda path: path), eServiceReference=object)
pkg = module('serviceapp_test', _=lambda text: text)
pkg.__path__ = [str(ROOT / 'src/plugin')]
native = module('serviceapp_test.serviceapp')
for name in ('serviceapp_set_setting', 'gstplayer_set_setting', 'exteplayer3_set_setting',
             'playback_profile_set_setting', 'player_set_option', 'servicemp3_gstplayer_enable',
             'servicemp3_exteplayer3_enable'):
    setattr(native, name, lambda *args, _name=name: calls.append((_name, args)))
spec = importlib.util.spec_from_file_location('serviceapp_test.plugin', ROOT / 'src/plugin/plugin.py')
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class PluginTests(unittest.TestCase):
    def setUp(self):
        calls[:] = []
        self.ui = plugin.ServiceAppSettings(types.SimpleNamespace(open=lambda *a, **k: None))
        for element in self.ui.all_config_elements():
            element.cancel()

    def test_defaults_preserve_legacy(self):
        plugin.init_serviceapp_settings()
        profiles = [args for name, args in calls if name == 'playback_profile_set_setting']
        self.assertEqual(len(profiles), 3)
        self.assertTrue(all(args[1:] == ('legacy', 8192, 0, 8192, 0, 0) for args in profiles))

    def test_mp3_row_updates_mp3_only(self):
        cfg = plugin.config_serviceapp.exteplayer3['serviceexteplayer3']
        row = next(row for row in self.ui.exteplayer3_options(cfg) if row[0].strip() == 'MP3 software decoding')
        self.assertIs(row[1], cfg.mp3_swdecoding)
        row[1].value = True
        plugin.init_serviceapp_settings()
        args = next(args for name, args in calls if name == 'exteplayer3_set_setting' and args[0] == 2)
        self.assertTrue(args[8])
        self.assertFalse(args[2])

    def test_profile_buffers_and_native_hls_propagate(self):
        cfg = plugin.config_serviceapp.options['servicegstplayer']
        cfg.profile.value = 'auto'
        cfg.ts_buffer_size.value = 2048
        cfg.hls_buffer_size.value = 16384
        plugin.init_serviceapp_settings()
        args = next(args for name, args in calls if name == 'playback_profile_set_setting' and args[0] == 1)
        self.assertEqual(args, (1, 'auto', 2048, 0, 16384, 0, 0))

    def test_openpli_menu_hides_unsupported_switches(self):
        cfg = plugin.config_serviceapp.gstplayer['servicegstplayer']
        cfg.interface.value = 'openpli'
        self.assertEqual(self.ui.gstplayer_options(cfg), [])
        options = plugin.config_serviceapp.options['servicegstplayer']
        options.profile.value = 'ts'
        options.show_advanced.value = True
        labels = [row[0] for row in self.ui.profile_options('gstplayer', options, cfg)]
        self.assertTrue(any('Live TS buffer' in label for label in labels))
        self.assertFalse(any('VOD ring buffer' in label for label in labels))

    def test_hidden_changes_are_cancelled(self):
        cfg = plugin.config_serviceapp.options['servicegstplayer']
        cfg.ts_buffer_size.value = 2048
        cfg.profile.value = 'vod'
        self.ui.keyCancel()
        self.assertEqual(cfg.ts_buffer_size.value, 8192)
        self.assertEqual(cfg.profile.value, 'legacy')

    def test_advanced_options_reset_to_player_defaults(self):
        cfg = plugin.config_serviceapp.exteplayer3['serviceexteplayer3']
        cfg.ffmpeg_option.value = 'rw_timeout=10000000;reconnect_delay_max=4'
        plugin.init_serviceapp_settings()
        self.assertIn(('player_set_option', (2, 'exteplayer3', 'ffmpeg_option', cfg.ffmpeg_option.value)), calls)
        cfg.ffmpeg_option.value = ''
        plugin.init_serviceapp_settings()
        self.assertEqual(calls[-2], ('player_set_option', (2, 'exteplayer3', 'ffmpeg_option', '')))

    def test_ffmpeg_validation(self):
        validate = plugin.serviceapp_client.validFFmpegOptions
        for value in ('', 'rw_timeout=10000000', 'reconnect_delay_max=4;user_agent=test value'):
            self.assertTrue(validate(value), value)
        for value in ('missing', '=value', 'key=', 'key=value;', 'key=value;;key2=value', 'key=\0'):
            self.assertFalse(validate(value), value)


if __name__ == '__main__':
    unittest.main()
