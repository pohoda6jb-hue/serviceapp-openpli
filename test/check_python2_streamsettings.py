"""Run persistence and UTF-8 identity checks under the actual legacy interpreter."""
from __future__ import print_function
import os
import shutil
import sys
import tempfile
import types

package = types.ModuleType('legacy_stream_test')
package.__path__ = [os.path.abspath('src/plugin')]
package._ = lambda value: value
calls = []
native = types.ModuleType('legacy_stream_test.serviceapp')
native.stream_set_settings = lambda key, values: calls.append((key, values))
package.serviceapp = native
sys.modules[package.__name__] = package
sys.modules[native.__name__] = native
from legacy_stream_test import streamsettings

directory = tempfile.mkdtemp()
try:
    streamsettings.PATH = os.path.join(directory, 'preferences.json')
    assert streamsettings.load_settings() == {}
    address = u'https://host/caf\u00e9.ts?token=1'
    identity = streamsettings.stream_identity(address)
    assert identity == streamsettings.stream_identity(address.encode('utf-8'))
    assert identity == streamsettings.stream_identity(address + u'#sapp_live=1')
    values = {'sapp_live': '1', 'sapp_profile': 'ts'}
    streamsettings.save_settings(identity, values)
    streamsettings.save_settings(identity, {'sapp_live': '0'})
    assert streamsettings.load_settings()[identity] == {'sapp_live': '0'}
    assert 'token' not in open(streamsettings.PATH).read()
    calls[:] = []
    streamsettings.initialize()
    assert calls == [(identity, {'sapp_live': '0'})]
    streamsettings.save_settings(identity, {})
    assert streamsettings.load_settings() == {}
    print('Legacy persistence, replacement, reload and UTF-8 identity checks passed')
finally:
    shutil.rmtree(directory)
