#!/bin/bash
# Run only in the disposable Debian Jessie MIPS root on the CI runner.
set -euo pipefail
cd /src
sdk=/src/work/vti-headers
target=/src/work/vti-target/lib
out=/src/work/vti-build
mkdir -p "$out"
gcc -dumpversion | grep -q '^4\.9'
python2.7 -c 'import sys; assert sys.version_info[:3] == (2, 7, 9)'
cd "$sdk/libsigc++-1.2.5"
./configure --disable-dependency-tracking > "$out/sigc-mips-configure.log" 2>&1
make -C sigc++ slot.h signal.h bind.h bind_return.h object_slot.h \
  retype_return.h class_slot.h hide.h retype.h method_slot.h > "$out/sigc-mips-make.log" 2>&1
cd /src
flags=(-std=gnu++11 -O2 -g -fPIC -fno-rtti -fno-strict-aliasing -mips32 -mabi=32 -mfp32 -mhard-float
  -DSERVICEAPP_VTI15 -DHAVE_EPG -D_GLIBCXX_USE_CXX11_ABI=0 -D_FILE_OFFSET_BITS=32
  -include /src/CI/vti/python-ucs2-config.h -include Python.h
  -I /usr/include/python2.7 -I "$sdk/uchar-include"
  -I "$sdk/vuplus" -I "$sdk/vuplus/include" -I "$sdk/dvbsi/include"
  -I /usr/include/freetype2 -I "$sdk/libsigc++-1.2.5"
  -I "$sdk/libsigc++-1.2.5/sigc++/config" -I src/serviceapp)
sources=(serviceapp extplayer scriptrun myconsole wrappers m3u8 gstplayer exteplayer3 common
  subtitles/subtitles subtitles/subrip)
objects=()
for source in "${sources[@]}"; do
  object="$out/${source//\//_}.o"
  echo "MIPS GCC4.9: $source"
  g++ "${flags[@]}" -c "src/serviceapp/$source.cpp" -o "$object"
  objects+=("$object")
done
gcc -O2 -fPIC -mips32 -mabi=32 -mfp32 -mhard-float \
  -c src/serviceapp/cJSON/cJSON.c -o "$out/cJSON.o"
g++ -shared -mips32 -mabi=32 -mfp32 -mhard-float -Wl,--hash-style=sysv \
  -Wl,-soname,serviceapp.so -Wl,-z,now "${objects[@]}" "$out/cJSON.o" \
  -L "$target" -lpython2.7 -lssl -lcrypto -luchardet -lsigc-1.2 \
  -lpthread -ldl -o "$out/serviceapp.so"

# A real MIPS layout probe, independent of Enigma startup or DVB hardware.
cat > "$out/layout.cpp" <<'EOF'
#include <Python.h>
#include <vector>
#include <list>
#include <map>
#include <string>
#include <cstdio>
#include <cstddef>
#define private public
#include <lib/base/ebase.h>
#undef private
int main() {
  static_assert(sizeof(Py_UNICODE) == 2, "VTi Python uses UCS2");
  printf("{\"pointer\":%zu,\"timer_size\":%zu,\"context\":%zu,\"interval\":%zu,\"active\":%zu,\"single\":%zu}\n",
    sizeof(void*), sizeof(eTimer), offsetof(eTimer, context), offsetof(eTimer, interval),
    offsetof(eTimer, bActive), offsetof(eTimer, bSingleShot));
}
EOF
g++ "${flags[@]}" "$out/layout.cpp" -o "$out/layout"
"$out/layout" > "$out/layout.json"

cd /src/work/ffmpeg-3.4.1
./configure --disable-programs --disable-doc --disable-everything --disable-asm \
  --extra-cflags='-mips32 -mabi=32 -mfp32 -mhard-float' > "$out/ffmpeg-configure.log" 2>&1
cd /src/work/vti-exteplayer
base=(main/exteplayer.c container/container.c container/container_ffmpeg.c
  manager/manager.c manager/audio.c manager/video.c manager/subtitle.c
  output/output_subtitle.c output/graphic_subtitle.c external/plugins/src/png.c
  output/output.c output/writer/common/pes.c
  output/writer/common/misc.c output/writer/common/writer.c output/linuxdvb_buffering.c
  playback/playback.c external/ffmpeg/src/bitstream.c external/ffmpeg/src/latmenc.c
  external/ffmpeg/src/mpeg4audio.c external/flv2mpeg4/src/m4vencode.c
  external/flv2mpeg4/src/flvdecoder.c external/flv2mpeg4/src/dcprediction.c
  external/flv2mpeg4/src/flv2mpeg4.c output/linuxdvb_mipsel.c)
# The old .bb recipe still names removed wma.c/h263.c. In this pinned
# revision WMA is in bcma.c and H263 in mpeg4.c; mjpeg.c supplies the
# additional symbols referenced by AvailableWriter. Build every actual
# MIPS writer, rather than copying that stale recipe list.
writers=(writer aac ac3 mp3 pcm lpcm dts amr bcma h265 h264 mpeg2 mpeg4 divx3 vp wmv vc1 mjpeg)
for writer in "${writers[@]}"; do base+=("output/writer/mipsel/$writer.c"); done
# Direct receiver libc ELF inputs do not include the compiler's normal linker
# script. Supply the real archived compiler-root startup support archive too.
# Its imports remain subject to the exact VTi symbol/version check.
libc_startup=$(gcc -print-file-name=libc_nonshared.a)
test -f "$libc_startup"
gcc -std=gnu99 -O2 -mips32 -mabi=32 -mfp32 -mhard-float -D_FILE_OFFSET_BITS=64 \
  -D_LARGEFILE64_SOURCE -D_LARGEFILE_SOURCE -DHAVE_FLV2MPEG4_CONVERTER \
  -I include -I external -I external/flv2mpeg4 -I /src/work/ffmpeg-3.4.1 \
  "${base[@]}" -L "$target" -lpthread -lavformat -lavcodec -lavutil -lswresample \
  -lswscale -ldl "$libc_startup" \
  -Wl,-rpath-link,"$target" -Wl,--hash-style=sysv -o "$out/exteplayer3"
cd /src
python2.7 -m compileall -q src/plugin
python2.7 test/check_python2_streamsettings.py
{ gcc --version | head -n1; python2.7 --version 2>&1; uname -m; } > "$out/compiler.txt"
