# VTi 15.0.04 / VU+ Solo2 port preparation

This branch prepares Python 2.7 persistence and native option handling. It does
not produce or claim a working VTi MIPS package yet. OpenPLi ARM binaries are
not transferable to Solo2.

## Receiver facts supplied 2026-10-13

* `/etc/issue`: `vuplus 3.0.0` (this banner alone does not identify the VTi build).
* `uname -m`: `mips`; accepted packages include `mips32el`, `vusolo2`, `mipsel`.
* Python 2.7.9, `python-core` 2.7.9-r1-vuplus1.
* glibc 2.21-r0, libgcc1 4.9.2-r0, libsigc-1.2-5 1.2.5-r2.
* libavcodec57, libavformat57, libavutil55: VTi001.3.4.1-r14.
* Enigma2, installed ServiceApp/player, libstdc++, OpenSSL and development
  headers remain unconfirmed. The original grep expression contained embedded
  newlines and did not reliably match all requested package names.

The SF8008 player uses libavcodec58/libavformat58/libavutil56 and glibc >=2.33;
that package cannot satisfy this receiver's confirmed ABI requirements.

Required before a receiver package can be validated:

* matching Enigma2 headers and target libraries/sysroot, or a reproducible SDK;
* VTi-specific service virtual interfaces and event numbering;
* Solo2 MIPS hardware output and actual outage/zapping/VOD tests.

The receiver is unavailable. Continue from public sources; further receiver
diagnostics are not a prerequisite for reference research or port preparation.
Feed metadata below describes a build reference, not the installed receiver.

## Public reference audit, 2026-10-13

The official feed configuration package was downloaded and inspected as data:
`distro-feed-configs_1.0-r6-vuplus1-vti-20200910-15.0.04-r7_vusolo2.ipk`.
It reveals separate `static/` feeds containing the base libraries, which are
absent from the much smaller update-only package lists.

Reference feed:
https://vuplus-support.org/openembedded/2.0/vti/20200910_vti-15.0_04_Su4oophuraey/

* `vusolo2/Packages.gz`: Enigma2 `vti-15.0.04-20200921-r01r04`.
* `mips32el/static/Packages.gz`: libstdc++6 4.9.2-r0, libpython2.7-1.0
  2.7.9-r1-vuplus1, libsigc-1.2-5 1.2.5-r2, libcrypto1.0.0 1.0.2a-r0,
  uchardet 0.0.6-r0, gstplayer 0.1-r06, FFmpeg/libav 3.4.1-r14.
* The inspected model/base lists do not contain matching Enigma2 development
  headers. Runtime IPKs provide libraries, not a complete compiler SDK.
* The Enigma2 package's `Source:` points at an internal VTi Git server;
  public Vu+ sources must be compared with the actual VTi interfaces.

`CI/vti/audit_reference.py` downloads the exact official Enigma2 package (or
reads a supplied local copy), checks its pinned SHA256, and inspects its ELF
symbols without running the receiver executable or package scripts. CI saves
the audit report, separately from Python compatibility checks.

Confirmed from the official executable:

* ELF32 little-endian MIPS32 O32, flags `0x50001005`.
* Vtable sizes: iPlayableService 104 bytes; iStaticServiceInformation 60;
  iServiceInformation 52; iStreamedService 32; eTimer/eConnection 24 each.
* `eServiceMP3::setTarget(int)` has one argument.
* `iStaticServiceInformation::getInfoObject(reference,int)` and
  `iServiceInformation::getInfoObject(int)` are exported.
* `eTimer::startLongTimer(int)` and `eConnection::AddRef()/Release()` are
  exported. Do not blindly copy replacement definitions from another port.

Public Vu+ header reference:
https://github.com/OpenVuPlus/dvbapp/tree/847b84273e9696223fd0f50d1957309cfee2caec

Its `lib/service/iservice.h` uses `PyObject*` for streamed buffer charge,
has no `iTapService`, and declares `evEOF` at index 7. Our OpenVision source
currently refers to `iTapService` and `iStreamBufferInfo`; these require a
separate VTi compatibility path before a full native build. The Vu+ source
snapshot is from 2019 and is not claimed to be the exact VTi source.
Matching vtable sizes alone do not certify method order, enum values, timers,
signal layouts, or actual receiver playback.

Run the reference check:

```sh
python3 CI/vti/audit_reference.py --output work/vti-reference-audit.json
```

Reference inspected (not executed or blindly incorporated):
https://github.com/boingbasti/e2-serviceapp-vti

Its README requires a target sysroot which is absent from the repository.
Its MIPS build uses Python 2.7, libsigc++ 1.2 and explicit C++/glibc ABI
compatibility settings. These must be checked against the intended receiver.
The reference includes FFmpeg 6.1.1 changes; upgrading VTi FFmpeg is not implied
or authorized merely by adapting ServiceApp.
Inspected source revision: `94be6a8ed312bedf31e89c55982291fbb1775e49`.

CI checks real Python 2.7 execution and Python C-API syntax, as well as the
existing Python 3 regressions. Those checks do not substitute for a VTi SDK
build or hardware verification.
