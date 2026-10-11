serviceapp [![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html) [![serviceapp](https://github.com/OpenVisionE2/serviceapp/actions/workflows/serviceapp.yml/badge.svg)](https://github.com/OpenVisionE2/serviceapp/actions/workflows/serviceapp.yml) [![ovbot](https://github.com/OpenVisionE2/serviceapp/actions/workflows/ovbot.yml/badge.svg)](https://github.com/OpenVisionE2/serviceapp/actions/workflows/ovbot.yml)
==========
serviceapp service for enigma2

1) opravu MP3 software decoding GUI bug (dts_swdecoding -> mp3_swdecoding),
2) podporu string options v ExtEplayer3Options::update,
3) nové konfigurační volby a menu/profily pro Live TS, HLS, VOD/Auto,
4) zpřístupnění relevantních skrytých voleb live_ts, progressive, nice, mpegts_program_id, ffmpeg_option a GstPlayer ring_buffer_maxsize/download_buffer_path tam, kde dávají smysl,
5) oddělené TS/HLS buffery a reconnect/timeout strategii pokud to aktuální exteplayer3/gstplayer rozhraní reálně podporuje; nevymýšlej neexistující CLI přepínače bez ověření,
6) zachovat bezpečné defaulty a backward compatibility,
7) HLS Explorer ponechat volitelný a preferovat nativní přehrávačový HLS handling,

## TS/HLS profiles and OpenPLi

### Build a Duo 4K package on GitHub

The **OpenPLi 9.2 Duo 4K package** Actions workflow builds only ServiceApp and
its compile dependencies against the pinned OpenPLi `release-9.2` metadata
(`73ca1f1613f9b84c1bfc08a003bb4a0c59a3e0c0`), using Ubuntu 20.04 and
`MACHINE=vuduo4k`. It does not build a new image or install anything on a receiver.
The older release is deliberately separate from current scarthgap metadata.

Changes to the workflow/build script on the feature branch start a build.
After the workflow is available on the default branch, Actions -> this workflow
-> Run workflow also allows manual builds of a selected branch. Download the
`serviceapp-openpli92-vuduo4k` artifact only from a successful run; it contains
the runtime IPK, source revisions and SHA256 checksums. Logs are saved separately
on failure. Artifacts expire after 14 days. An initial build may exceed a hosted
runner's disk/time limits; failures do not produce an installable package.

Downloads and OpenEmbedded shared-state tasks are restored from GitHub cache
before each build and saved even after a build failure. Each attempt writes a
new cache entry, so later attempts can reuse newly completed dependencies.
Cache keys isolate the pinned 9.2 metadata, Ubuntu host and Duo 4K target.
BitBake still checks task signatures and rebuilds changed tasks; this is not a
resume of a stopped compiler process. The first run has no cache, and GitHub
can evict caches under its storage/retention limits.

This package targets Duo 4K, not Duo 4K SE or Dreambox DM8000. Before installing,
keep a receiver backup and a copy of the original ServiceApp package, and check
the new package's dependencies against the receiver. Build success does not
replace actual audio/video, seeking and network recovery tests on OpenPLi 9.2.

Each service type (4097 when replaced, 5001, 5002) has its own **Playback
profile**. Selecting a profile does not switch the player or replace Enigma2's
ServiceMP3. The existing replacement and player settings still control that.

| Profile | ExtEplayer3 | GstPlayer | HLS Explorer |
| --- | --- | --- | --- |
| Legacy (default) | Existing settings; optional advanced Live TS | Existing buffer settings | Existing saved setting |
| Auto | HTTP(S) `.ts` -> Live TS; `.m3u8` -> HLS; otherwise VOD | Separate TS/HLS buffer settings | Off unless explicitly enabled for HLS |
| Live TS | `-v`, player-native live TS handling | TS buffer size/duration | Off |
| HLS | Original playlist sent to FFmpeg; no `-v` | HLS buffer size/duration | Off by default; optional variant selection |
| VOD | No live TS mode; player handles seeking/EOF | Existing VOD buffer; optional disk download buffer | Off |

Auto ignores query strings and service option fragments and matches extensions
case-insensitively. It does not inspect content, guess from `/live/`, or classify
local `.ts` recordings as live streams. Use an explicit profile for extensionless
or token-only URLs, a VOD `.ts` URL, or a resolver URL. Profiles are selected when
the service is created, before any external URL resolver runs.

TS and HLS GstPlayer buffers are independently configurable in KB and seconds.
Both initially use 8192 KB / 0 seconds to preserve the established allocation;
zero duration leaves the GStreamer default. These are not promises about startup
buffer thresholds, latency or HLS segment counts. Test smaller TS buffers on the
actual receiver before using them routinely. ExtEplayer3 has no verified generic
TS/HLS network buffer size switch in this ServiceApp interface; GstPlayer's buffer
settings are not sent to ExtEplayer3.

### GstPlayer interface on OpenPLi

Choose **GstPlayer interface -> OpenPLi positional interface** for the e2i/gstplayer
used by OpenPLi's recipe. The upstream ServiceApp flags interface remains the
default for existing compatible binaries. Choosing the interface is explicit;
the reported JSON version alone is not reliable capability detection.

The OpenPLi command is an argv vector in this order:

```
gstplayer_gst-1.0 URL audio_index timeout_ms is_live download_template ring_MB duration_s size_KB Header=Value ...
```

The adapter uses audio index -1 unless overridden and timeout/is_live 0. OpenPLi
disables ifdsrc by default; its download timeout is specific to that source, not
a general HTTP reconnect policy. Sink and embedded-subtitle enable switches are
not present in the positional interface, so those GUI rows are hidden. ServiceApp
still provides its normal audio/subtitle track commands and selection policy.

### Advanced settings

**Show advanced options** reveals only controls relevant to the current profile.
Empty advanced text/default selections restore the player's constructor defaults.
All settings, including rows hidden after a profile change, are saved or cancelled
together. Existing Python setter signatures and stored configuration keys remain.

* `live_ts`: `-v`, enabled by Live TS; exposed directly in Legacy.
* `progressive`: `-o 0` / `-o 1`; the player requires a value. Leave at player
  default unless a particular progressive-download source requires it.
* `nice`: `-p VALUE`; GUI permits 0..19 (higher means lower priority). Player default
  is unchanged. Per-service overrides also accept -20..19; negative values need
  the operating system's priority permission and are not a streaming preset.
* `mpegts_program_id`: `-P ID`; GUI zero means leave the selection unset.
* `ffmpeg_option`: `-f key=value`. Multiple entries separated by semicolons become
  repeated `-f` arguments. Keys must contain only letters, digits or underscores;
  values must be nonempty and cannot contain NUL or the semicolon separator.
  Values containing spaces remain a single argv element. They are never shell
  commands. Empty GUI text clears an earlier setting.
* GstPlayer `ring_buffer_maxsize` / `download_buffer_path`: VOD disk buffering,
  in MB plus an absolute GLib temporary-file template ending in `XXXXXX`, e.g.
  `/media/hdd/serviceapp-XXXXXX`. The target directory must already exist and be
  writable. In the verified OpenPLi backend both values are required to enable
  download buffering. Both are removed for TS/HLS profiles. The compatible flags
  adapter retains ServiceApp's `-r` / `-p` mapping.

Per-service `sapp_` options still override profile-derived player settings, e.g.
`sapp_live_ts=0` or `sapp_buffer_size=4096`. `sapp_profile=ts|hls|vod|auto|legacy`
can override the selected profile for one service. Use the existing ServiceApp
fragment/header syntax and URL encoding for values; `sapp_` entries are removed
from outgoing HTTP headers. A profile changes live mode/buffers/Explorer only;
it does not reset user-selected audio decoding or advanced FFmpeg options.

### Reconnect and timeout limits

The inspected ExtEplayer3 copies `-f` options into an AVFormat dictionary, then
sets HTTP(S) `timeout=20000000` and `reconnect=1` itself. Live TS additionally sets
`seekable=0`, `reconnect_at_eof=1`, and `reconnect_streamed=1`. Therefore GUI knobs
claiming to disable reconnect or freely replace that timeout would be misleading.
This change uses the player's existing strategy and does not add restart loops,
unlimited retry claims, or unsupported CLI flags. EOF reconnect is not enabled
for native HLS or VOD by the ServiceApp profiles.

Advanced `reconnect_delay_max=4` or `rw_timeout=10000000` are examples of FFmpeg
dictionary options, not defaults or guarantees. Only use them after checking
the linked FFmpeg version and source protocol. `rw_timeout` uses microseconds;
propagation into HLS segment requests depends on that FFmpeg build. There is no
verified general reconnect control in the OpenPLi GstPlayer interface.

### Source audit and validation

CLI audit used these primary sources (the receiver's installed binaries may differ):

* [OpenPLi recipes, scarthgap](https://github.com/OpenPLi/openpli-oe-core/tree/c09e297db976e44280ac53420760515b2e416331/meta-openpli/recipes-multimedia):
  exteplayer3 from oe-mirrors and GstPlayer from gitlab.com/e2i/gstplayer, including
  the patch disabling ifdsrc's timeout.
* [ExtEplayer3 CLI](https://github.com/oe-mirrors/exteplayer3/blob/e258b47863fae1d74dbd1d707c948ae4232fea64/main/exteplayer.c)
  and [HTTP defaults](https://github.com/oe-mirrors/exteplayer3/blob/e258b47863fae1d74dbd1d707c948ae4232fea64/container/container_ffmpeg.c).
* [OpenPLi GstPlayer CLI](https://gitlab.com/e2i/gstplayer/-/blob/a289516735c506c5db3b8ab146d3cd3db2674ddc/common/gstplayer.c)
  and [GStreamer backend](https://gitlab.com/e2i/gstplayer/-/blob/a289516735c506c5db3b8ab146d3cd3db2674ddc/gst-1.0/gst-backend.c).
* [FFmpeg protocol options](https://ffmpeg.org/ffmpeg-protocols.html#http).

Run portable checks with Python 3 and a C++11 compiler (`CXX` may override `g++`):

```
python3 -m compileall -q src/plugin test
python3 test/test_plugin.py
python3 test/check_playback.py
```

The C++ harness compiles unchanged production option parsing, argv generation,
profile application and additive Python API against minimal Enigma2 shims. It
tests URL classification, string values/spaces, progressive arguments, range
validation, native HLS, independent buffers and service override precedence.
It does not link the complete Enigma2 module or play media. A full build needs
the receiver's OpenPLi SDK (Enigma2, Python development files, uchardet and OpenSSL).
No OpenPLi 9.2 hardware or exact installed-player capability check was available
for this patch; cross-build and receiver playback remain release gates.

On the target OpenPLi 9.2 receiver, compare Legacy and the new profiles using the
same streams: TS/HLS zap time, sustained playback, short network interruption
and recovery, HLS master/media playlists with tokens, audio switching, VOD seeking
and EOF, and cancellation of changed settings. Include the installed player and
FFmpeg versions in results. No merge or deployment is performed by these checks.
