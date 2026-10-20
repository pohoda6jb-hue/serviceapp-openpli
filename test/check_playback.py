"""Compile unchanged production option/argv/profile functions with Enigma2 shims.

Checks deterministic policy, not receiver SDK linking or real playback.
"""
import os
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sysconfig
import tempfile

SRC = Path(__file__).resolve().parents[1] / 'src/serviceapp'


def read(name):
    return (SRC / name).read_text()


def section(text, start, end):
    return text[text.index(start):text.index(end)]


ext, gst, service = (read(name) for name in ('exteplayer3.cpp', 'gstplayer.cpp', 'serviceapp.cpp'))
code = r'''
#define NO_PYTHON
#define NO_UCHARDET
#include "common.h"
#include "playbackprofile.h"
#include "recovery.h"
#include "playerprotocol.h"
#include <cassert>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#define eWarning(...) ((void)0)
#define eDebug(...) ((void)0)
'''
for name, prefix, cls in [('exteplayer3.h', 'struct ', 'ExtEplayer3'), ('gstplayer.h', 'class ', 'GstPlayer')]:
    code += section(read(name), prefix + cls + 'Options', 'class ' + cls + ':')
code += section(read('common.cpp'), 'SettingEntry::SettingEntry()', 'Url::Url(')
code += section(ext, 'const std::string', 'ExtEplayer3::ExtEplayer3(')
code += section(gst, 'const std::string', 'GstPlayer::GstPlayer(')
code += r'''
struct BasePlayer { virtual ~BasePlayer() {} };
class ExtEplayer3: public BasePlayer {
public:
    ExtEplayer3Options mPlayerOptions;
    std::string mPath;
    HeaderMap mHeaders;
    ExtEplayer3(ExtEplayer3Options &options): mPlayerOptions(options) {}
    std::vector<std::string> buildCommand();
};
class GstPlayer: public BasePlayer {
public:
    GstPlayerOptions mPlayerOptions;
    std::string mPath;
    HeaderMap mHeaders;
    GstPlayer(GstPlayerOptions &options): mPlayerOptions(options) {}
    std::vector<std::string> buildCommand();
};
struct eServiceReference { int type; std::string path; };
struct eServiceFactoryApp { enum { idServiceMP3=4097, idServiceGstPlayer=5001, idServiceExtEplayer3=5002 }; };
HeaderMap getHeaders(const std::string &) { return HeaderMap(); }
HeaderMap serviceHeaders(const std::string &) { return HeaderMap(); }
static std::map<std::string, HeaderMap> g_stream_settings;
'''
code += section(read('serviceapp.h'), 'struct eServiceAppOptions', '#if SIGCXX_MAJOR_VERSION')
code += section(ext, 'std::vector<std::string> ExtEplayer3::buildCommand()', 'int ExtEplayer3::start(')
code += section(gst, 'std::vector<std::string> GstPlayer::buildCommand()', 'int GstPlayer::start(')
code += section(service, 'enum\n{', 'static const std::string gReplaceServiceMP3Path')
code += section(service, 'static void updatePlayerOptions', 'class eServiceOfflineOperations')
bridge = '#include <Python.h>\n' + section(service,
    'static PyObject *playback_profile_set_setting', 'static PyMethodDef serviceappMethods')
policy_code = code
code += (Path(__file__).parent / 'playback_checks.cpp').read_text()
build_dir = os.environ.get('SERVICEAPP_TEST_BUILD_DIR')
with (nullcontext(build_dir) if build_dir else tempfile.TemporaryDirectory(prefix='serviceapp-check-')) as tmp:
    path = Path(tmp)
    (path / 'check.cpp').write_text(code)
    exe = path / ('check.exe' if os.name == 'nt' else 'check')
    for bundled in (False, True):
        defines = ['-DSERVICEAPP_BUNDLED_EXTEPLAYER3'] if bundled else []
        subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++11', '-Wall', '-Wextra',
                        *defines, '-I' + str(SRC), str(path / 'check.cpp'), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    # Compile the additive native Python API against real Python headers too.
    (path / 'bridge.cpp').write_text(policy_code + bridge)
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++11', '-Wall', '-Wextra',
                    '-Wno-unused-parameter', '-fsyntax-only', '-I' + str(SRC),
                    '-I' + sysconfig.get_path('include'), str(path / 'bridge.cpp')], check=True)
    print('Native Python bridge syntax check passed')
