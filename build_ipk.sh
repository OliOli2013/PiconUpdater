#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
VERSION="$(cat "$ROOT/version")"
OUT="${1:-$ROOT/dist}"
WORK="${TMPDIR:-/tmp}/piconupdater-ipk-$$"
PKG="$WORK/pkg"
CTRL="$WORK/control"
mkdir -p "$OUT" "$PKG/usr/lib/enigma2/python/Plugins/Extensions/PiconUpdater" "$CTRL"
DEST="$PKG/usr/lib/enigma2/python/Plugins/Extensions/PiconUpdater"
for f in __init__.py plugin.py ui.py catalog.py storage.py version icon.png catalog_fallback.json custom_sources.json LICENSE changelog README.md THIRD_PARTY.md; do
    [ ! -e "$ROOT/$f" ] || cp -a "$ROOT/$f" "$DEST/"
done
for d in assets previews_local; do
    [ ! -d "$ROOT/$d" ] || cp -a "$ROOT/$d" "$DEST/"
done
cat > "$CTRL/control" <<EOF
Package: enigma2-plugin-extensions-piconupdater
Version: $VERSION
Section: base
Priority: optional
Architecture: all
Maintainer: Paweł Pawełek
Depends: enigma2, python3
Description: PiconUpdater 2 - dynamic picons/picons catalog, filters and installer for Enigma2
OE: enigma2-plugin-extensions-piconupdater
Homepage: https://github.com/OliOli2013/PiconUpdater
License: MIT
EOF
printf '2.0\n' > "$WORK/debian-binary"
( cd "$CTRL" && tar -czf "$WORK/control.tar.gz" . )
( cd "$PKG" && tar -czf "$WORK/data.tar.gz" . )
python3 - "$WORK" "$OUT/enigma2-plugin-extensions-piconupdater_${VERSION}_all.ipk" <<'PY'
import os, sys, time
work, out = sys.argv[1], sys.argv[2]
files = ['debian-binary','control.tar.gz','data.tar.gz']
def header(name, size):
    # SysV ar header: 16/12/6/6/8/10 + magic
    return ('%-16s%-12d%-6d%-6d%-8o%-10d`\n' % (name+'/', int(time.time()), 0, 0, 0o100644, size)).encode('ascii')
with open(out,'wb') as dst:
    dst.write(b'!<arch>\n')
    for name in files:
        path=os.path.join(work,name); data=open(path,'rb').read()
        dst.write(header(name,len(data))); dst.write(data)
        if len(data)%2: dst.write(b'\n')
print(out)
PY
rm -rf "$WORK"
