# VU+ Zero 4K / OpenPLi 9.2 test build

The user confirmed OpenPLi 9.2 on VU+ Zero 4K. The build uses
`MACHINE=vuzero4k`, not the Duo4K package or the non-4K `vuzero` target.

The pinned OpenPLi 9.2 revision is
`73ca1f1613f9b84c1bfc08a003bb4a0c59a3e0c0`, whose meta-vuplus submodule is
`7de0306aa67b26e9402fb83de9103b957b2fa6cb`.
[vuzero4k.conf](https://github.com/OpenPLi-meta/meta-vuplus/blob/7de0306aa67b26e9402fb83de9103b957b2fa6cb/conf/machine/vuzero4k.conf)
selects BCM72604 and includes
[vuxxo4k.inc](https://github.com/OpenPLi-meta/meta-vuplus/blob/7de0306aa67b26e9402fb83de9103b957b2fa6cb/conf/machine/include/vuxxo4k.inc),
which sets `TARGET_ARCH=arm` and `DEFAULTTUNE=armv7ahf-neon`.

ServiceApp is compiled against that receiver's Enigma2/Python 3.9 SDK.
It requires the separate `exteplayer3-serviceapp` package, whose executable is
`/usr/bin/exteplayer3-serviceapp`. An existing `/usr/bin/exteplayer3` remains
available to other plugins; its installed version on this receiver is unknown.
The GUI player name remains `exteplayer3`. The companion source is the same
audited series 69 and live-stream patch as in the Duo4K test build.

The package audit requires `vuzero4k` for ServiceApp and `armv7ahf-neon` or
`vuzero4k` for the player, native ARM EABI5 hard-float binaries, the exact
companion install path, and its dependency/name in ServiceApp. Only one receiver
is built per run. The ZIP contains both IPKs, provenance, checksums and a Czech
installation/test guide. FFmpeg, receiver drivers and an image are not bundled.

Playback on Zero 4K remains untested. Live recovery is opt-in, finite and handles
an exited player; it cannot recover a frozen player whose process stays alive.
Use native HLS handling and test TS/HLS interruptions, channel changes and VOD
as described in `CTI-NEJDRIV.txt` and [TESTING.md](TESTING.md).
