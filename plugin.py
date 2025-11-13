import os
import gettext
import json
import requests
import tarfile
import subprocess
import shutil
import stat
import traceback
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

class PiconUpdater(Screen):
    # Definicje skórek GUI dla różnych rozdzielczości ekranu
    desktop_size = getDesktop(0).size()
    
    # --- SKÓRKA FULL HD (1080p) ---
    if desktop_size.height() > 720:
        skin = """
            <screen position="center,center" size="900,600" title="Picon Updater" backgroundColor="#1a1a1a">
                <widget name="header_info" position="20,10" size="860,45" font="Regular;32" foregroundColor="#00ccff" transparent="1" halign="center" valign="center" />
                <eLabel position="20,60" size="860,2" backgroundColor="#333333" />

                <widget name="picon_list" position="50,80" size="400,350" itemHeight="35" font="Regular;26" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="470,80" size="380,300" backgroundColor="#333333" zPosition="1" />
                
                <widget name="status" position="470,390" size="380,30" font="Regular;22" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="470,430" size="380,60" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                
                <eLabel position="20,510" size="860,2" backgroundColor="#333333" />
                <widget name="footer" position="20,520" size="860,20" font="Regular;16" foregroundColor="#aaaaaa" transparent="1" halign="center" />
                
                <ePixmap position="20,550" size="200,40" pixmap="skin_default/buttons/red.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="240,550" size="200,40" pixmap="skin_default/buttons/green.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="460,550" size="200,40" pixmap="skin_default/buttons/yellow.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="680,550" size="200,40" pixmap="skin_default/buttons/blue.png" zPosition="1" transparent="1" alphatest="on" />
                
                <widget source="key_red" render="Label" position="20,550" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_green" render="Label" position="240,550" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_yellow" render="Label" position="460,550" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_blue" render="Label" position="680,550" size="200,40" zPosition="2" font="Regular;24" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
            </screen>
        """
    # --- SKÓRKA HD (720p) ---
    else:
        skin = """
            <screen position="center,center" size="620,450" title="Picon Updater" backgroundColor="#1a1a1a">
                <widget name="header_info" position="10,5" size="600,35" font="Regular;24" foregroundColor="#00ccff" transparent="1" halign="center" valign="center" />
                <eLabel position="10,45" size="600,1" backgroundColor="#333333" />

                <widget name="picon_list" position="20,60" size="280,260" itemHeight="30" font="Regular;20" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="310,60" size="280,180" backgroundColor="#333333" zPosition="1" />
                
                <widget name="status" position="310,250" size="280,30" font="Regular;18" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="310,290" size="280,60" font="Regular;16" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                
                <eLabel position="10,370" size="600,1" backgroundColor="#333333" />
                <widget name="footer" position="10,380" size="600,20" font="Regular;14" foregroundColor="#aaaaaa" transparent="1" halign="center" />
                
                <ePixmap position="20,410" size="140,35" pixmap="skin_default/buttons/red.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="170,410" size="140,35" pixmap="skin_default/buttons/green.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="320,410" size="140,35" pixmap="skin_default/buttons/yellow.png" zPosition="1" transparent="1" alphatest="on" />
                <ePixmap position="470,410" size="140,35" pixmap="skin_default/buttons/blue.png" zPosition="1" transparent="1" alphatest="on" />
                
                <widget source="key_red" render="Label" position="20,410" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_green" render="Label" position="170,410" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_yellow" render="Label" position="320,410" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
                <widget source="key_blue" render="Label" position="470,410" size="140,35" zPosition="2" font="Regular;20" valign="center" halign="center" transparent="1" foregroundColor="#ffffff" />
            </screen>
        """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        # --- KONFIGURACJA ---
        self.github_user = "OliOli2013"
        self.repo_name = "PiconUpdater"
        self.version_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.repo_name}/main/version"
        self.installer_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.repo_name}/main/installer.sh"
        
        # Odczyt wersji
        version_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/version")
        self.version = "1.0.0"
        if os.path.exists(version_path):
            try:
                with open(version_path, 'r') as f:
                    self.version = f.read().strip()
            except:
                pass
        
        self.title = _("Picon Updater")
        self.console = eConsoleAppContainer()
        self.selected_picon = None
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.setPreview)
        
        json_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/picons.json")
        try:
            with open(json_path, 'r') as f:
                self.picons = json.load(f)
        except Exception as e:
            self.session.open(MessageBox, _("Błąd ładowania picons.json: ") + str(e), MessageBox.TYPE_ERROR)
            self.picons = []
        
        self.picon_list = [picon["name"] for picon in self.picons]
        
        self["picon_list"] = MenuList(self.picon_list)
        self["preview"] = Pixmap()
        self["status"] = Label("")
        self["description"] = Label(_("Wybierz picon aby zobaczyć podgląd"))
        self["header_info"] = Label(f"Picon Updater v{self.version}")
        
        self["key_red"] = Label(_("Wyjście"))
        self["key_green"] = Label(_("Pobierz"))
        self["key_yellow"] = Label(_("Język"))
        self["key_blue"] = Label(_("Restart GUI"))
        self["footer"] = Label(_("by: Paweł Pawełek | msisystem@t.pl | Facebook: Enigma 2, Oprogramowanie i dodatki"))
        
        self["actions"] = ActionMap(["ColorActions", "NavigationActions", "SetupActions"], 
        {
            "red": self.exit,
            "green": self.download,
            "yellow": self.changeLanguage,
            "blue": self.restartGUI,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
            "cancel": self.exit,
            "ok": self.download
        }, -1)
        
        self["picon_list"].onSelectionChanged.append(self.selectionChanged)
        self.onLayoutFinish.append(self.selectionChanged)
        
        self.update_timer = eTimer()
        self.update_timer.callback.append(self.checkUpdate)
        self.update_timer.start(1000, True)

    def checkUpdate(self):
        print("[PiconUpdater] Sprawdzanie aktualizacji...")
        try:
            r = requests.get(self.version_url, timeout=5)
            if r.status_code == 200:
                remote_version = r.text.strip()
                if remote_version != self.version:
                    self.session.openWithCallback(self.updatePluginConfirmed, MessageBox, 
                        _("Dostępna jest nowa wersja wtyczki!\nLokalna: %s\nNowa: %s\n\nCzy chcesz zaktualizować teraz?") % (self.version, remote_version), 
                        MessageBox.TYPE_YESNO)
        except:
            pass

    def updatePluginConfirmed(self, answer):
        if answer:
            self.session.open(MessageBox, _("Rozpoczynam aktualizację wtyczki...\nGUI zrestartuje się automatycznie."), MessageBox.TYPE_INFO, timeout=3)
            cmd = f"wget -qO - {self.installer_url} | /bin/sh"
            self.console.execute(cmd)

    def selectionChanged(self):
        selected_index = self["picon_list"].getSelectionIndex()
        if selected_index >= 0 and selected_index < len(self.picons):
            self.selected_picon = self.picons[selected_index]
            description_text = self.selected_picon["name"]
            satellites = self.selected_picon.get("satellites")
            if satellites and isinstance(satellites, list):
                description_text += f"\nSat: {', '.join(satellites)}"
            elif satellites and isinstance(satellites, str):
                description_text += f"\nSat: {satellites}"
            self["description"].setText(description_text)
            self.loadPreview(self.selected_picon["preview"])
        else:
            self.selected_picon = None
            self["description"].setText(_("Nie wybrano picona"))
            self["preview"].instance.setPixmap(None)

    def loadPreview(self, url):
        try:
            tmp_path = "/tmp/picon_preview.png"
            if os.path.exists(tmp_path): os.remove(tmp_path)
            self["status"].setText(_("Pobieranie podglądu..."))
            if url.startswith("file://"):
                local_path = url[7:]
                if os.path.exists(local_path): shutil.copyfile(local_path, tmp_path)
            else:
                r = requests.get(url, stream=True, timeout=10)
                r.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            self.picload.setPara([self["preview"].instance.size().width(), self["preview"].instance.size().height(), 1, 1, False, 1, "#00000000"])
            self.picload.startDecode(tmp_path)
            self["status"].setText("")
        except Exception as e:
            print(f"[PiconUpdater] Preview error: {e}")
            self["status"].setText(_("Błąd podglądu!"))
            self["preview"].instance.setPixmap(None)

    def setPreview(self, picInfo=None):
        ptr = self.picload.getData()
        if ptr is not None:
            self["preview"].instance.setPixmap(ptr)
            self["preview"].instance.show()

    # --- MODYFIKACJA DLA KATALOGU PICON ---
    def createPiconDir(self):
        """
        Zwraca ścieżkę do /usr/share/enigma2/picon.
        Jeśli jest to symlink (np. do USB), zwraca ścieżkę docelową.
        Jeśli katalog nie istnieje, tworzy go.
        """
        target_path = "/usr/share/enigma2/picon"
        
        # Jeśli to symlink, podążamy za nim, aby operować na prawdziwym katalogu
        if os.path.islink(target_path):
            real_path = os.path.realpath(target_path)
            print(f"[PiconUpdater] Wykryto symlink {target_path} -> {real_path}")
            target_path = real_path

        # Jeśli katalog nie istnieje, tworzymy go
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path, mode=0o755)
                print(f"[PiconUpdater] Utworzono katalog: {target_path}")
            except Exception as e:
                print(f"[PiconUpdater] Błąd tworzenia katalogu: {e}")
                raise Exception(f"Nie można utworzyć katalogu {target_path}")
        
        return target_path

    def cleanupPiconDir(self, picon_dir):
        """
        Usuwa WSZYSTKIE pliki w picon_dir przed nową instalacją.
        """
        print(f"[PiconUpdater] Czyszczenie katalogu: {picon_dir}")
        if os.path.exists(picon_dir):
            # Zabezpieczenie folderu previews wewnątrz pluginu (gdyby tam był)
            previews_path_in_plugin = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/previews")
            temp_previews_backup = "/tmp/picon_previews_backup"
            previews_moved = False
            
            # Jeśli usuwamy w miejscu gdzie jest plugin, chronimy podglądy
            if os.path.commonpath([os.path.abspath(previews_path_in_plugin), os.path.abspath(picon_dir)]) == os.path.abspath(picon_dir):
                 if os.path.exists(previews_path_in_plugin):
                    try:
                        shutil.move(previews_path_in_plugin, temp_previews_backup)
                        previews_moved = True
                    except: pass

            for item in os.listdir(picon_dir):
                item_path = os.path.join(picon_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"[PiconUpdater] Błąd usuwania {item}: {e}")

            # Przywracanie podglądów
            if previews_moved:
                try:
                    shutil.move(temp_previews_backup, previews_path_in_plugin)
                except: pass
    # --------------------------------------

    def get_package_name_from_ipk(self, ipk_filename):
        base_name = ipk_filename.rsplit('.ipk', 1)[0]
        match = re.search(r'([_-][0-9\._-]+_all$|_all$)', base_name)
        if match: return base_name[:match.start()]
        return base_name

    def install_ipk(self, package_path):
        self["status"].setText(_("Instalowanie pakietu IPK..."))
        try:
            # 1. Sprawdź i wyczyść katalog docelowy (usuń stare picony)
            target_dir = self.createPiconDir()
            self.cleanupPiconDir(target_dir)

            # 2. Odinstaluj stary pakiet systemowy (opcjonalne, ale dobre dla porządku w opkg)
            package_filename = os.path.basename(package_path)
            package_name_to_remove = self.get_package_name_from_ipk(package_filename)
            if package_name_to_remove:
                subprocess.run(["opkg", "remove", "--force-depends", package_name_to_remove], capture_output=True)

            # 3. Instaluj nowy
            subprocess.run(["opkg", "install", "--force-overwrite", package_path], capture_output=True, check=True)
            
            self.session.open(MessageBox, _("Pakiet IPK zainstalowany pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
        except Exception as e:
            self["status"].setText(_("Błąd instalacji IPK!"))
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
        finally:
            if os.path.exists(package_path): os.remove(package_path)
            self["status"].setText("")

    def install_tar_xz(self, archive_path):
        temp_extract_dir = "/tmp/picon_extract_temp"
        
        try:
            # 1. Przygotuj katalog docelowy (usuń stare picony)
            picon_dir = self.createPiconDir()
            if not os.access(picon_dir, os.W_OK): raise Exception(f"Brak uprawnień do {picon_dir}")
            self.cleanupPiconDir(picon_dir)
            
            # 2. Rozpakuj do TEMP
            if os.path.exists(temp_extract_dir): shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)
            self["status"].setText(_("Rozpakowywanie archiwum..."))
            with tarfile.open(archive_path, 'r:xz') as tar:
                for member in tar.getmembers():
                    if member.islnk() or member.issym(): continue
                    try: tar.extract(member, path=temp_extract_dir)
                    except: continue

            # 3. Przenieś do /usr/share/enigma2/picon
            extracted_items = os.listdir(temp_extract_dir)
            source_dir_for_move = temp_extract_dir
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                source_dir_for_move = os.path.join(temp_extract_dir, extracted_items[0])

            for item in os.listdir(source_dir_for_move):
                source_path = os.path.join(source_dir_for_move, item)
                destination_path = os.path.join(picon_dir, item)
                try:
                    if os.path.exists(destination_path):
                        if os.path.isdir(destination_path): shutil.rmtree(destination_path)
                        else: os.remove(destination_path)
                    shutil.move(source_path, destination_path)
                except: traceback.print_exc()
            
            # 4. Uprawnienia i reload
            for root, dirs, files in os.walk(picon_dir):
                for d in dirs: os.chmod(os.path.join(root, d), 0o755)
                for f in files: os.chmod(os.path.join(root, f), 0o644)

            os.system("touch /usr/share/enigma2/picon/force_reload")
            self.session.open(MessageBox, _("Pobrano i zainstalowano pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
            
        except Exception as e:
            self["status"].setText(_("Błąd instalacji TAR.XZ!"))
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
        finally:
            self["status"].setText("")
            if os.path.exists(archive_path): os.remove(archive_path)
            if os.path.exists(temp_extract_dir): shutil.rmtree(temp_extract_dir, ignore_errors=True)

    def download(self):
        if self.selected_picon:
            url = self.selected_picon.get("url")
            if url:
                self["status"].setText(_("Pobieranie picon..."))
                self.download_timer = eTimer()
                self.download_timer.callback.append(self._do_download)
                self.download_timer.start(100, True)
            else:
                self.session.open(MessageBox, _("Brak URL do pobrania."), MessageBox.TYPE_ERROR)
        else:
            self.session.open(MessageBox, _("Proszę wybrać picon."), MessageBox.TYPE_INFO)

    def _do_download(self):
        if hasattr(self, 'download_timer') and self.download_timer is not None:
            self.download_timer = None
        if self.selected_picon:
            url = self.selected_picon.get("url")
            if url:
                tmp_archive_path = "/tmp/" + os.path.basename(url)
                try:
                    r = requests.get(url, stream=True, timeout=300)
                    r.raise_for_status()
                    with open(tmp_archive_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

                    if tmp_archive_path.lower().endswith(".ipk"):
                        self.install_ipk(tmp_archive_path)
                    elif tmp_archive_path.lower().endswith(".tar.xz"):
                        self.install_tar_xz(tmp_archive_path)
                    else:
                        self.session.open(MessageBox, _("Nieobsługiwany format pliku."), MessageBox.TYPE_ERROR)
                        if os.path.exists(tmp_archive_path): os.remove(tmp_archive_path)
                except Exception as e:
                    self["status"].setText(_("Błąd pobierania!"))
                    self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
        
    def changeLanguage(self):
        self.session.open(MessageBox, _("Funkcja zmiany języka niezaimplementowana."), MessageBox.TYPE_INFO)

    def restartGUI(self, auto_restart=False):
        if auto_restart:
            self.session.open(MessageBox, _("GUI zostanie zrestartowane..."), MessageBox.TYPE_INFO, timeout=3)
            if not hasattr(self, 'restart_timer') or self.restart_timer is None:
                self.restart_timer = eTimer()
            self.restart_timer.callback.append(lambda: self.console.execute("killall -9 enigma2"))
            self.restart_timer.start(3000, True)
        else:
            self.session.open(MessageBox, _("Restartowanie GUI..."), MessageBox.TYPE_INFO)
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
        name="Instalacja i aktualizacja Picon",
        description="Pobieranie i instalacja zestawów picon",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/icon.png"),
        fnc=main
    )
