# Picon Updater
Wtyczka (plugin) dla tunerów Enigma2 (Python 3) służąca do łatwego pobierania i instalowania zestawów picon (ikon kanałów).

Autor: **Paweł Pawełek** | msisystem@t.pl | Facebook: Enigma 2, Oprogramowanie i dodatki

![Zrzut ekranu wtyczki Picon Updater](https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/screenshot.png)

## 🚀 Główne Funkcje

* **Prosta instalacja:** Pobieranie i instalacja picon dla satelitów (np. Hotbird 13°E, Astra 19.2°E) oraz IPTV.
* **Wybór lokalizacji:** Możliwość instalacji picon w pamięci wewnętrznej (Flash) lub na nośniku zewnętrznym (USB/HDD).
* **Automatyczne symlinki:** Wtyczka sama tworzy i zarządza linkami symbolicznymi (symlink), gdy picony instalowane są na USB/HDD.
* **Automatyczne aktualizacje:** Wtyczka sama sprawdza dostępność nowej wersji przy starcie i proponuje aktualizację.
* **Podgląd (Preview):** Możliwość podejrzenia wybranego zestawu picon przed instalacją.
* **Inteligentne czyszczenie:** Wtyczka automatycznie usuwa stare picony przed wgraniem nowego zestawu, aby uniknąć bałaganu.
* **Wsparcie formatów:** Obsługa instalacji picon zarówno z pakietów `.ipk`, jak i archiwów `.tar.xz`.

## 🛠️ Instalacja

Wtyczka przeznaczona jest dla obrazów Enigma2 opartych na **Python 3** (np. OpenATV 7.x, OpenPLi 9.x i nowsze).

Aby zainstalować wtyczkę, połącz się ze swoim tunerem przez terminal (Telnet lub SSH) i wklej poniższą komendę:

```bash
wget -qO - [https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh](https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh) | /bin/sh
