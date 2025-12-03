import os
import gettext
import json
import requests
import tarfile
import subprocess
import shutil
import datetime
import re

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from enigma import eConsoleAppContainer, eTimer, getDesktop, ePicLoad

def localeInit():
    from Components.Language import language
    lang = language.getLanguage()[:2]
    os.environ["LANGUAGE"] = lang
    gettext.bindtextdomain("PiconUpdater", resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/locale"))
    gettext.textdomain("PiconUpdater")
    return gettext.gettext

_ = localeInit()

# --- KONFIGURACJA WERSJI I GITHUBA ---
CURRENT_VERSION = "1.2"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/"
VERSION_FILE_URL = GITHUB_RAW_URL + "version"

class PiconUpdater(Screen):
    desktop_size = getDesktop(0).size()
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Skórka FULL HD
    if desktop_size.height() > 720:
        skin = """
            <screen position="center,center" size="900,550" title="Picon Updater" backgroundColor="#1a1a1a">
                <widget name="title_header" position="20,10" size="860,40" font="Regular;32" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                <eLabel position="20,55" size="860,2" backgroundColor="#333333" />
                <widget name="category_label" position="50,70" size="400,35" font="Regular;26" foregroundColor="#00ccff" transparent="1" halign="left" />
                <widget name="picon_list" position="50,110" size="400,290" itemHeight="35" font="Regular;26" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="470,110" size="380,220" backgroundColor="#333333" zPosition="1" />
                <widget name="status" position="470,340" size="380,30" font="Regular;22" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="470,380" size="380,80" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="top" />
                <eLabel position="20,460" size="860,2" backgroundColor="#333333" />
                <widget name="footer" position="20,470" size="860,20" font="Regular;16" foregroundColor="#aaaaaa" transparent="1" halign="center" />
                
                <ePixmap position="20,500" size="200,40" pixmap="skin_default/buttons/red.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="240,500" size="200,40" pixmap="skin_default/buttons/green.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="460,500" size="200,40" pixmap="skin_default/buttons/yellow.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="680,500" size="200,40" pixmap="skin_default/buttons/blue.png" zPosition="1" transparent="1" alphatest="on" />
                
                <widget source="key_red" render="Label" position="20,500" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_green" render="Label" position="240,500" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_yellow" render="Label" position="460,500" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_blue" render="Label" position="680,500" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
            </screen>
        """
    # Skórka HD
    else:
        skin = """
            <screen position="center,center" size="620,400" title="Picon Updater" backgroundColor="#1a1a1a">
                <widget name="title_header" position="10,5" size="600,30" font="Regular;24" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                <eLabel position="10,38" size="600,1" backgroundColor="#333333" />
                <widget name="category_label" position="20,45" size="280,25" font="Regular;20" foregroundColor="#00ccff" transparent="1" halign="left" />
                <widget name="picon_list" position="20,75" size="280,215" itemHeight="30" font="Regular;20" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="310,75" size="280,160" backgroundColor="#333333" zPosition="1" />
                <widget name="status" position="310,240" size="280,25" font="Regular;18" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="310,265" size="280,50" font="Regular;16" foregroundColor="#ffffff" transparent="1" halign="center" valign="top" />
                <eLabel position="10,320" size="600,1" backgroundColor="#333333" />
                <widget name="footer" position="10,330" size="600,20" font="Regular;14" foregroundColor="#aaaaaa" transparent="1" halign="center" />
                <ePixmap position="20,360" size="140,35" pixmap="skin_default/buttons/red.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="170,360" size="140,35" pixmap="skin_default/buttons/green.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="320,360" size="140,35" pixmap="skin_default/buttons/yellow.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="470,360" size="140,35" pixmap="skin_default/buttons/blue.png" zPosition="1" transparent="1" alphatest="on" />
                <widget source="key_red" render="Label" position="20,360" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_green" render="Label" position="170,360" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_yellow" render="Label" position="320,360" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_blue" render="Label" position="470,360" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
            </screen>
        """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.title = "Picon Updater " + CURRENT_VERSION
        self.console = eConsoleAppContainer()
        self.selected_picon = None
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.setPreview)
        
        self.categories = []
        self.picons_by_category = {}
        self.current_category_idx = 0
        self.new_version_available = False
        
        self["title_header"] = Label("Picon Updater v" + CURRENT_VERSION)
        self["picon_list"] = MenuList([])
        self["preview"] = Pixmap()
        self["status"] = Label("")
        self["description"] = Label(_("Ładowanie..."))
        self["category_label"] = Label("")
        
        # Stopka
        self.footer_base = "© Twórca: Paweł Pawełek | 📅 " + self.current_date + " | ✉ email: msisystem@t.pl"
        self["footer"] = Label(self.footer_base)
        
        # Przyciski
        self["key_red"] = Label(_("Wyjście"))
        self["key_green"] = Label(_("Aktualizuj")) # Zmieniono z "Pobierz"
        self["key_yellow"] = Label(_("Język"))
        self["key_blue"] = Label("") 
        
        self["actions"] = ActionMap(["ColorActions", "NavigationActions", "SetupActions"], 
        {
            "red": self.exit,
            "green": self.updatePlugin, # Zmiana akcji na aktualizację wtyczki
            "yellow": self.changeLanguage,
            "blue": self.nextCategory,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
            "cancel": self.exit,
            "ok": self.download # OK teraz pobiera picony
        }, -1)
        
        self["picon_list"].onSelectionChanged.append(self.selectionChanged)
        self.onShow.append(self.start_delay)

        self.loadJson()

    def loadJson(self):
        json_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/picons.json")
        try:
            with open(json_path, 'r') as f:
                all_picons_data = json.load(f)
                self._organize_picons(all_picons_data)
        except Exception as e:
            print(f"[PiconUpdater] JSON Error: {e}")
            self.categories = ["Błąd"]
            self.picons_by_category = {"Błąd": []}

    def start_delay(self):
        self.start_timer = eTimer()
        self.start_timer.callback.append(self.onStart)
        self.start_timer.start(200, True)

    def onStart(self):
        self.refreshList()
        self.selectionChanged()
        # Sprawdź aktualizację w tle po uruchomieniu
        self.checkUpdate()

    # --- MECHANIZM AKTUALIZACJI WTYCZKI ---
    def checkUpdate(self):
        """Pobiera plik version z GitHuba i porównuje z obecną wersją."""
        try:
            # Używamy eConsoleAppContainer lub requests w wątku, ale tutaj dla prostoty requests z krótkim timeoutem
            # W idealnym świecie powinno to być asynchroniczne, ale plik jest malutki.
            self.update_timer = eTimer()
            self.update_timer.callback.append(self._do_check_update)
            self.update_timer.start(500, True)
        except:
            pass

    def _do_check_update(self):
        try:
            r = requests.get(VERSION_FILE_URL, timeout=3)
            if r.status_code == 200:
                remote_version = r.text.strip()
                # Proste porównanie stringów (zakładamy format X.Y)
                if remote_version != CURRENT_VERSION:
                    self.new_version_available = True
                    self["status"].setText(_("Dostępna nowa wersja: ") + remote_version)
                    self["footer"].setText(self.footer_base + " | ⚠ AKTUALIZACJA: " + remote_version)
                    self["key_green"].setText(_("Aktualizuj!"))
                else:
                    self["status"].setText(_("Wtyczka jest aktualna."))
        except Exception as e:
            print(f"[PiconUpdater] Check update error: {e}")

    def updatePlugin(self):
        """Pobiera nową wersję plików wtyczki i restartuje GUI."""
        if not self.new_version_available:
            self.session.open(MessageBox, _("Wtyczka jest aktualna (v%s). Czy mimo to chcesz wymusić przeinstalowanie z GitHub?") % CURRENT_VERSION, MessageBox.TYPE_YESNO, callback=self.forceUpdate)
        else:
            self.forceUpdate(True)

    def forceUpdate(self, confirmed):
        if not confirmed:
            return
            
        self["status"].setText(_("Pobieranie aktualizacji wtyczki..."))
        
        # Lista plików do zaktualizowania (podstawowe pliki)
        files_to_update = ["plugin.py", "picons.json", "version"]
        base_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/")
        
        try:
            for filename in files_to_update:
                url = GITHUB_RAW_URL + filename
                save_path = os.path.join(base_path, filename)
                
                print(f"[PiconUpdater] Updating {filename} from {url}")
                r = requests.get(url, stream=True, timeout=10)
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            self.session.open(MessageBox, _("Wtyczka zaktualizowana pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
            
        except Exception as e:
            self["status"].setText(_("Błąd aktualizacji!"))
            self.session.open(MessageBox, _("Błąd aktualizacji wtyczki: ") + str(e), MessageBox.TYPE_ERROR)

    # --- KONIEC MECHANIZMU AKTUALIZACJI ---

    def _organize_picons(self, all_picons):
        self.picons_by_category = {}
        found_categories = set()
        default_cat = "Satelita"
        for picon in all_picons:
            cat = picon.get("category", default_cat)
            found_categories.add(cat)
            if cat not in self.picons_by_category:
                self.picons_by_category[cat] = []
            self.picons_by_category[cat].append(picon)
        
        self.categories = sorted(list(found_categories))
        if "Satelita" in self.categories:
            self.categories.insert(0, self.categories.pop(self.categories.index("Satelita")))
        self.current_category_idx = 0
        self.updateBlueButton()

    def nextCategory(self):
        if len(self.categories) > 1:
            self.current_category_idx += 1
            if self.current_category_idx >= len(self.categories):
                self.current_category_idx = 0
            self.refreshList()
            self.updateBlueButton()

    def updateBlueButton(self):
        if not self.categories or len(self.categories) <= 1:
            self["key_blue"].setText("")
            return

        next_cat_idx = (self.current_category_idx + 1) % len(self.categories)
        next_cat_name = self.categories[next_cat_idx]
        
        if next_cat_name == "Satelita":
            self["key_blue"].setText("SAT")
        else:
            self["key_blue"].setText(next_cat_name)

    def refreshList(self):
        if not self.categories:
            self["picon_list"].setList([])
            self["category_label"].setText(_("Brak danych"))
            return

        current_cat_name = self.categories[self.current_category_idx]
        current_picons = self.picons_by_category[current_cat_name]
        
        self["category_label"].setText(f"{current_cat_name} ({len(current_picons)})")
        
        list_items = [p["name"] for p in current_picons]
        self["picon_list"].setList(list_items)
        self["picon_list"].moveToIndex(0)
        self.updateBlueButton()

    def selectionChanged(self):
        if not self.categories:
            return

        if self["preview"].instance:
            self["preview"].instance.setPixmap(None)

        selected_index = self["picon_list"].getSelectionIndex()
        current_cat_name = self.categories[self.current_category_idx]
        current_picons = self.picons_by_category[current_cat_name]

        if selected_index >= 0 and selected_index < len(current_picons):
            self.selected_picon = current_picons[selected_index]
            description_text = self.selected_picon["name"]
            
            satellites = self.selected_picon.get("satellites")
            if satellites:
                if isinstance(satellites, list):
                    description_text += f"\nSat: {', '.join(satellites)}"
                else:
                    description_text += f"\nSat: {satellites}"
            
            # Dodanie informacji o przycisku OK
            description_text += "\n\n[OK] - Pobierz wybraną paczkę picon"
            
            self["description"].setText(description_text)
            self.loadPreview(self.selected_picon["preview"])
        else:
            self.selected_picon = None
            self["description"].setText(_("Lista pusta"))
            if self["preview"].instance:
                self["preview"].instance.setPixmap(None)

    def loadPreview(self, url):
        try:
            if self["preview"].instance is None:
                return

            tmp_path = "/tmp/picon_preview.png"
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            
            self["status"].setText(_("Ładowanie podglądu..."))
            
            if url.startswith("file://"):
                local_path = url.replace("file://", "")
                if os.path.exists(local_path):
                    shutil.copyfile(local_path, tmp_path)
                else:
                    self["status"].setText(_("Brak podglądu"))
                    return 
            else:
                r = requests.get(url, stream=True, timeout=5)
                r.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            self.picload.setPara([
                self["preview"].instance.size().width(),
                self["preview"].instance.size().height(),
                1, 1, False, 1, "#00000000"
            ])
            self.picload.startDecode(tmp_path)
            self["status"].setText("")
            
        except Exception as e:
            print(f"[PiconUpdater] Preview Error: {e}")
            self["status"].setText(_("Błąd podglądu"))

    def setPreview(self, picInfo=None):
        ptr = self.picload.getData()
        if ptr is not None:
            self["preview"].instance.setPixmap(ptr)
            self["preview"].instance.show()

    def createPiconDir(self):
        picon_dir = "/usr/share/enigma2/picon" 
        try:
            if os.path.islink("/picon"):
                real_picon_target = os.path.realpath("/picon")
                if os.path.isdir(real_picon_target):
                    picon_dir = real_picon_target
            
            if not os.path.exists(picon_dir):
                os.makedirs(picon_dir, mode=0o755)
            return picon_dir
        except Exception as e:
            raise Exception(f"Błąd tworzenia katalogu: {str(e)}")

    def get_package_name_from_ipk(self, ipk_filename):
        base = ipk_filename.rsplit('.ipk', 1)[0]
        match = re.search(r'([_-][0-9\._-]+_all$|_all$)', base)
        if match: return base[:match.start()]
        return base

    def install_ipk(self, package_path):
        self["status"].setText(_("Instalacja IPK..."))
        try:
            name = self.get_package_name_from_ipk(os.path.basename(package_path))
            subprocess.run(["opkg", "remove", "--force-depends", name], capture_output=True)
            
            subprocess.run(["opkg", "install", "--force-overwrite", package_path], check=True, capture_output=True)
            self.session.open(MessageBox, _("Zainstalowano! Restart GUI..."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
        except Exception as e:
            self.session.open(MessageBox, _("Błąd instalacji IPK: ") + str(e), MessageBox.TYPE_ERROR)
        finally:
            if os.path.exists(package_path): os.remove(package_path)

    def install_tar_xz(self, archive_path):
        temp_dir = "/tmp/picon_extract"
        picon_dir = self.createPiconDir()
        self["status"].setText(_("Instalacja TAR.XZ..."))
        
        try:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            with tarfile.open(archive_path, 'r:xz') as tar:
                tar.extractall(temp_dir)
                
            items = os.listdir(temp_dir)
            src = temp_dir
            if len(items) == 1 and os.path.isdir(os.path.join(temp_dir, items[0])):
                src = os.path.join(temp_dir, items[0])
                
            for item in os.listdir(src):
                source_path = os.path.join(src, item)
                destination_path = os.path.join(picon_dir, item)
                
                if os.path.exists(destination_path):
                    if os.path.isdir(destination_path):
                        shutil.rmtree(destination_path)
                    else:
                        os.remove(destination_path)
                
                shutil.move(source_path, destination_path)
                
            os.system("touch /usr/share/enigma2/picon/force_reload")
            self.session.open(MessageBox, _("Zainstalowano! Restart GUI..."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
            
        except Exception as e:
            self.session.open(MessageBox, _("Błąd TAR.XZ: ") + str(e), MessageBox.TYPE_ERROR)
        finally:
            if os.path.exists(archive_path): os.remove(archive_path)
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

    def download(self):
        # Ta funkcja jest teraz podpięta pod przycisk OK
        if self.selected_picon:
            url = self.selected_picon.get("url")
            if url:
                self["status"].setText(_("Pobieranie picon..."))
                self.download_timer = eTimer()
                self.download_timer.callback.append(self._do_download)
                self.download_timer.start(100, True)
            else:
                self.session.open(MessageBox, _("Brak URL!"), MessageBox.TYPE_ERROR)

    def _do_download(self):
        url = self.selected_picon.get("url")
        tmp_path = "/tmp/" + os.path.basename(url)
        try:
            r = requests.get(url, stream=True, timeout=300)
            r.raise_for_status()
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if tmp_path.endswith(".ipk"):
                self.install_ipk(tmp_path)
            elif tmp_path.endswith(".tar.xz"):
                self.install_tar_xz(tmp_path)
            else:
                self.session.open(MessageBox, _("Nieznany format!"), MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, _("Błąd pobierania: ") + str(e), MessageBox.TYPE_ERROR)

    def changeLanguage(self):
        self.session.open(MessageBox, _("Język systemowy używany domyślnie."), MessageBox.TYPE_INFO)

    def restartGUI(self, auto_restart=False):
        if auto_restart:
            if not hasattr(self, 'restart_timer'): self.restart_timer = eTimer()
            self.restart_timer.callback.append(lambda: self.console.execute("killall -9 enigma2"))
            self.restart_timer.start(3000, True)
        else:
            self.console.execute("killall -9 enigma2")

    def up(self): self["picon_list"].up()
    def down(self): self["picon_list"].down()
    def left(self): self["picon_list"].pageUp()
    def right(self): self["picon_list"].pageDown()
    def exit(self): self.close()

def main(session, **kwargs):
    session.open(PiconUpdater)

def Plugins(**kwargs):
    from Plugins.Plugin import PluginDescriptor
    return PluginDescriptor(
        name="Picon Updater",
        description="Pobieranie i instalacja picon (Sat/IPTV)",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/icon.png"),
        fnc=main
    )
