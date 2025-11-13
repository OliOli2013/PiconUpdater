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
    if desktop_size.height() > 720:
        skin = """
            <screen position="center,center" size="900,550" title="Instalacja i aktualizacja Picon" backgroundColor="#1a1a1a">
                <widget name="picon_list" position="50,50" size="400,350" itemHeight="35" font="Regular;26" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="470,50" size="380,300" backgroundColor="#333333" zPosition="1" />
                <widget name="status" position="470,360" size="380,30" font="Regular;22" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="470,400" size="380,50" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                
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
    else:
        skin = """
            <screen position="center,center" size="620,400" title="Instalacja i aktualizacja Picon" backgroundColor="#1a1a1a">
                <widget name="picon_list" position="20,20" size="280,260" itemHeight="30" font="Regular;20" foregroundColor="#ffffff" transparent="1" scrollbarMode="showOnDemand" />
                <widget name="preview" position="310,20" size="280,180" backgroundColor="#333333" zPosition="1" />
                <widget name="status" position="310,210" size="280,30" font="Regular;18" foregroundColor="#ffff00" transparent="1" halign="center" />
                <widget name="description" position="310,250" size="280,60" font="Regular;16" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                
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
        self.title = _("Instalacja i aktualizacja Picon")
        self.console = eConsoleAppContainer()
        self.selected_picon = None
        self.picload = ePicLoad()
        # Podłączanie metody setPreview do sygnału PictureData, aby ładować podglądy
        self.picload.PictureData.get().append(self.setPreview)
        
        # Ścieżka do pliku picons.json
        json_path = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/picons.json")
        try:
            with open(json_path, 'r') as f:
                self.picons = json.load(f)
        except Exception as e:
            # Wyświetl komunikat o błędzie, jeśli picons.json nie może być załadowany
            self.session.open(MessageBox, _("Błąd ładowania picons.json: ") + str(e), MessageBox.TYPE_ERROR)
            self.picons = [] # Ustaw pustą listę picon, aby zapobiec dalszym błędom
        
        # Tworzenie listy nazw picon do wyświetlenia w MenuList
        self.picon_list = [picon["name"] for picon in self.picons]
        
        # Definicja widgetów w ekranie
        self["picon_list"] = MenuList(self.picon_list)
        self["preview"] = Pixmap()
        self["status"] = Label("")
        self["description"] = Label(_("Wybierz picon aby zobaczyć podgląd"))
        # Etykiety dla kolorowych przycisków
        self["key_red"] = Label(_("Wyjście"))
        self["key_green"] = Label(_("Pobierz"))
        self["key_yellow"] = Label(_("Język"))
        self["key_blue"] = Label(_("Restart GUI")) # Przycisk dla wymuszonego restartu
        self["footer"] = Label(_("by: Paweł Pawełek | msisystem@t.pl | Facebook: Enigma 2, Oprogramowanie i dodatki"))
        
        # Definicja akcji klawiszy
        self["actions"] = ActionMap(["ColorActions", "NavigationActions", "SetupActions"], 
        {
            "red": self.exit,        # Czerwony przycisk: wyjście z pluginu
            "green": self.download,  # Zielony przycisk: pobieranie i instalacja
            "yellow": self.changeLanguage, # Żółty przycisk: zmiana języka (niezaimplementowana)
            "blue": self.restartGUI, # Niebieski przycisk: ręczny restart GUI
            "up": self.up,           # Klawisz góra: przewiń listę w górę
            "down": self.down,       # Klawisz dół: przewiń listę w dół
            "left": self.left,       # Klawisz lewo: przewiń listę stronę w górę
            "right": self.right,     # Klawisz prawo: przewiń listę stronę w dół
            "cancel": self.exit,     # Klawisz exit/cancel: wyjście z pluginu
            "ok": self.download      # Klawisz OK: pobieranie i instalacja
        }, -1)
        
        # Podłączenie metody selectionChanged do zdarzenia zmiany wyboru na liście
        self["picon_list"].onSelectionChanged.append(self.selectionChanged)
        # Wywołanie selectionChanged po załadowaniu GUI, aby wyświetlić podgląd dla pierwszego elementu
        self.onLayoutFinish.append(self.selectionChanged)

    def selectionChanged(self):
        """Metoda wywoływana przy zmianie wyboru na liście picon, aktualizuje opis i podgląd."""
        selected_index = self["picon_list"].getSelectionIndex()
        if selected_index >= 0 and selected_index < len(self.picons):
            self.selected_picon = self.picons[selected_index]
            description_text = self.selected_picon["name"]
            
            # Pobierz i dodaj informację o satelitach, jeśli pole 'satellites' istnieje w picons.json
            satellites = self.selected_picon.get("satellites")
            if satellites and isinstance(satellites, list): # Upewnij się, że to lista
                description_text += f"\nSat: {', '.join(satellites)}" # Dodaj satelity w nowej linii
            elif satellites and isinstance(satellites, str): # Jeśli to pojedynczy string
                description_text += f"\nSat: {satellites}" # Dodaj satelity w nowej linii
            
            self["description"].setText(description_text)
            self.loadPreview(self.selected_picon["preview"])
        else:
            self.selected_picon = None
            self["description"].setText(_("Nie wybrano picona"))
            self["preview"].instance.setPixmap(None)

    def loadPreview(self, url):
        """Pobiera i wyświetla podgląd picony z podanego URL (lokalnego lub zdalnego)."""
        try:
            tmp_path = "/tmp/picon_preview.png"
            # Usuń stary plik podglądu, jeśli istnieje
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            
            self["status"].setText(_("Pobieranie podglądu..."))
            
            # Sprawdź, czy URL to lokalna ścieżka (file://) czy zdalny adres HTTP/HTTPS
            if url.startswith("file://"):
                local_path = url[7:]  # Usuń "file://" z początku, aby uzyskać czystą ścieżkę
                if os.path.exists(local_path):
                    shutil.copyfile(local_path, tmp_path) # Skopiuj lokalny plik do /tmp
                else:
                    raise Exception(f"Lokalny plik nie istnieje: {local_path}")
            else:
                # Pobierz plik z internetu
                r = requests.get(url, stream=True, timeout=10) # Timeout 10 sekund na pobieranie
                r.raise_for_status() # Zgłoś wyjątek dla kodów statusu HTTP >= 400
                with open(tmp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Ustaw parametry dla ePicLoad i rozpocznij dekodowanie obrazu
            self.picload.setPara([
                self["preview"].instance.size().width(),
                self["preview"].instance.size().height(),
                1, 1, False, 1, "#00000000" # Parametry skalowania i kolor tła
            ])
            self.picload.startDecode(tmp_path) # Rozpocznij dekodowanie obrazu
            self["status"].setText("") # Wyczyść status po zakończeniu operacji
            
        except Exception as e:
            print(f"[PiconUpdater] Błąd ładowania podglądu: {str(e)}")
            self["status"].setText(_("Błąd ładowania podglądu!"))
            self["preview"].instance.setPixmap(None) # Usuń podgląd w przypadku błędu

    def setPreview(self, picInfo=None):
        """Metoda wywoływana po zakończeniu dekodowania obrazu przez ePicLoad."""
        ptr = self.picload.getData()
        if ptr is not None:
            self["preview"].instance.setPixmap(ptr) # Ustaw zdekodowany obraz jako podgląd
            self["preview"].instance.show() # Upewnij się, że widget podglądu jest widoczny

    def createPiconDir(self):
        """Tworzy katalog docelowy dla picon, jeśli nie istnieje.
        Domyślnie używa /usr/share/enigma2/picon, ale może być zmienione.
        """
        # Upewniamy się, że picon_dir to zawsze prawidłowa ścieżka bez końcowego slasha.
        picon_dir = "/usr/share/enigma2/picon" 
        
        try:
            # Sprawdź, czy /picon jest symlinkiem, a jeśli tak, użyj jego celu
            if os.path.islink("/picon"):
                real_picon_target = os.path.realpath("/picon")
                if os.path.isdir(real_picon_target):
                    picon_dir = real_picon_target
                    print(f"[PiconUpdater] Wykryto symlink /picon -> {picon_dir}. Picony będą instalowane tam.")
                else:
                    print(f"[PiconUpdater] Cel symlinka /picon ({real_picon_target}) nie jest katalogiem. Używam domyślnego {picon_dir}.")
            elif os.path.isdir("/picon"):
                # Jeśli /picon jest katalogiem, używamy go bezpośrednio
                picon_dir = "/picon"
                print(f"[PiconUpdater] /picon jest katalogiem. Picony będą instalowane tam.")
            else:
                # Jeśli /picon nie istnieje lub nie jest katalogiem/symlinkiem, używamy domyślnego
                print(f"[PiconUpdater] /picon nie istnieje lub nie jest katalogiem/symlinkiem. Używam domyślnego {picon_dir}.")
            
            # Upewnij się, że docelowy katalog istnieje
            if not os.path.exists(picon_dir):
                os.makedirs(picon_dir, mode=0o755) # Utwórz katalog z uprawnieniami 755
                print(f"[PiconUpdater] Utworzono katalog picon: {picon_dir}")
            return picon_dir
        except Exception as e:
            raise Exception(f"Nie można utworzyć katalogu picon: {str(e)}")

    def cleanupPiconDir(self, picon_dir):
        """Usuwa wszystkie pliki i katalogi w katalogu picon,
        z wyjątkiem podkatalogu 'previews' jeśli istnieje wewnątrz pluginu.
        Jest to agresywne czyszczenie, mające na celu uniknięcie konfliktów.
        """
        print(f"[PiconUpdater] Rozpoczynam czyszczenie katalogu: {picon_dir}")
        try:
            if os.path.exists(picon_dir):
                previews_path_in_plugin = resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/previews")
                temp_previews_backup = "/tmp/picon_previews_backup"
                previews_moved = False

                # Sprawdź, czy katalog 'previews' pluginu jest podkatalogiem lokalizacji picon.
                # Jest to ważne, aby nie próbować przenosić katalogu previews z innych miejsc.
                # Używamy os.path.commonpath aby sprawdzić, czy ścieżka previews jest w ścieżce picon_dir.
                if os.path.exists(previews_path_in_plugin) and os.path.isdir(previews_path_in_plugin) \
                   and os.path.commonpath([os.path.abspath(previews_path_in_plugin), os.path.abspath(picon_dir)]) == os.path.abspath(picon_dir):
                    try:
                        shutil.move(previews_path_in_plugin, temp_previews_backup)
                        previews_moved = True
                        print(f"[PiconUpdater] Tymczasowo przeniesiono katalog 'previews' z {previews_path_in_plugin} do {temp_previews_backup}")
                    except Exception as e:
                        print(f"[PiconUpdater] Błąd podczas przenoszenia katalogu 'previews': {e}")
                        traceback.print_exc()

                # Usuń wszystkie elementy z głównego katalogu picon
                for item in os.listdir(picon_dir):
                    item_path = os.path.join(picon_dir, item)
                    try:
                        if os.path.islink(item_path) or os.path.isfile(item_path):
                            os.remove(item_path)
                            print(f"[PiconUpdater] Usunięto plik/symlink: {item_path}")
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            print(f"[PiconUpdater] Usunięto katalog: {item_path}")
                    except Exception as e_inner:
                        print(f"[PiconUpdater] Błąd podczas usuwania elementu {item_path}: {e_inner}. Kontynuuję.")
                        traceback.print_exc()
                
                print(f"[PiconUpdater] Zawartość katalogu picon wyczyszczona: {picon_dir}")

                # Przywróć katalog 'previews' na swoje miejsce, jeśli został przeniesiony
                if previews_moved:
                    try:
                        shutil.move(temp_previews_backup, previews_path_in_plugin) # Przywróć do oryginalnej ścieżki
                        print(f"[PiconUpdater] Przywrócono katalog 'previews' do {previews_path_in_plugin}")
                    except Exception as e:
                        print(f"[PiconUpdater] Błąd podczas przywracania katalogu 'previews': {e}")
                        traceback.print_exc()

        except Exception as e:
            print(f"[PiconUpdater] Krytyczny błąd podczas czyszczenia katalogu picon {picon_dir}: {e}")
            traceback.print_exc()
            self.session.open(MessageBox, _("Błąd czyszczenia katalogu picon: ") + str(e), MessageBox.TYPE_ERROR)

        # Upewnij się, że katalog picon istnieje na końcu, nawet po problemach z czyszczeniem
        if not os.path.exists(picon_dir):
            try:
                os.makedirs(picon_dir, mode=0o755)
                print(f"[PiconUpdater] Utworzono brakujący katalog picon: {picon_dir}")
            except Exception as e:
                raise Exception(f"Nie można utworzyć katalogu picon: {str(e)}")
        print(f"[PiconUpdater] Zakończono czyszczenie katalogu: {picon_dir}")

    def get_package_name_from_ipk(self, ipk_filename):
        """
        Próbuje wyodrębnić nazwę pakietu z nazwy pliku IPK.
        Służy do identyfikacji pakietu do usunięcia.
        Obsługuje formaty typu:
        - nazwa_pakietu_WERSJA_arch.ipk
        - nazwa_pakietu-WERSJA_arch.ipk
        - nazwa_pakietu_YYYY-MM-DD--HH-MM-SS_arch.ipk
        - nazwa_pakietu_all.ipk
        """
        base_name = ipk_filename.rsplit('.ipk', 1)[0]
        
        # Regex do dopasowania od końca stringu
        match = re.search(r'([_-][0-9\._-]+_all$|_all$)', base_name)
        if match:
            return base_name[:match.start()]
        
        print(f"[PiconUpdater] Nie znaleziono standardowego wzorca wersji w nazwie IPK: {ipk_filename}. Próba użycia całej nazwy bazowej: {base_name}")
        return base_name

    def install_ipk(self, package_path):
        """Instaluje pakiet .ipk za pomocą opkg.
        Próbuje odinstalować poprzednią wersję pakietu, a następnie instaluje nową,
        wymuszając nadpisanie plików w przypadku konfliktu.
        """
        self["status"].setText(_("Instalowanie pakietu IPK..."))
        print(f"[PiconUpdater] Rozpoczynam instalację IPK: {package_path}")
        
        try:
            package_filename = os.path.basename(package_path)
            package_name_to_remove = self.get_package_name_from_ipk(package_filename)
            
            # Krok 1: Próba odinstalowania poprzedniego pakietu o tej samej nazwie (jeśli istnieje)
            if package_name_to_remove:
                print(f"[PiconUpdater] Próba odinstalowania starego pakietu: {package_name_to_remove}")
                remove_process = subprocess.run(["opkg", "remove", "--force-depends", package_name_to_remove],
                                                capture_output=True, text=True)
                print(f"[PiconUpdater] opkg remove stdout: {remove_process.stdout}")
                print(f"[PiconUpdater] opkg remove stderr: {remove_process.stderr}")
                if remove_process.returncode != 0 and "No packages removed" not in remove_process.stderr and \
                   "Unknown package" not in remove_process.stderr:
                    print(f"[PiconUpdater] Ostrzeżenie: Błąd podczas usuwania pakietu {package_name_to_remove}: {remove_process.stderr}")
            
            # Krok 2: Całkowite wyczyszczenie katalogu picon przed instalacją IPK
            self.cleanupPiconDir(self.createPiconDir())

            # Krok 3: Instalacja nowego pakietu z opcją --force-overwrite
            print(f"[PiconUpdater] Próba instalacji nowego pakietu: {package_path}")
            install_process = subprocess.run(["opkg", "install", "--force-overwrite", package_path],
                                             capture_output=True, text=True, check=True)
            print(f"[PiconUpdater] opkg install stdout: {install_process.stdout}")
            print(f"[PiconUpdater] opkg install stderr: {install_process.stderr}")
            
            # Krok 4: Poinformuj użytkownika i zrestartuj GUI
            self.session.open(MessageBox, _("Pakiet IPK zainstalowany pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            print(f"[PiconUpdater] Zakończono instalację IPK: {package_path}")
            self.restartGUI(auto_restart=True)

        except subprocess.CalledProcessError as e:
            error_message = _("Błąd instalacji IPK: ") + e.stderr.strip()
            print(f"[PiconUpdater] IPK installation error: {e}")
            print(f"[PiconUpdater] opkg stdout (on error): {e.stdout}")
            print(f"[PiconUpdater] opkg stderr (on error): {e.stderr}")
            self["status"].setText(_("Błąd instalacji IPK! Sprawdź logi."))
            self.session.open(MessageBox, error_message, MessageBox.TYPE_ERROR)

        except Exception as e:
            print(f"[PiconUpdater] Unexpected IPK installation error: {e}")
            self["status"].setText(_("Nieznany błąd instalacji IPK! Sprawdź logi."))
            self.session.open(MessageBox, _("Nieznany błąd podczas instalacji IPK: ") + str(e), MessageBox.TYPE_ERROR)
            traceback.print_exc()

        finally:
            if os.path.exists(package_path):
                os.remove(package_path)
                print(f"[PiconUpdater] Usunięto pobrany plik IPK: {package_path}")
            self["status"].setText("")


    def install_tar_xz(self, archive_path):
        """Instaluje picony z archiwum TAR.XZ.
        Rozpakowuje do tymczasowego katalogu, a następnie przenosi pliki do docelowego /picon,
        uwzględniając strukturę z pojedynczym głównym katalogiem (np. 'logos' lub 'snp-full') w archiwum.
        """
        temp_extract_dir = "/tmp/picon_extract_temp"
        picon_dir = self.createPiconDir() # Upewnij się, że katalog picon istnieje
        
        try:
            if not os.access(picon_dir, os.W_OK):
                raise Exception(f"Brak uprawnień do zapisu w {picon_dir}")
            
            # Krok 1: Wyczyść katalog picon przed rozpakowaniem
            self.cleanupPiconDir(picon_dir)
            
            # Krok 2: Stwórz tymczasowy katalog do rozpakowania
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir) # Usuń stary, jeśli istnieje
            os.makedirs(temp_extract_dir) # Utwórz nowy
            print(f"[PiconUpdater] Tymczasowy katalog rozpakowywania utworzony: {temp_extract_dir}")

            self["status"].setText(_("Rozpakowywanie archiwum..."))
            print(f"[PiconUpdater] Rozpakowywanie archiwum: {archive_path} do {temp_extract_dir}")
            
            # Krok 3: Rozpakuj archiwum do tymczasowego katalogu
            with tarfile.open(archive_path, 'r:xz') as tar:
                for member in tar.getmembers():
                    # Zabezpieczenie przed atakami Path Traversal i problemami z linkami
                    if member.islnk() or member.issym():
                        print(f"[PiconUpdater] Ostrzeżenie: Pomijam link symboliczny/twardy link w archiwum: {member.name}")
                        continue
                    
                    target_path_full = os.path.join(temp_extract_dir, member.name)
                    abs_temp_extract_dir = os.path.abspath(temp_extract_dir)
                    abs_target_path_full = os.path.abspath(target_path_full)

                    # Upewnij się, że ścieżka docelowa znajduje się wewnątrz temp_extract_dir
                    if not abs_target_path_full.startswith(abs_temp_extract_dir + os.sep) and \
                       abs_temp_extract_dir != abs_target_path_full:
                        raise Exception(f"Próba rozpakowania pliku poza dozwolonym katalogiem: {member.name}")

                    try:
                        tar.extract(member, path=temp_extract_dir)
                    except Exception as extract_e:
                        print(f"[PiconUpdater] Błąd podczas rozpakowywania pliku {member.name}: {extract_e}. Pomijam.")
                        traceback.print_exc()
                        continue

            # Krok 4: Przenieś zawartość z tymczasowego katalogu do docelowego katalogu picon
            print(f"[PiconUpdater] Przenoszenie zawartości z {temp_extract_dir} do {picon_dir}")
            extracted_items = os.listdir(temp_extract_dir)
            
            if not extracted_items:
                raise Exception(_("Rozpakowane archiwum jest puste."))

            source_dir_for_move = temp_extract_dir # Domyślne źródło do przeniesienia

            # Heurystyka: jeśli w temp_extract_dir jest tylko jeden element i jest to katalog,
            # (np. 'logos', 'snp-full.220x132', 'srp')
            # to oznacza, że archiwum spakowało picony wewnątrz tego katalogu.
            # Musimy przenieść ZAWARTOŚĆ tego katalogu do picon_dir.
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                detected_subdir = os.path.join(temp_extract_dir, extracted_items[0])
                print(f"[PiconUpdater] Wykryto pojedynczy podkatalog w archiwum: {extracted_items[0]}. Przenoszę jego zawartość.")
                source_dir_for_move = detected_subdir
            else:
                print(f"[PiconUpdater] Brak pojedynczego podkatalogu w archiwum. Przenoszę bezpośrednio zawartość {temp_extract_dir}.")

            # Przeniesienie wszystkich elementów z source_dir_for_move do picon_dir
            for item in os.listdir(source_dir_for_move):
                source_path = os.path.join(source_dir_for_move, item)
                destination_path = os.path.join(picon_dir, item) # Docelowo zawsze do /picon
                try:
                    # Jeśli plik/katalog już istnieje w docelowym miejscu, usuń go przed przeniesieniem
                    if os.path.exists(destination_path):
                        if os.path.isdir(destination_path):
                            shutil.rmtree(destination_path)
                        else:
                            os.remove(destination_path)
                    
                    shutil.move(source_path, destination_path)
                    print(f"[PiconUpdater] Przeniesiono: {source_path} -> {destination_path}")
                except Exception as move_e:
                    print(f"[PiconUpdater] Błąd podczas przenoszenia {source_path} do {destination_path}: {move_e}. Pomijam.")
                    traceback.print_exc()
                    
            # Krok 5: Ustaw prawidłowe uprawnienia dla wszystkich plików i katalogów picon
            print(f"[PiconUpdater] Ustawianie uprawnień w {picon_dir}...")
            for root, dirs, files in os.walk(picon_dir):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o755) # Katalogi: rwxr-xr-x
                for f in files:
                    os.chmod(os.path.join(root, f), 0o644) # Pliki: rw-r--r--
            print(f"[PiconUpdater] Uprawnienia ustawione.")

            # Krok 6: Wymuś odświeżenie GUI (touch force_reload)
            os.system("touch /usr/share/enigma2/picon/force_reload")
            print(f"[PiconUpdater] Utworzono force_reload plik.")
            
            # Krok 7: Poinformuj użytkownika i zrestartuj GUI
            self.session.open(MessageBox, _("Pobrano i zainstalowano pomyślnie! GUI zostanie zrestartowane."), MessageBox.TYPE_INFO, timeout=5)
            print(f"[PiconUpdater] Zakończono instalację TAR.XZ: {archive_path}")
            self.restartGUI(auto_restart=True) # Wywołanie automatycznego restartu
            
        except tarfile.ReadError as e:
            print(f"[PiconUpdater] TarFile ReadError: {e}")
            self["status"].setText(_("Błąd pliku archiwum (niepoprawny format lub uszkodzony)! Sprawdź logi."))
            traceback.print_exc()
            self.session.open(MessageBox, _("Błąd pliku archiwum (niepoprawny format lub uszkodzony): ") + str(e), MessageBox.TYPE_ERROR)
        except Exception as e:
            print(f"[PiconUpdater] Install TAR.XZ Error: {e}")
            self["status"].setText(_("Błąd rozpakowywania lub instalacji TAR.XZ! Sprawdź logi."))
            traceback.print_exc()
            self.session.open(MessageBox, _("Błąd rozpakowywania lub instalacji TAR.XZ: ") + str(e), MessageBox.TYPE_ERROR)
        finally:
            self["status"].setText("")
            # Upewnij się, że pobrany plik archiwum jest zawsze usuwany
            if os.path.exists(archive_path):
                os.remove(archive_path)
                print(f"[PiconUpdater] Usunięto pobrany plik archiwum: {archive_path}")
            # Upewnij się, że tymczasowy katalog jest zawsze usuwany
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                print(f"[PiconUpdater] Usunięto tymczasowy katalog: {temp_extract_dir}")


    def download(self):
        """Rozpoczyna proces pobierania wybranego zestawu picon."""
        if self.selected_picon:
            url = self.selected_picon.get("url")
            if url:
                self["status"].setText(_("Pobieranie picon..."))
                # Użyj eTimer, aby opóźnić rozpoczęcie pobierania, co pozwala na odświeżenie GUI
                self.download_timer = eTimer()
                self.download_timer.callback.append(self._do_download)
                self.download_timer.start(100, True) # Uruchom jednorazowo po 100ms
            else:
                self.session.open(MessageBox, _("Brak URL do pobrania dla wybranego picona."), MessageBox.TYPE_ERROR)
        else:
            self.session.open(MessageBox, _("Proszę wybrać picon do pobrania."), MessageBox.TYPE_INFO)

    def _do_download(self):
        """Właściwa logika pobierania pliku picon (wykonywana z opóźnieniem przez timer)."""
        # Sprawdź, czy timer jest jeszcze aktywny (zapobiega wielokrotnym wywołaniom)
        if hasattr(self, 'download_timer') and self.download_timer is not None:
            self.download_timer = None # Wyłącz timer po wywołaniu
        
        if self.selected_picon:
            url = self.selected_picon.get("url")
            if url:
                # Użyj oryginalnej nazwy pliku z URL do zapisu w /tmp
                tmp_archive_path = "/tmp/" + os.path.basename(url)
                print(f"[PiconUpdater] Rozpoczynam pobieranie z: {url} do {tmp_archive_path}")
                try:
                    # Pobieranie pliku
                    r = requests.get(url, stream=True, timeout=300) # Timeout 300 sekund dla dużych plików
                    r.raise_for_status() # Zgłoś błąd dla nieudanych odpowiedzi HTTP
                    with open(tmp_archive_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"[PiconUpdater] Pobrano plik: {tmp_archive_path}")

                    # Wywołaj odpowiednią funkcję instalacji w zależności od rozszerzenia pliku
                    if tmp_archive_path.lower().endswith(".ipk"):
                        self.install_ipk(tmp_archive_path)
                    elif tmp_archive_path.lower().endswith(".tar.xz"):
                        self.install_tar_xz(tmp_archive_path)
                    else:
                        # Nieobsługiwany format pliku
                        self.session.open(MessageBox, _("Nieobsługiwany format pliku: ") + os.path.basename(url), MessageBox.TYPE_ERROR)
                        print(f"[PiconUpdater] Nieobsługiwany format pliku: {tmp_archive_path}")
                        if os.path.exists(tmp_archive_path):
                            os.remove(tmp_archive_path) # Usuń nieobsługiwany plik

                except requests.exceptions.RequestException as e:
                    # Obsługa błędów sieciowych podczas pobierania
                    print(f"[PiconUpdater] RequestError: {e}")
                    self["status"].setText(_("Błąd sieci podczas pobierania! Sprawdź połączenie."))
                    traceback.print_exc()
                    self.session.open(MessageBox, _("Błąd sieci podczas pobierania: ") + str(e), MessageBox.TYPE_ERROR)
                except Exception as e:
                    # Ogólna obsługa błędów podczas pobierania lub przekierowania do instalacji
                    print(f"[PiconUpdater] Download/Install Error: {e}")
                    self["status"].setText(_("Błąd pobierania lub instalacji! Sprawdź logi."))
                    traceback.print_exc()
                    self.session.open(MessageBox, _("Błąd pobierania lub instalacji: ") + str(e), MessageBox.TYPE_ERROR)
                finally:
                    # Status jest ustawiany w poszczególnych funkcjach instalacji.
                    # Tutaj tylko upewniamy się, że jest czysto, jeśli nie było przekierowania.
                    pass
        
    def changeLanguage(self):
        """Funkcja zmiany języka (obecnie niezaimplementowana)."""
        self.session.open(MessageBox, _("Funkcja zmiany języka niezaimplementowana."), MessageBox.TYPE_INFO)

    def restartGUI(self, auto_restart=False):
        """Restartuje interfejs graficzny Enigmy2."""
        if auto_restart:
            # Komunikat o automatycznym restarcie z timeoutem
            self.session.open(MessageBox, _("GUI zostanie zrestartowane..."), MessageBox.TYPE_INFO, timeout=3)
            # Opóźnienie restartu, aby MessageBox mógł się wyświetlić.
            if not hasattr(self, 'restart_timer') or self.restart_timer is None:
                self.restart_timer = eTimer()
            self.restart_timer.callback.append(lambda: self.console.execute("killall -9 enigma2"))
            self.restart_timer.start(3000, True) # Czekaj 3 sekundy (3000 ms) przed restartem
        else:
            # Ręczny restart wywołany przez użytkownika (np. przyciskiem "Blue")
            self.session.open(MessageBox, _("Restartowanie GUI..."), MessageBox.TYPE_INFO)
            self.console.execute("killall -9 enigma2")

    # Metody nawigacyjne dla MenuList
    def up(self):
        self["picon_list"].up()

    def down(self):
        self["picon_list"].down()

    def left(self):
        self["picon_list"].pageUp()

    def right(self):
        self["picon_list"].pageDown()

    def exit(self):
        """Zamyka ekran pluginu."""
        self.close()

def main(session, **kwargs):
    """Główna funkcja wywoływana po uruchomieniu pluginu z menu Enigmy2."""
    session.open(PiconUpdater)

def Plugins(**kwargs):
    """Definicja pluginu dla systemu Enigma2."""
    from Plugins.Plugin import PluginDescriptor
    return PluginDescriptor(
        name="Instalacja i aktualizacja Picon",
        description="Pobieranie i instalacja zestawów picon",
        where=PluginDescriptor.WHERE_PLUGINMENU, # Plugin będzie widoczny w menu "Wtyczki"
        icon=resolveFilename(SCOPE_PLUGINS, "Extensions/PiconUpdater/icon.png"), # Ścieżka do ikony pluginu
        fnc=main # Funkcja wywoływana po uruchomieniu pluginu
    )
