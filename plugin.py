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
        
        # Odczyt wersji z pliku
        version_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/version")
        self.version = "1.0.0" # Domyślna, gdyby pliku nie było
        if os.path.exists(version_path):
            try:
                with open(version_path, 'r') as f:
                    self.version = f.read().strip()
            except:
                pass
        
        # Standardowy tytuł okna (może być niewidoczny w niektórych skórkach)
        self.title = _("Picon Updater")

        self.console = eConsoleAppContainer()
        self.selected_picon = None
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.setPreview)
        
        # Ładowanie JSON
        json_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/picons.json")
        try:
            with open(json_path, 'r') as f:
                self.picons = json.load(f)
        except Exception as e:
            self.session.open(MessageBox, _("Błąd ładowania picons.json: ") + str(e), MessageBox.TYPE_ERROR)
            self.picons = []
        
        # Tworzenie listy
        self.picon_list = [picon["name"] for picon in self.picons]
        
        # Definicja widgetów
        self["picon_list"] = MenuList(self.picon_list)
        self["preview"] = Pixmap()
        self["status"] = Label("")
        self["description"] = Label(_("Wybierz picon aby zobaczyć podgląd"))
        
        # NOWY WIDGET: Nagłówek z wersją
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
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            
            self["status"].setText(_("Pobieranie podglądu..."))
            
            if url.startswith("file://"):
                local_path = url[7:]
                if os.path.exists(local_path):
                    shutil.copyfile(local_path, tmp_path)
                else:
                    raise Exception(f"Lokalny plik nie istnieje: {local_path}")
            else:
                r = requests.get(url, stream=True, timeout=10)
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
            print(f"[PiconUpdater] Błąd ładowania podglądu: {str(e)}")
            self["status"].setText(_("Błąd ładowania podglądu!"))
            self["preview"].instance.setPixmap(None)

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
            elif os.path.isdir("/picon"):
                picon_dir = "/picon"
            
            if not os.path.exists(picon_dir):
                os.makedirs(picon_dir, mode=0o755)
            return picon_dir
        except Exception as e:
            raise Exception(f"Nie można utworzyć katalogu picon: {str(e)}")

    def cleanupPiconDir(self, picon_dir):
        print(f"[PiconUpdater] Rozpoczynam czyszczenie katalogu: {picon_dir}")
        try:
            if os.path.exists(picon_dir):
                previews_path_in_plugin = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/previews")
                temp_previews_backup = "/tmp/picon_previews_backup"
                previews_moved = False

                if os.path.exists(previews_path_in_plugin) and os.path.isdir(previews_path_in_plugin) \
                   and os.path.commonpath([os.path.abspath(previews_path_in_plugin), os.path.abspath(picon_dir)]) == os.path.abspath(picon_dir):
                    try:
                        shutil.move(previews_path_in_plugin, temp_previews_backup)
                        previews_moved = True
                    except Exception:
                        traceback.print_exc()

                for item in os.listdir(picon_dir):
                    item_path = os.path.join(picon_dir, item)
                    try:
                        if os.path.islink(item_path) or os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception:
                        traceback.print_exc()

                if previews_moved:
                    try:
                        shutil.move(temp_previews_backup, previews_path_in_plugin)
                    except Exception:
                        traceback.print_exc()

        except Exception as e:
            print(f"[PiconUpdater] Błąd podczas czyszczenia: {e}")
            self.session.open(MessageBox, _("Błąd czyszczenia katalogu picon: ") + str(e), MessageBox.TYPE_ERROR)

        if not os.path.exists(picon_dir):
            os.makedirs(picon_dir, mode=0o755)

    def get_package_name_from_ipk(self, ipk_filename):
        base_name = ipk_filename.rsplit('.ipk', 1)[0]
        match = re.search(r'([_-][0-9\._-]+_all$|_all$)', base_name)
        if match:
            return base_name[:match.start()]
        return base_name

    def install_ipk(self, package_path):
        self["status"].setText(_("Instalowanie pakietu IPK..."))
        try:
            package_filename = os.path.basename(package_path)
            package_name_to_remove = self.get_package_name_from_ipk(package_filename)
            
            if package_name_to_remove:
                subprocess.run(["opkg", "remove", "--force-depends", package_name_to_remove], capture_output=True)
            
            self.cleanupPiconDir(self.createPiconDir())

            subprocess.run(["opkg", "install", "--force-overwrite", package_path], capture_output=True, check=True)
            
            self.session.open(MessageBox, _("Pakiet IPK zainstalowany pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)

        except subprocess.CalledProcessError as e:
            self["status"].setText(_("Błąd instalacji IPK!"))
            self.session.open(MessageBox, _("Błąd instalacji IPK: ") + e.stderr.strip(), MessageBox.TYPE_ERROR)
        except Exception as e:
            self["status"].setText(_("Nieznany błąd instalacji IPK!"))
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
            traceback.print_exc()
        finally:
            if os.path.exists(package_path):
                os.remove(package_path)
            self["status"].setText("")

    def install_tar_xz(self, archive_path):
        temp_extract_dir = "/tmp/picon_extract_temp"
        picon_dir = self.createPiconDir()
        
        try:
            if not os.access(picon_dir, os.W_OK):
                raise Exception(f"Brak uprawnień do zapisu w {picon_dir}")
            
            self.cleanupPiconDir(picon_dir)
            
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)

            self["status"].setText(_("Rozpakowywanie archiwum..."))
            
            with tarfile.open(archive_path, 'r:xz') as tar:
                for member in tar.getmembers():
                    if member.islnk() or member.issym(): continue
                    try:
                        tar.extract(member, path=temp_extract_dir)
                    except: continue

            extracted_items = os.listdir(temp_extract_dir)
            if not extracted_items:
                raise Exception(_("Rozpakowane archiwum jest puste."))

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
                    
            for root, dirs, files in os.walk(picon_dir):
                for d in dirs: os.chmod(os.path.join(root, d), 0o755)
                for f in files: os.chmod(os.path.join(root, f), 0o644)

            os.system("touch /usr/share/enigma2/picon/force_reload")
            
            self.session.open(MessageBox, _("Pobrano i zainstalowano pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            self.restartGUI(auto_restart=True)
            
        except Exception as e:
            self["status"].setText(_("Błąd instalacji TAR.XZ!"))
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
            traceback.print_exc()
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
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

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
