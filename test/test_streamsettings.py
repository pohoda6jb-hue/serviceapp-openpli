import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

package = types.ModuleType('stream_test_package')
package.__path__ = []
package._ = lambda value: value
calls = []
package.serviceapp = types.SimpleNamespace(stream_set_settings=lambda key, values: calls.append((key, values)))
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(package.__name__ + '.streamsettings',
    Path(__file__).resolve().parents[1] / 'src/plugin/streamsettings.py')
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)

class StreamPreferences(unittest.TestCase):
    def test_identity_preserves_query_and_ignores_local_options(self):
        self.assertEqual(settings.stream_identity('https://host/a?token=1#sapp_live=1'),
                         settings.stream_identity('https://host/a?token=1'))
        self.assertNotEqual(settings.stream_identity('https://host/a?token=1'),
                            settings.stream_identity('https://host/a?token=2'))

    def test_persistence_reload_and_remove_without_url_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            settings.PATH = str(Path(directory) / 'settings.json')
            identity = settings.stream_identity('https://user:secret@host/live.ts')
            values = {'sapp_live': '1', 'sapp_profile': 'ts'}
            settings.save_settings(identity, values)
            self.assertNotIn('secret', Path(settings.PATH).read_text())
            calls.clear()
            settings.initialize()
            self.assertEqual(calls, [(identity, values)])
            settings.save_settings(identity, {})
            self.assertEqual(settings.load_settings(), {})

if __name__ == '__main__':
    unittest.main()
