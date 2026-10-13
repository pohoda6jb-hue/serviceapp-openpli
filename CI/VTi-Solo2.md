# VTi 15.0.04 / VU+ Solo2 experimental port

This branch produces experimental MIPS test packages with Python 2.7 persistence
and native option handling. The build and selected static ABI checks pass;
receiver playback remains untested. OpenPLi ARM binaries are not transferable
to Solo2.

Successful target build, source revision
`8058a0752c0e155f4d748110201213084d28eced`:
https://github.com/pohoda6jb-hue/serviceapp-openpli/actions/runs/38461744227

Test package artifact:
https://github.com/pohoda6jb-hue/serviceapp-openpli/actions/runs/38461744227/artifacts/11847790242

GCC 4.9.2 and Python 2.7.9 compiled both native components. The static audit
resolved all 275 strong ServiceApp imports and 158 player imports against the
official VTi reference, verified MIPS32 O32 hard-float FP32, the Python UCS2
configuration and the selected timer fields. The downloaded bundle's checksums,
IPK controls, install paths and native MIPS payloads were also checked.

## Receiver facts supplied 2026-10-13

* `/etc/issue`: `vuplus 3.0.0` (this banner alone does not identify the VTi build).
* `uname -m`: `mips`; accepted packages include `mips32el`, `vusolo2`, `mipsel`.
* Python 2.7.9, `python-core` 2.7.9-r1-vuplus1.
* glibc 2.21-r0, libgcc1 4.9.2-r0, libsigc-1.2-5 1.2.5-r2.
* libavcodec57, libavformat57, libavutil55: VTi001.3.4.1-r14.
* Follow-up package listing: Enigma2 `vti-15.0.04-20200921-r01r04`,
  libstdc++6 4.9.2-r0, libssl1.0.0/libcrypto1.0.0 1.0.2a-r0.
  This is the same Enigma2 package version as the downloaded reference.
* No ServiceApp, exteplayer3 or uchardet entries appear in the supplied listing.
  The `gstplayer` search word was split by a newline, so its absence cannot be
  established from this filtered output. Do not infer gstplayer is installed.
* Receiver checks explicitly confirm missing Enigma2/Python development headers
  and `enigma2.pc`. A build environment must be assembled separately.

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
has no `iTapService`, and declares `evEOF` at index 7. An explicit
`SERVICEAPP_VTI15` path selects these older interfaces, checks the EOF index,
and retains the one-argument `setTarget` prototype. It also rejects libsigc++
2/3 for this target. The Vu+ source
snapshot is from 2019 and is not claimed to be the exact VTi source.
Matching vtable sizes alone do not certify method order, enum values, timers,
signal layouts, or actual receiver playback.

`CI/vti/check_vuplus_headers.sh` checks production native code on a Linux host
with Python 2.7, libsigc++ 1.2.5, uchardet 0.0.6 and these pinned public Vu+
headers. The public subtitle declarations are updated from OpenPLi because
the official VTi executable exports the newer `iSubtitleUser`/`SubtitleTrack`
methods; the audit checks these exports too. No timer offsets or padding are
invented to make this check pass. This syntax
check is not a MIPS target link or an assertion that public Vu+ and closed VTi
have identical object layouts. The MIPS build must explicitly set
`-DSERVICEAPP_VTI15` (or configure with `--enable-vti15`); the default
OpenPLi/OpenVision path is unchanged apart from returning a defined unsupported
result from the existing buffer-size stub.

The VTi path also uses two-argument message-pump constructors, default integer
packets for the older receive implementation, the exported
`ePythonConfigQuery::getConfigIntValue` for subtitle settings, and no unavailable
`sBuffer` info enum. Public deallocation forwarding for the console and service
factory preserves normal global delete while allowing construction against the
legacy protected `iObject::operator delete` declaration.

The build SDK also exposes the inherited inline deallocation forwarder for
GCC 4.9 constructor exception cleanup. This changes access control only;
the destructor remains protected, with no added fields or virtual methods.
The VTi EPG path uses the system clock (`time(NULL)`), as public Vu+ synchronizes
that clock and does not provide OpenPLi's `nowTime()` method.

## Native MIPS build and packaging gates

`.github/workflows/vti-solo2-build.yml` runs the native MIPS GCC 4.9.2 compiler
under QEMU in a disposable archived Debian Jessie root. Python 2.7.9 is checked
there too. A reusable cache stores only this compiler root. Source code and
the exact official VTi libraries are fetched and verified on every build.
The VM has older glibc headers; candidates are linked with the official VTi
library files and checked against their exported symbol versions.

`prepare_target.py` obtains the actual codec dependency closure from the official
feed. Linker and loader aliases come from ELF SONAMEs, including glibc libraries
whose filenames differ from their loader names. FFmpeg 3.4.1 source supplies the
headers for exteplayer3; FFmpeg libraries are neither rebuilt nor upgraded.

Before packaging, `validate_target.py` checks ELF32 little-endian MIPS32 O32,
hard-float FP32, receiver loader, runtime dependencies, strong symbol imports
and their versions, Python 2 initializer, and absence of embedded build paths.
A MIPS layout probe is compared with the timer's field accesses in the pinned
official Enigma executable. These are selected static compatibility checks,
not a substitute for receiver testing or proof of every closed VTi interface.

The official VTi Python library exports the UCS2 Unicode API; Debian's
same-version 2.7.9 headers default to UCS4. The build-only
`python-ucs2-config.h` configures both the API names and the real `Py_UNICODE`
type as two-byte unsigned short, following CPython 2.7.9's `unicodeobject.h`.
It does not alias missing symbols, replace runtime functions, or change Python
on the receiver. The MIPS probe asserts the type size and the import check
rejects a different reference Python Unicode ABI. Actual VTi development
headers are absent from the inspected feed; this is a documented configuration
adaptation of the compiler root's same-version headers.

Only successful candidates produce test IPKs and a ZIP with instructions,
checksums, compiler details and the static audit. The ServiceApp package requires
the exact confirmed Enigma version. It does not restart Enigma automatically.
Live recovery remains opt-in and handles player process exit; a player that stays
running while frozen is not covered by this mechanism.

For IPTV service type 4097, the main ServiceApp settings must select ServiceApp
and exteplayer3, followed by a GUI restart. Type 5002 selects exteplayer3 directly.
Saving a per-stream profile alone does not switch a native Enigma service to
ServiceApp. HLS Explorer remains optional; use native player HLS for the tests.

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
