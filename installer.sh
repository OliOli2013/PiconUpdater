#!/bin/sh
# --- Konfiguracja ---
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PiconUpdater"
REPO_URL="https://github.com/OliOli2013/PiconUpdater/archive/refs/heads/main.zip"
TMP_ZIP="/tmp/piconupdater.zip"
TMP_DIR="/tmp/piconupdater_extract"

echo "-------------------------------------------------"
echo "  Instalator wtyczki PiconUpdater by Pawełek"
echo "-------------------------------------------------"

# 1. Usuwanie starej wersji
if [ -d "$PLUGIN_PATH" ]; then
    echo "[!] Znaleziono starą wersję. Usuwanie..."
    rm -rf "$PLUGIN_PATH"
fi

# 2. Pobieranie najnowszej wersji z GitHub
echo "[*] Pobieranie najnowszej wersji..."
wget --no-check-certificate "$REPO_URL" -O "$TMP_ZIP"

if [ ! -f "$TMP_ZIP" ]; then
    echo "[X] Błąd pobierania! Sprawdź internet."
    exit 1
fi

# 3. Rozpakowywanie
echo "[*] Instalowanie..."
mkdir -p "$TMP_DIR"
unzip -oq "$TMP_ZIP" -d "$TMP_DIR"

# 4. Przenoszenie plików na miejsce
# GitHub po rozpakowaniu ZIP tworzy folder "NazwaRepo-main".
# Przenosimy jego zawartość do docelowego folderu wtyczki.
mkdir -p "$PLUGIN_PATH"
cp -r "$TMP_DIR"/PiconUpdater-main/* "$PLUGIN_PATH"

# 5. Sprzątanie
echo "[*] Czyszczenie plików tymczasowych..."
rm -rf "$TMP_DIR"
rm -f "$TMP_ZIP"

# 6. Restart GUI
echo "-------------------------------------------------"
echo "  Instalacja zakończona sukcesem!"
echo "  Restartowanie GUI za 3 sekundy..."
echo "-------------------------------------------------"
sleep 3
killall -9 enigma2
