#!/bin/sh
# PiconUpdater – safe GitHub installer/updater
# Public installation command remains unchanged:
# wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh

set -e

PLUGIN_PARENT="/usr/lib/enigma2/python/Plugins/Extensions"
PLUGIN_PATH="$PLUGIN_PARENT/PiconUpdater"
REPO_URL="https://github.com/OliOli2013/PiconUpdater/archive/refs/heads/main.zip"
TMP_BASE="/tmp/piconupdater-install-$$"
TMP_ZIP="$TMP_BASE/main.zip"
TMP_EXTRACT="$TMP_BASE/extract"
STAGE="$PLUGIN_PARENT/.PiconUpdater.new.$$"
BACKUP="$PLUGIN_PARENT/.PiconUpdater.backup.$$"
COMMITTED=0

say() { echo "[PiconUpdater] $*"; }

cleanup() {
    if [ "$COMMITTED" != "1" ]; then
        rm -rf "$STAGE" 2>/dev/null || true
        if [ -d "$BACKUP" ] && [ ! -d "$PLUGIN_PATH" ]; then
            say "Przywracanie poprzedniej wersji..."
            mv "$BACKUP" "$PLUGIN_PATH" 2>/dev/null || true
        fi
    fi
    rm -rf "$TMP_BASE" 2>/dev/null || true
    if [ "$COMMITTED" = "1" ]; then
        rm -rf "$BACKUP" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

say "Instalator PiconUpdater by Paweł Pawełek"
mkdir -p "$TMP_EXTRACT" "$PLUGIN_PARENT"
rm -rf "$STAGE" "$BACKUP"

say "Pobieranie najnowszej wersji z GitHub..."
if command -v wget >/dev/null 2>&1; then
    if ! wget -q -O "$TMP_ZIP" "$REPO_URL"; then
        say "Standardowa weryfikacja TLS nie powiodła się; ponawiam dla starszego obrazu Enigma2."
        wget --no-check-certificate -q -O "$TMP_ZIP" "$REPO_URL"
    fi
elif command -v curl >/dev/null 2>&1; then
    curl -fL --connect-timeout 20 --max-time 120 -o "$TMP_ZIP" "$REPO_URL"
else
    say "BŁĄD: brak wget i curl."
    exit 1
fi

[ -s "$TMP_ZIP" ] || { say "BŁĄD: pobrany plik jest pusty."; exit 1; }
command -v python3 >/dev/null 2>&1 || { say "BŁĄD: wymagany Python 3."; exit 1; }

say "Walidacja i bezpieczne rozpakowanie..."
python3 - "$TMP_ZIP" "$TMP_EXTRACT" <<'PY'
import os, sys, zipfile
archive, out = sys.argv[1], sys.argv[2]
root = "PiconUpdater-main/"
required = {"plugin.py", "ui.py", "catalog.py", "storage.py", "version", "installer.sh"}
seen = set()
with zipfile.ZipFile(archive, "r") as zf:
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if not name.startswith(root):
            continue
        rel = name[len(root):].lstrip("/")
        if not rel or rel.endswith("/"):
            continue
        norm = os.path.normpath(rel)
        if norm.startswith("..") or os.path.isabs(norm):
            raise SystemExit("unsafe ZIP path: %s" % rel)
        dst = os.path.join(out, norm)
        parent = os.path.dirname(dst)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with zf.open(info, "r") as src, open(dst, "wb") as f:
            while True:
                chunk = src.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        seen.add(rel.split("/")[0])
missing = required - seen
if missing:
    raise SystemExit("missing required files: %s" % ", ".join(sorted(missing)))
# Validate syntax without compileall/py_compile – some stripped images do not ship them.
for name in ("__init__.py", "plugin.py", "ui.py", "catalog.py", "storage.py"):
    path = os.path.join(out, name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
print("validated")
PY

say "Przygotowanie nowej wersji..."
mkdir -p "$STAGE"
for name in __init__.py plugin.py ui.py catalog.py storage.py version icon.png catalog_fallback.json custom_sources.json LICENSE changelog README.md THIRD_PARTY.md; do
    if [ -e "$TMP_EXTRACT/$name" ]; then
        cp -a "$TMP_EXTRACT/$name" "$STAGE/"
    fi
done
for name in assets previews_local; do
    if [ -d "$TMP_EXTRACT/$name" ]; then
        cp -a "$TMP_EXTRACT/$name" "$STAGE/"
    fi
done

for required in plugin.py ui.py catalog.py storage.py version; do
    [ -f "$STAGE/$required" ] || { say "BŁĄD: brak $required w stagingu."; exit 1; }
done
chmod 755 "$STAGE" 2>/dev/null || true
find "$STAGE" -type f -exec chmod 644 {} \; 2>/dev/null || true
chmod 755 "$STAGE/installer.sh" 2>/dev/null || true

say "Podmiana wtyczki z możliwością rollback..."
if [ -d "$PLUGIN_PATH" ]; then
    mv "$PLUGIN_PATH" "$BACKUP"
fi
mv "$STAGE" "$PLUGIN_PATH"
COMMITTED=1
sync 2>/dev/null || true

say "Instalacja zakończona: $(cat "$PLUGIN_PATH/version" 2>/dev/null || echo 'nowa wersja')"
say "Restart GUI..."
killall -9 enigma2 2>/dev/null || true
exit 0
