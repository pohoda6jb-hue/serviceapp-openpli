#!/usr/bin/env bash
set -euo pipefail

# Ubuntu 20.04 matches this older OE release's host Python requirements.
source_dir=$(cd "$(dirname "$0")/../.." && pwd)
# base.bbclass excludes S and B from pseudo interception. Keep the OE tree
# outside EXTERNALSRC, otherwise package ownership operations bypass pseudo.
oe_dir="$(dirname "$source_dir")/openpli92-build"
artifact_dir="$source_dir/artifacts"
cache_dir="$source_dir/.openpli-cache"
oe_revision=73ca1f1613f9b84c1bfc08a003bb4a0c59a3e0c0
recipe=enigma2-plugin-systemplugins-serviceapp
mkdir -p "$artifact_dir/logs" "$artifact_dir/package"
mkdir -p "$cache_dir/downloads" "$cache_dir/sstate"
exec > >(tee "$artifact_dir/logs/build.log") 2>&1

collect_logs() {
    status=$?
    if [ -d "$oe_dir/build/tmp/work" ]; then
        find "$oe_dir/build/tmp/work" -type f \( -name 'log.do_*' -o -name 'run.do_configure*' \) \
            -size -2M -print0 | tar --null -T - -czf "$artifact_dir/logs/tasks.tar.gz" || true
    fi
    df -h || true
    exit "$status"
}
trap collect_logs EXIT

git clone --no-checkout https://github.com/OpenPLi/openpli-oe-core.git "$oe_dir"
git -C "$oe_dir" checkout --detach "$oe_revision"
# meta-python2 uses a git:// submodule URL in this release; HTTPS avoids port 9418.
git -C "$oe_dir" config submodule.meta-python2.url https://git.openembedded.org/meta-python2
git -C "$oe_dir" submodule update --init --jobs 4

# OE install tasks run under pseudo (fake root), so Git sees another owner.
# Trust only this job's checked-out sources; never use a wildcard exception.
git config --global --add safe.directory "$source_dir"
git config --global --add safe.directory "$oe_dir"
git -C "$oe_dir" submodule foreach --recursive \
    'git config --global --add safe.directory "$PWD"'

# The 9.2 branding recipe splits a full path at underscores. GitHub's /__w
# prefix makes that field empty; strip the directory before parsing the name.
python3 - "$oe_dir" <<'PY'
from pathlib import Path
import sys
recipe = Path(sys.argv[1]) / 'meta-openpli/recipes-openpli/enigma2/enigma-info.bb'
old = "| cut -d '_' -f 2 | xargs basename -s .bb"
new = "| xargs -r -n 1 basename | cut -d '_' -f 2 | sed 's/\\.bb$//'"
text = recipe.read_text()
if text.count(old) != 1:
    raise SystemExit('Unexpected enigma-info recipe; review the path parsing fix.')
recipe.write_text(text.replace(old, new))
PY

cd "$oe_dir"
MACHINE=vuduo4k make init BB_NUMBER_THREADS=2 PARALLEL_MAKE=-j2 \
    DL_DIR="$cache_dir/downloads" SSTATE_DIR="$cache_dir/sstate"
append_dir="$oe_dir/meta-local/recipes-openpli/serviceapp"
mkdir -p "$append_dir"
cat > "$append_dir/$recipe.bbappend" <<EOF
inherit externalsrc
EXTERNALSRC = "$source_dir"
EXTERNALSRC_BUILD = "\${WORKDIR}/serviceapp-build"
SRCREV = "${SERVICEAPP_COMMIT:-$(git -C "$source_dir" rev-parse HEAD)}"
PV = "1+git177+openplits"
PKGV = "\${PV}"
PR = "r0.1"
# libsigc++ 3 needs C++17; select the verified 9.2 Enigma2 interfaces.
CXXFLAGS_append = " -std=gnu++17"
CPPFLAGS_append = " -DSERVICEAPP_OPENPLI92"
EXTRA_OEMAKE_append = " -k"
EOF
# Build only this package and its compile dependencies, not an entire image/feed.
cat >> build/conf/local.conf <<'EOF'
BB_NUMBER_THREADS = "2"
PARALLEL_MAKE = "-j2"
INHERIT += "rm_work"
# libtool's staged configure is a symlink into its work tree in this release.
RM_WORK_EXCLUDE += "enigma2-plugin-systemplugins-serviceapp libtool-native"
BB_DISKMON_DIRS = "STOPTASKS,${TMPDIR},2G,100K ABORT,${TMPDIR},1G,50K"
EOF
export MACHINE=vuduo4k
cd build
source env.source
if ! bitbake -e "$recipe" > "$artifact_dir/logs/recipe-environment.txt"; then
    tail -n 100 "$artifact_dir/logs/recipe-environment.txt"
    exit 1
fi
# Compile independent translation units even if one fails, to collect all
# remaining interface diagnostics in a single run. A failure still stops packaging.
bitbake -c package_write_ipk "$recipe"

find tmp/deploy -type f -path '*/ipk/*' -name "${recipe}_*.ipk" -exec cp '{}' "$artifact_dir/package/" \;
if ! compgen -G "$artifact_dir/package/*.ipk" > /dev/null; then
    echo 'No runtime IPK was produced.' >&2
    exit 1
fi
{
    printf 'Target: OpenPLi 9.2 / vuduo4k / ARMv7 / Python 3\n'
    printf 'OpenPLi build revision: %s\n' "$oe_revision"
    printf 'ServiceApp revision: %s\n' "$(git -C "$source_dir" rev-parse HEAD)"
    git -C "$oe_dir" submodule status
    printf '\nVerify on the receiver before routine use. No image/player/kernel packages are included.\n'
} > "$artifact_dir/package/BUILD-INFO.txt"
cd "$artifact_dir/package"
sha256sum ./*.ipk > SHA256SUMS
