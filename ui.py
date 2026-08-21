# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import tempfile
import threading
import time

try:
    import queue
except ImportError:
    import Queue as queue

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
try:
    from Screens.Console import Console
except Exception:
    Console = None
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Language import language
from enigma import eTimer, ePicLoad, getDesktop

from .catalog import (
    PLUGIN_VERSION, CACHE_FILE, get_catalog, load_state, save_state,
    newest_published, item_flags, type_label, scope_label, background_label,
    logo_label, remote_plugin_version, semver_tuple, download_file,
    scope_satellites, satellite_label, item_supports_satellite,
)
from .storage import storage_targets, target_by_id, free_space, validate_package, estimate_install_bytes, install_package, clear_picons

PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_URL = "https://olioli2013.github.io/aio-iptv-projekt/"
INSTALL_COMMAND = "wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"

TEXT = {
    "pl": {
        "title": "PiconUpdater",
        "loading": "Ładowanie katalogu piconów…",
        "exit": "Wyjście",
        "install": "Instaluj",
        "filters": "Filtry",
        "refresh": "Odśwież",
        "empty": "Brak pakietów dla wybranych filtrów.",
        "filter_summary": "Filtry",
        "catalog_online": "Katalog GitHub: aktualny",
        "catalog_cache": "Katalog: pamięć podręczna",
        "catalog_fallback": "Katalog awaryjny",
        "catalog_changes": "nowe: %d • aktualizacje: %d",
        "plugin_update": "Nowa wersja wtyczki: %s",
        "plugin_current": "Wtyczka aktualna: %s",
        "source": "Źródło",
        "ptype": "Typ",
        "scope": "Pakiet / zakres",
        "satellite": "Konkretny satelita",
        "satellite_all": "Cała paczka / bez filtrowania",
        "satellite_note": "Filtr konkretnego satelity działa dla SRP i instaluje tylko picony z wybranej pozycji orbitalnej.",
        "size": "Rozmiar picon",
        "padding": "Pole logo",
        "logo": "Styl logo",
        "background": "Tło",
        "release": "Wydanie",
        "package_size": "Rozmiar paczki",
        "location": "Instalacja",
        "status": "Status",
        "new": "NOWE",
        "latest": "NAJNOWSZE",
        "update": "AKTUALIZACJA",
        "installed": "ZAINSTALOWANE",
        "normal": "Dostępne",
        "confirm_install": "Zainstalować wybrany zestaw piconów?\n\n%s\n\nLokalizacja: %s\n\nUWAGA: po poprawnym pobraniu i sprawdzeniu paczki obecne picony w tej lokalizacji zostaną usunięte, a następnie zainstalowany zostanie nowy zestaw.",
        "clearing_old": "Usuwanie poprzednich piconów",
        "downloading": "Pobieranie: %s",
        "installing": "Instalowanie piconów: %s",
        "installed_ok": "Zainstalowano %d piconów.\nLokalizacja: %s%s",
        "busy": "Operacja jest w toku. Poczekaj na jej zakończenie.",
        "error": "Błąd",
        "tools": "Narzędzia PiconUpdater",
        "tool_update": "Aktualizacja / reinstalacja wtyczki",
        "tool_qr": "Strona projektu / kod QR",
        "tool_clear_cache": "Wyczyść cache katalogu",
        "tool_clear_picons": "Wyczyść picony w wybranej lokalizacji",
        "clear_cache_ok": "Cache katalogu został usunięty.",
        "confirm_clear": "Usunąć wszystkie pliki PNG z lokalizacji?\n%s\n\nTa operacja nie ma cofnięcia.",
        "clear_ok": "Usunięto %d plików PNG.",
        "confirm_plugin_update": "Uruchomić bezpieczny instalator z Twojego repozytorium GitHub?\n\n%s",
        "filter_title": "Filtry katalogu piconów",
        "all": "Wszystkie",
        "apply": "Zastosuj",
        "reset": "Reset",
        "cancel": "Anuluj",
        "qr_title": "PiconUpdater – strona projektu",
        "qr_hint": "Zeskanuj kod QR telefonem lub wpisz adres w przeglądarce.",
        "legacy_note": "SNP jest trybem legacy; projekt picons nie aktualizuje już indeksów SNP.",
    },
    "en": {
        "title": "PiconUpdater",
        "loading": "Loading picon catalog…",
        "exit": "Exit",
        "install": "Install",
        "filters": "Filters",
        "refresh": "Refresh",
        "empty": "No packages match the selected filters.",
        "filter_summary": "Filters",
        "catalog_online": "GitHub catalog: current",
        "catalog_cache": "Catalog: cache",
        "catalog_fallback": "Fallback catalog",
        "catalog_changes": "new: %d • updates: %d",
        "plugin_update": "Plugin update available: %s",
        "plugin_current": "Plugin is current: %s",
        "source": "Source",
        "ptype": "Type",
        "scope": "Package / scope",
        "satellite": "Specific satellite",
        "satellite_all": "Whole package / no filtering",
        "satellite_note": "Specific-satellite filtering is available for SRP and installs only picons from the selected orbital position.",
        "size": "Picon size",
        "padding": "Logo area",
        "logo": "Logo style",
        "background": "Background",
        "release": "Release",
        "package_size": "Package size",
        "location": "Install to",
        "status": "Status",
        "new": "NEW",
        "latest": "LATEST",
        "update": "UPDATE",
        "installed": "INSTALLED",
        "normal": "Available",
        "confirm_install": "Install the selected picon set?\n\n%s\n\nLocation: %s\n\nNOTE: after the package is downloaded and verified, current picons in this location will be removed before the new set is installed.",
        "clearing_old": "Removing previous picons",
        "downloading": "Downloading: %s",
        "installing": "Installing picons: %s",
        "installed_ok": "Installed %d picons.\nLocation: %s%s",
        "busy": "An operation is still running. Please wait.",
        "error": "Error",
        "tools": "PiconUpdater tools",
        "tool_update": "Update / reinstall plugin",
        "tool_qr": "Project website / QR code",
        "tool_clear_cache": "Clear catalog cache",
        "tool_clear_picons": "Clear picons in selected location",
        "clear_cache_ok": "Catalog cache removed.",
        "confirm_clear": "Delete all PNG files from this location?\n%s\n\nThis cannot be undone.",
        "clear_ok": "Removed %d PNG files.",
        "confirm_plugin_update": "Run the safe installer from your GitHub repository?\n\n%s",
        "filter_title": "Picon catalog filters",
        "all": "All",
        "apply": "Apply",
        "reset": "Reset",
        "cancel": "Cancel",
        "qr_title": "PiconUpdater – project website",
        "qr_hint": "Scan the QR code with your phone or enter the address in a browser.",
        "legacy_note": "SNP is legacy; the picons project no longer updates SNP indexes.",
    },
}


def _lang():
    try:
        return "pl" if (language.getLanguage() or "")[:2].lower() == "pl" else "en"
    except Exception:
        return "en"


def _t(key):
    lang = _lang()
    return TEXT.get(lang, TEXT["en"]).get(key, key)


def _desktop():
    try:
        sz = getDesktop(0).size()
        return int(sz.width()), int(sz.height())
    except Exception:
        return 1280, 720


def _human_bytes(value):
    try:
        value = float(value or 0)
    except Exception:
        return "—"
    units = ["B", "KB", "MB", "GB"]
    idx = 0
    while value >= 1024.0 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    if idx == 0:
        return "%d %s" % (int(value), units[idx])
    return "%.1f %s" % (value, units[idx])


def _short_scope(scope):
    if not scope:
        return "—"
    if scope == "full":
        return "FULL"
    if scope == "iptv-pl":
        return "IPTV PL"
    return scope.upper().replace(".", "+")


def _main_skin():
    w, h = _desktop()
    if w <= 1024 or h <= 576:
        return """
        <screen position="center,center" size="900,560" title="PiconUpdater" backgroundColor="#0B0F14">
            <eLabel position="0,0" size="900,560" backgroundColor="#0B0F14" zPosition="-10" />
            <eLabel position="0,0" size="900,76" backgroundColor="#121824" zPosition="-2" />
            <widget name="qr_small" position="14,12" size="52,52" pixmap="{qr}" alphatest="blend" scale="1" />
            <widget name="site" position="76,10" size="360,24" font="Regular;16" foregroundColor="#00C2FF" transparent="1" />
            <widget name="catalog_status" position="76,38" size="360,22" font="Regular;15" foregroundColor="#A9B4C2" transparent="1" />
            <widget name="title" position="450,12" size="430,30" font="Regular;25" halign="right" foregroundColor="#00C2FF" transparent="1" />
            <widget name="plugin_status" position="450,44" size="430,18" font="Regular;15" halign="right" foregroundColor="#FFD200" transparent="1" />
            <eLabel position="0,74" size="900,2" backgroundColor="#00C2FF" />
            <widget name="picon_list" position="16,90" size="540,338" itemHeight="34" font="Regular;17" scrollbarMode="showOnDemand" foregroundColor="#D7DEE9" foregroundColorSelected="#FFFFFF" backgroundColor="#0B0F14" backgroundColorSelected="#18364A" transparent="0" />
            <eLabel position="568,90" size="2,338" backgroundColor="#203346" />
            <widget name="preview" position="590,96" size="280,168" alphatest="blend" scale="1" />
            <widget name="details" position="584,276" size="300,152" font="Regular;15" foregroundColor="#D7DEE9" transparent="1" />
            <widget name="filters_summary" position="16,438" size="868,44" font="Regular;15" foregroundColor="#00C2FF" backgroundColor="#121824" transparent="0" valign="center" />
            <eLabel position="0,492" size="900,68" backgroundColor="#121824" zPosition="-1" />
            <eLabel position="16,500" size="120,28" backgroundColor="#B71C1C" zPosition="1" />
            <eLabel position="148,500" size="120,28" backgroundColor="#167A37" zPosition="1" />
            <eLabel position="280,500" size="120,28" backgroundColor="#B89300" zPosition="1" />
            <eLabel position="412,500" size="120,28" backgroundColor="#1556A8" zPosition="1" />
            <widget name="key_red" position="16,500" size="120,28" font="Regular;17" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_green" position="148,500" size="120,28" font="Regular;17" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_yellow" position="280,500" size="120,28" font="Regular;17" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_blue" position="412,500" size="120,28" font="Regular;17" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="operation" position="548,500" size="336,28" font="Regular;15" halign="right" valign="center" foregroundColor="#FFD200" transparent="1" />
            <widget name="footer" position="16,536" size="868,18" font="Regular;13" halign="center" foregroundColor="#8A94A6" transparent="1" />
        </screen>""".format(qr=os.path.join(PLUGIN_PATH, "assets", "qr_site_small.png"))
    if w <= 1280 or h <= 720:
        return """
        <screen position="center,center" size="980,620" title="PiconUpdater" backgroundColor="#0B0F14">
            <eLabel position="0,0" size="980,620" backgroundColor="#0B0F14" zPosition="-10" />
            <eLabel position="0,0" size="980,84" backgroundColor="#121824" zPosition="-2" />
            <widget name="qr_small" position="16,14" size="54,54" pixmap="{qr}" alphatest="blend" scale="1" />
            <widget name="site" position="82,12" size="400,24" font="Regular;17" foregroundColor="#00C2FF" transparent="1" />
            <widget name="catalog_status" position="82,42" size="400,22" font="Regular;16" foregroundColor="#A9B4C2" transparent="1" />
            <widget name="title" position="500,12" size="460,34" font="Regular;28" halign="right" foregroundColor="#00C2FF" transparent="1" />
            <widget name="plugin_status" position="500,48" size="460,20" font="Regular;16" halign="right" foregroundColor="#FFD200" transparent="1" />
            <eLabel position="0,82" size="980,2" backgroundColor="#00C2FF" />
            <widget name="picon_list" position="18,100" size="590,376" itemHeight="38" font="Regular;18" scrollbarMode="showOnDemand" foregroundColor="#D7DEE9" foregroundColorSelected="#FFFFFF" backgroundColor="#0B0F14" backgroundColorSelected="#18364A" transparent="0" />
            <eLabel position="620,100" size="2,376" backgroundColor="#203346" />
            <widget name="preview" position="650,108" size="300,180" alphatest="blend" scale="1" />
            <widget name="details" position="638,302" size="324,174" font="Regular;16" foregroundColor="#D7DEE9" transparent="1" />
            <widget name="filters_summary" position="18,486" size="944,50" font="Regular;16" foregroundColor="#00C2FF" backgroundColor="#121824" transparent="0" valign="center" />
            <eLabel position="0,546" size="980,74" backgroundColor="#121824" zPosition="-1" />
            <eLabel position="18,555" size="130,30" backgroundColor="#B71C1C" zPosition="1" />
            <eLabel position="160,555" size="130,30" backgroundColor="#167A37" zPosition="1" />
            <eLabel position="302,555" size="130,30" backgroundColor="#B89300" zPosition="1" />
            <eLabel position="444,555" size="130,30" backgroundColor="#1556A8" zPosition="1" />
            <widget name="key_red" position="18,555" size="130,30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_green" position="160,555" size="130,30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_yellow" position="302,555" size="130,30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="key_blue" position="444,555" size="130,30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
            <widget name="operation" position="590,555" size="372,30" font="Regular;16" halign="right" valign="center" foregroundColor="#FFD200" transparent="1" />
            <widget name="footer" position="18,596" size="944,18" font="Regular;14" halign="center" foregroundColor="#8A94A6" transparent="1" />
        </screen>""".format(qr=os.path.join(PLUGIN_PATH, "assets", "qr_site_small.png"))
    return """
    <screen position="center,center" size="1100,690" title="PiconUpdater" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="1100,690" backgroundColor="#0B0F14" zPosition="-10" />
        <eLabel position="0,0" size="1100,90" backgroundColor="#121824" zPosition="-2" />
        <widget name="qr_small" position="18,16" size="56,56" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="site" position="88,14" size="450,26" font="Regular;19" foregroundColor="#00C2FF" transparent="1" />
        <widget name="catalog_status" position="88,46" size="450,24" font="Regular;18" foregroundColor="#A9B4C2" transparent="1" />
        <widget name="title" position="560,14" size="520,38" font="Regular;32" halign="right" foregroundColor="#00C2FF" transparent="1" />
        <widget name="plugin_status" position="560,54" size="520,22" font="Regular;18" halign="right" foregroundColor="#FFD200" transparent="1" />
        <eLabel position="0,88" size="1100,2" backgroundColor="#00C2FF" />
        <widget name="picon_list" position="20,108" size="660,418" itemHeight="42" font="Regular;20" scrollbarMode="showOnDemand" foregroundColor="#D7DEE9" foregroundColorSelected="#FFFFFF" backgroundColor="#0B0F14" backgroundColorSelected="#18364A" transparent="0" />
        <eLabel position="694,108" size="2,418" backgroundColor="#203346" />
        <widget name="preview" position="735,116" size="330,198" alphatest="blend" scale="1" />
        <widget name="details" position="720,332" size="360,194" font="Regular;18" foregroundColor="#D7DEE9" transparent="1" />
        <widget name="filters_summary" position="20,540" size="1060,54" font="Regular;18" foregroundColor="#00C2FF" backgroundColor="#121824" transparent="0" valign="center" />
        <eLabel position="0,606" size="1100,84" backgroundColor="#121824" zPosition="-1" />
        <eLabel position="20,616" size="145,32" backgroundColor="#B71C1C" zPosition="1" />
        <eLabel position="180,616" size="145,32" backgroundColor="#167A37" zPosition="1" />
        <eLabel position="340,616" size="145,32" backgroundColor="#B89300" zPosition="1" />
        <eLabel position="500,616" size="145,32" backgroundColor="#1556A8" zPosition="1" />
        <widget name="key_red" position="20,616" size="145,32" font="Regular;20" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="key_green" position="180,616" size="145,32" font="Regular;20" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="key_yellow" position="340,616" size="145,32" font="Regular;20" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="key_blue" position="500,616" size="145,32" font="Regular;20" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="operation" position="660,616" size="420,32" font="Regular;18" halign="right" valign="center" foregroundColor="#FFD200" transparent="1" />
        <widget name="footer" position="20,665" size="1060,18" font="Regular;15" halign="center" foregroundColor="#8A94A6" transparent="1" />
    </screen>""".format(qr=os.path.join(PLUGIN_PATH, "assets", "qr_site_small.png"))


def _filter_skin():
    w, h = _desktop()
    if w <= 1280 or h <= 720:
        width, height = 760, 500
        list_y, list_h, hint_y, bar_y, key_y = 90, 272, 374, 430, 440
        key_w, gaps = 150, (30, 200, 370)
    else:
        width, height = 840, 560
        list_y, list_h, hint_y, bar_y, key_y = 100, 300, 414, 490, 500
        key_w, gaps = 160, (40, 220, 400)
    return """
    <screen position="center,center" size="{w},{h}" title="PiconUpdater" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="{w},70" backgroundColor="#121824" />
        <widget name="title" position="20,18" size="{tw},32" font="Regular;26" halign="center" foregroundColor="#00C2FF" transparent="1" />
        <eLabel position="0,68" size="{w},2" backgroundColor="#00C2FF" />
        <widget name="list" position="30,{list_y}" size="{lw},{list_h}" itemHeight="44" font="Regular;20" scrollbarMode="showOnDemand" foregroundColor="#D7DEE9" foregroundColorSelected="#FFFFFF" backgroundColor="#0B0F14" backgroundColorSelected="#18364A" transparent="0" />
        <widget name="hint" position="30,{hint_y}" size="{lw},42" font="Regular;16" foregroundColor="#A9B4C2" halign="center" transparent="1" />
        <eLabel position="0,{bar_y}" size="{w},{bar_h}" backgroundColor="#121824" />
        <eLabel position="{x1},{key_y}" size="{key_w},30" backgroundColor="#B71C1C" zPosition="1" />
        <eLabel position="{x2},{key_y}" size="{key_w},30" backgroundColor="#167A37" zPosition="1" />
        <eLabel position="{x3},{key_y}" size="{key_w},30" backgroundColor="#B89300" zPosition="1" />
        <widget name="key_red" position="{x1},{key_y}" size="{key_w},30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="key_green" position="{x2},{key_y}" size="{key_w},30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
        <widget name="key_yellow" position="{x3},{key_y}" size="{key_w},30" font="Regular;18" halign="center" valign="center" transparent="1" zPosition="3" foregroundColor="#FFFFFF" />
    </screen>""".format(
        w=width, h=height, tw=width-40, lw=width-60, list_y=list_y, list_h=list_h,
        hint_y=hint_y, bar_y=bar_y, bar_h=height-bar_y, key_y=key_y, key_w=key_w,
        x1=gaps[0], x2=gaps[1], x3=gaps[2],
    )


def _qr_skin():
    w, h = _desktop()
    if w <= 1280 or h <= 720:
        return """
        <screen position="center,center" size="760,560" title="PiconUpdater" backgroundColor="#0B0F14">
            <eLabel position="0,0" size="760,70" backgroundColor="#121824" />
            <widget name="title" position="20,18" size="720,34" font="Regular;26" halign="center" foregroundColor="#00C2FF" transparent="1" />
            <widget name="qr" position="190,88" size="380,380" pixmap="{qr}" alphatest="blend" scale="1" />
            <widget name="site" position="20,480" size="720,24" font="Regular;18" halign="center" foregroundColor="#D7DEE9" transparent="1" />
            <widget name="hint" position="20,514" size="720,24" font="Regular;16" halign="center" foregroundColor="#A9B4C2" transparent="1" />
        </screen>""".format(qr=os.path.join(PLUGIN_PATH, "assets", "qr_site.png"))
    return """
    <screen position="center,center" size="900,650" title="PiconUpdater" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="900,80" backgroundColor="#121824" />
        <widget name="title" position="20,20" size="860,38" font="Regular;30" halign="center" foregroundColor="#00C2FF" transparent="1" />
        <widget name="qr" position="225,96" size="450,450" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="site" position="20,562" size="860,28" font="Regular;21" halign="center" foregroundColor="#D7DEE9" transparent="1" />
        <widget name="hint" position="20,604" size="860,24" font="Regular;18" halign="center" foregroundColor="#A9B4C2" transparent="1" />
    </screen>""".format(qr=os.path.join(PLUGIN_PATH, "assets", "qr_site.png"))


class PiconFilterScreen(Screen):
    skin = _filter_skin()

    def __init__(self, session, catalog, current_filters, location_id):
        Screen.__init__(self, session)
        self.catalog = list(catalog or [])
        self.filters = dict(current_filters or {})
        self.location_id = location_id
        self.targets = storage_targets()
        self.rows = ["type", "satellite", "scope", "canvas", "logotype", "background", "location"]
        self.options = self._build_options()
        self["title"] = Label(_t("filter_title"))
        self["list"] = MenuList([])
        self["hint"] = Label("← / → zmiana • wybierz Konkretny satelita dla małej paczki SRP • OK/Zielony zastosuj" if _lang() == "pl" else "← / → change • choose Specific satellite for a smaller SRP install • OK/Green apply")
        self["key_red"] = Label(_t("cancel"))
        self["key_green"] = Label(_t("apply"))
        self["key_yellow"] = Label(_t("reset"))
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "cancel": self.close,
            "red": self.close,
            "green": self.apply,
            "ok": self.apply,
            "yellow": self.reset,
            "left": lambda: self.cycle(-1),
            "right": lambda: self.cycle(1),
            "up": self["list"].up,
            "down": self["list"].down,
        }, -1)
        self.refresh()

    def _unique(self, key):
        vals = sorted(set([str(x.get(key) or "") for x in self.catalog if x.get(key)]))
        return vals

    def _build_options(self):
        all_label = _t("all")
        satellites = []
        for item in self.catalog:
            for sat in scope_satellites(item.get("scope")):
                if sat not in satellites:
                    satellites.append(sat)
        satellites.sort()
        return {
            "type": [("*", all_label)] + [(v, type_label(v)) for v in self._unique("type")],
            "satellite": [("*", _t("satellite_all"))] + [(v, satellite_label(v)) for v in satellites],
            "scope": [("*", all_label)] + [(v, scope_label(v)) for v in self._unique("scope")],
            "canvas": [("*", all_label)] + [(v, v) for v in self._unique("canvas")],
            "logotype": [("*", all_label)] + [(v, logo_label(v)) for v in self._unique("logotype")],
            "background": [("*", all_label)] + [(v, background_label(v)) for v in self._unique("background")],
            "location": [(x["id"], x["label"]) for x in self.targets],
        }

    def _current_value(self, row):
        return self.location_id if row == "location" else self.filters.get(row, "*")

    def _label_for(self, row, value):
        for key, label in self.options.get(row, []):
            if key == value:
                return label
        return value

    def refresh(self):
        names = {
            "type": _t("ptype"), "satellite": _t("satellite"), "scope": _t("scope"), "canvas": _t("size"),
            "logotype": _t("logo"), "background": _t("background"), "location": _t("location"),
        }
        rows = []
        for row in self.rows:
            value = self._current_value(row)
            rows.append("%-18s  %s" % ((names[row] + ":"), self._label_for(row, value)))
        idx = self["list"].getSelectionIndex()
        self["list"].setList(rows)
        if idx >= 0:
            self["list"].moveToIndex(min(idx, len(rows) - 1))

    def cycle(self, direction):
        idx = self["list"].getSelectionIndex()
        if idx < 0 or idx >= len(self.rows):
            return
        row = self.rows[idx]
        opts = self.options.get(row, [])
        if not opts:
            return
        current = self._current_value(row)
        pos = 0
        for i, (value, _label) in enumerate(opts):
            if value == current:
                pos = i
                break
        pos = (pos + direction) % len(opts)
        value = opts[pos][0]
        if row == "location":
            self.location_id = value
        else:
            self.filters[row] = value
        self.refresh()

    def reset(self):
        for row in ("type", "satellite", "scope", "canvas", "logotype", "background"):
            self.filters[row] = "*"
        self.refresh()

    def apply(self):
        self.close((self.filters, self.location_id))


class PiconQRScreen(Screen):
    skin = _qr_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(_t("qr_title"))
        self["qr"] = Pixmap()
        self["site"] = Label(SITE_URL)
        self["hint"] = Label(_t("qr_hint"))
        self["actions"] = ActionMap(["OkCancelActions", "NumberActions"], {
            "cancel": self.close, "ok": self.close, "0": self.close,
        }, -1)


class PiconUpdaterMain(Screen):
    skin = _main_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.catalog = []
        self.filtered = []
        self.catalog_meta = {}
        self.state = load_state()
        self.remote_version = ""
        self.location_id = self.state.get("last_location", "flash")
        if self.location_id not in [x["id"] for x in storage_targets()]:
            self.location_id = "flash"
        self.filters = {"type": "*", "satellite": "*", "scope": "*", "canvas": "*", "logotype": "*", "background": "*"}
        self.busy = False
        self.started = False
        self.work_queue = queue.Queue()
        self.worker_timer = eTimer()
        self.worker_timer.callback.append(self._poll_queue)
        self.worker_timer.start(200, False)
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self._preview_ready)

        self["qr_small"] = Pixmap()
        self["site"] = Label(SITE_URL)
        self["catalog_status"] = Label(_t("loading"))
        self["title"] = Label("%s %s" % (_t("title"), PLUGIN_VERSION))
        self["plugin_status"] = Label("")
        self["picon_list"] = MenuList([])
        self["preview"] = Pixmap()
        self["details"] = Label("")
        self["filters_summary"] = Label("")
        self["key_red"] = Label(_t("exit"))
        self["key_green"] = Label(_t("install"))
        self["key_yellow"] = Label(_t("filters"))
        self["key_blue"] = Label(_t("refresh"))
        self["operation"] = Label("")
        self["footer"] = Label("PiconUpdater %s | picons/picons • AIO-IPTV • QR → | by Paweł Pawełek" % PLUGIN_VERSION)

        self["actions"] = ActionMap([
            "OkCancelActions", "ColorActions", "DirectionActions", "MenuActions", "NumberActions", "InfoActions"
        ], {
            "cancel": self.exit,
            "red": self.exit,
            "green": self.install_selected,
            "ok": self.install_selected,
            "yellow": self.open_filters,
            "blue": self.refresh_catalog,
            "menu": self.open_tools,
            "0": self.open_qr,
            "info": self.open_qr,
            "up": self["picon_list"].up,
            "down": self["picon_list"].down,
            "left": self["picon_list"].pageUp,
            "right": self["picon_list"].pageDown,
        }, -1)
        self["picon_list"].onSelectionChanged.append(self.selection_changed)
        self.onShow.append(self._on_show)

    def _on_show(self):
        if not self.started:
            self.started = True
            self._start_catalog_worker(False)

    def _set_busy(self, value):
        self.busy = bool(value)

    def _start_catalog_worker(self, force):
        if self.busy:
            return
        self._set_busy(True)
        self["operation"].setText(_t("loading"))

        def work():
            try:
                items, meta = get_catalog(PLUGIN_PATH, force=force)
                remote = remote_plugin_version()
                self.work_queue.put(("catalog", items, meta, remote))
            except Exception as e:
                self.work_queue.put(("error", str(e)))
        t = threading.Thread(target=work)
        t.daemon = True
        t.start()

    def refresh_catalog(self):
        self._start_catalog_worker(True)

    def _poll_queue(self):
        while True:
            try:
                msg = self.work_queue.get_nowait()
            except queue.Empty:
                break
            kind = msg[0]
            if kind == "catalog":
                self.catalog, self.catalog_meta, self.remote_version = msg[1], msg[2], msg[3]
                self._set_busy(False)
                self["operation"].setText("")
                self._update_catalog_status()
                self._apply_filters()
            elif kind == "progress":
                _kind, phase, done, total = msg
                if total:
                    pct = int((float(done) / float(total)) * 100.0)
                    self["operation"].setText((phase + " %d%%") % pct)
                else:
                    self["operation"].setText(phase if not done else "%s %s" % (phase, _human_bytes(done)))
            elif kind == "install_done":
                item, result = msg[1], msg[2]
                self._set_busy(False)
                self["operation"].setText("")
                key = item.get("variant_key")
                self.state.setdefault("installed", {})[key] = {
                    "name": item.get("name"),
                    "published_at": item.get("published_at", ""),
                    "release_tag": item.get("release_tag", ""),
                    "path": result.get("path", ""),
                    "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                self.state["last_location"] = self.location_id
                try:
                    save_state(self.state)
                except Exception:
                    pass
                self._apply_filters(keep_index=True)
                extra = ""
                if result.get("satellite") and result.get("satellite") != "*":
                    extra += "\nSatelita: %s" % satellite_label(result.get("satellite"))
                if result.get("symlink"):
                    extra += "\n%s" % result.get("symlink")
                self.session.open(MessageBox, _t("installed_ok") % (result.get("count", 0), result.get("path", ""), extra), MessageBox.TYPE_INFO, timeout=8)
            elif kind == "error":
                self._set_busy(False)
                self["operation"].setText("")
                self.session.open(MessageBox, "%s: %s" % (_t("error"), msg[1]), MessageBox.TYPE_ERROR)

    def _update_catalog_status(self):
        if self.catalog_meta.get("online"):
            text = _t("catalog_online")
        elif self.catalog_meta.get("cached"):
            text = _t("catalog_cache")
        else:
            text = _t("catalog_fallback")
        latest = newest_published(self.catalog)
        new_count = 0
        update_count = 0
        for item in self.catalog:
            flags = item_flags(item, self.state, latest)
            if "NEW" in flags or "LATEST" in flags:
                new_count += 1
            if "UPDATE" in flags:
                update_count += 1
        text += " • %d • %s" % (len(self.catalog), _t("catalog_changes") % (new_count, update_count))
        self["catalog_status"].setText(text)
        if self.remote_version:
            if semver_tuple(self.remote_version) > semver_tuple(PLUGIN_VERSION):
                self["plugin_status"].setText(_t("plugin_update") % self.remote_version)
            else:
                self["plugin_status"].setText(_t("plugin_current") % PLUGIN_VERSION)

    def _match(self, item):
        for key in ("type", "scope", "canvas", "logotype", "background"):
            wanted = self.filters.get(key, "*")
            if wanted != "*" and item.get(key) != wanted:
                return False
        satellite = self.filters.get("satellite", "*")
        if satellite != "*" and not item_supports_satellite(item, satellite):
            return False
        return True

    def _item_prefix(self, item):
        flags = item_flags(item, self.state, newest_published(self.catalog))
        if "UPDATE" in flags:
            return "[%s] " % _t("update")
        if "NEW" in flags:
            return "[%s] " % _t("new")
        if "INSTALLED" in flags:
            return "[%s] " % _t("installed")
        if "LATEST" in flags:
            return "[%s] " % _t("latest")
        return ""

    def _row_text(self, item):
        satellite = self.filters.get("satellite", "*")
        scope_text = satellite_label(satellite) if satellite != "*" else _short_scope(item.get("scope"))
        return "%s%s | %s | %s | %s | %s" % (
            self._item_prefix(item),
            (item.get("type") or "—").upper(),
            scope_text,
            item.get("canvas") or "—",
            (item.get("logotype") or "—").upper(),
            (item.get("background") or "—").upper(),
        )

    def _apply_filters(self, keep_index=False):
        old_idx = self["picon_list"].getSelectionIndex() if keep_index else 0
        self.filtered = [x for x in self.catalog if self._match(x)]
        self["picon_list"].setList([self._row_text(x) for x in self.filtered])
        if self.filtered:
            self["picon_list"].moveToIndex(min(max(old_idx, 0), len(self.filtered) - 1))
        self._update_filter_summary()
        self.selection_changed()

    def _update_filter_summary(self):
        def fv(key, fn=None):
            value = self.filters.get(key, "*")
            if value == "*":
                return _t("all")
            return fn(value) if fn else value
        loc = target_by_id(self.location_id)
        sat = self.filters.get("satellite", "*")
        sat_text = _t("satellite_all") if sat == "*" else satellite_label(sat)
        text = "%s: %s • %s • %s • %s • %s • %s    |    %s: %s" % (
            _t("filter_summary"), fv("type", type_label), sat_text, fv("scope", scope_label),
            fv("canvas"), fv("logotype", logo_label), fv("background", background_label),
            _t("location"), loc.get("label", ""),
        )
        self["filters_summary"].setText(text)

    def selected_item(self):
        idx = self["picon_list"].getSelectionIndex()
        if idx < 0 or idx >= len(self.filtered):
            return None
        return self.filtered[idx]

    def selection_changed(self):
        item = self.selected_item()
        if not item:
            self["details"].setText(_t("empty"))
            return
        flags = item_flags(item, self.state, newest_published(self.catalog))
        status_map = {"UPDATE": _t("update"), "NEW": _t("new"), "INSTALLED": _t("installed"), "LATEST": _t("latest")}
        status = _t("normal")
        for key in ("UPDATE", "NEW", "INSTALLED", "LATEST"):
            if key in flags:
                status = status_map[key]
                break
        details = (
            "%s: %s\n%s: %s\n%s: %s\n%s: %s (%s)\n%s: %s\n%s: %s\n%s: %s\n%s: %s\n%s: %s" % (
                _t("source"), item.get("source", "—"),
                _t("ptype"), type_label(item.get("type")),
                _t("scope"), (satellite_label(self.filters.get("satellite")) if self.filters.get("satellite", "*") != "*" else scope_label(item.get("scope"))),
                _t("size"), item.get("canvas", "—"), item.get("padded", "—"),
                _t("logo"), logo_label(item.get("logotype")),
                _t("background"), background_label(item.get("background")),
                _t("release"), item.get("release_tag") or "—",
                _t("package_size"), _human_bytes(item.get("size")),
                _t("status"), status,
            )
        )
        if item.get("type") == "snp":
            details += "\n" + _t("legacy_note")
        self["details"].setText(details)
        self._load_preview(item)

    def _load_preview(self, item):
        background = (item or {}).get("background") or "transparent"
        path = os.path.join(PLUGIN_PATH, "previews_local", "sample_%s.png" % background)
        if not os.path.exists(path):
            path = os.path.join(PLUGIN_PATH, "previews_local", "sample_transparent.png")
        if not os.path.exists(path):
            path = os.path.join(PLUGIN_PATH, "previews_local", "%s.png" % background)
        try:
            inst = self["preview"].instance
            if inst is None:
                return
            self.picload.setPara([inst.size().width(), inst.size().height(), 1, 1, False, 1, "#00000000"])
            self.picload.startDecode(path)
        except Exception:
            pass

    def _preview_ready(self, info=None):
        try:
            ptr = self.picload.getData()
            if ptr is not None and self["preview"].instance is not None:
                self["preview"].instance.setPixmap(ptr)
                self["preview"].instance.show()
        except Exception:
            pass

    def open_filters(self):
        if self.busy:
            self.session.open(MessageBox, _t("busy"), MessageBox.TYPE_INFO, timeout=4)
            return
        self.session.openWithCallback(self._filters_done, PiconFilterScreen, self.catalog, self.filters, self.location_id)

    def _filters_done(self, result):
        if not result:
            return
        self.filters, self.location_id = result
        self.state["last_location"] = self.location_id
        try:
            save_state(self.state)
        except Exception:
            pass
        self._apply_filters()

    def install_selected(self):
        if self.busy:
            self.session.open(MessageBox, _t("busy"), MessageBox.TYPE_INFO, timeout=4)
            return
        item = self.selected_item()
        if not item:
            return
        item = dict(item)
        item["selected_satellite"] = self.filters.get("satellite", "*")
        target = target_by_id(self.location_id)
        msg = _t("confirm_install") % (self._row_text(item), target.get("label", target.get("path", "")))
        self.session.openWithCallback(lambda ok: self._start_install(item, target) if ok else None, MessageBox, msg, MessageBox.TYPE_YESNO)

    def _start_install(self, item, target):
        self._set_busy(True)
        self["operation"].setText(_t("downloading") % "0%")

        def work():
            suffix = ".tar.xz" if item.get("format") == "tar.xz" else ".ipk"
            fd, tmp = tempfile.mkstemp(prefix="piconupdater-", suffix=suffix, dir="/tmp")
            os.close(fd)
            try:
                need = int(item.get("size") or 0)
                free = free_space("/tmp")
                if need and free and free < int(need * 1.35):
                    raise IOError("Za mało miejsca w /tmp: potrzeba ok. %s, wolne %s" % (_human_bytes(need * 1.35), _human_bytes(free)))

                def dprog(done, total):
                    self.work_queue.put(("progress", _t("downloading").split(":")[0], done, total))
                download_file(item.get("download_url"), tmp, progress=dprog, timeout=120, expected_digest=item.get("digest", ""))

                # Fully validate the downloaded archive before touching existing picons.
                # Only after successful validation do we remove the old set. This gives
                # the update access to the space occupied by previous picons without
                # risking deletion because of a corrupt/incomplete download.
                validate_package(tmp, item)
                self.work_queue.put(("progress", _t("clearing_old"), 0, 0))
                clear_picons(target)
                required = estimate_install_bytes(tmp, item, target)
                target_free = free_space(target.get("path", "/"))
                if required and target_free and target_free < required:
                    raise IOError("Za mało miejsca po usunięciu poprzednich piconów: potrzeba ok. %s, wolne %s" % (_human_bytes(required), _human_bytes(target_free)))

                def iprog(done, total):
                    self.work_queue.put(("progress", _t("installing").split(":")[0], done, total))
                result = install_package(tmp, item, target, progress=iprog)
                self.work_queue.put(("install_done", item, result))
            except Exception as e:
                self.work_queue.put(("error", str(e)))
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
        t = threading.Thread(target=work)
        t.daemon = True
        t.start()

    def open_qr(self):
        self.session.open(PiconQRScreen)

    def open_tools(self):
        if self.busy:
            self.session.open(MessageBox, _t("busy"), MessageBox.TYPE_INFO, timeout=4)
            return
        choices = [
            (_t("tool_update"), "update"),
            (_t("tool_qr"), "qr"),
            (_t("tool_clear_cache"), "cache"),
            (_t("tool_clear_picons"), "clear"),
        ]
        self.session.openWithCallback(self._tool_selected, ChoiceBox, title=_t("tools"), list=choices)

    def _tool_selected(self, choice):
        if not choice:
            return
        action = choice[1]
        if action == "qr":
            self.open_qr()
        elif action == "cache":
            try:
                if os.path.exists(CACHE_FILE):
                    os.unlink(CACHE_FILE)
            except Exception:
                pass
            self.session.open(MessageBox, _t("clear_cache_ok"), MessageBox.TYPE_INFO, timeout=4)
        elif action == "clear":
            target = target_by_id(self.location_id)
            msg = _t("confirm_clear") % target.get("path", "")
            self.session.openWithCallback(lambda ok: self._do_clear(target) if ok else None, MessageBox, msg, MessageBox.TYPE_YESNO)
        elif action == "update":
            msg = _t("confirm_plugin_update") % INSTALL_COMMAND
            self.session.openWithCallback(self._run_plugin_installer, MessageBox, msg, MessageBox.TYPE_YESNO)

    def _do_clear(self, target):
        try:
            count = clear_picons(target)
            self.session.open(MessageBox, _t("clear_ok") % count, MessageBox.TYPE_INFO, timeout=6)
        except Exception as e:
            self.session.open(MessageBox, "%s: %s" % (_t("error"), e), MessageBox.TYPE_ERROR)

    def _run_plugin_installer(self, confirmed):
        if not confirmed:
            return
        if Console is not None:
            self.session.open(Console, title="PiconUpdater – GitHub update", cmdlist=[INSTALL_COMMAND], closeOnSuccess=False)
        else:
            os.system(INSTALL_COMMAND)

    def exit(self):
        if self.busy:
            self.session.open(MessageBox, _t("busy"), MessageBox.TYPE_INFO, timeout=4)
            return
        latest = newest_published(self.catalog)
        if latest:
            self.state["seen_published_at"] = latest
        self.state["last_location"] = self.location_id
        try:
            save_state(self.state)
        except Exception:
            pass
        try:
            self.worker_timer.stop()
        except Exception:
            pass
        self.close()
