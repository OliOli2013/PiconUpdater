# PiconUpdater — audit 1.2 → 2.0.0

## Findings in 1.2

1. The picon catalog was hard-coded in `picons.json`; release URLs became stale and there was no live discovery of upstream packages.
2. The update check covered the plugin version, not new picon releases or updates to an installed picon variant.
3. Picon metadata was too shallow to select naming method, resolution, logo padding, logo style, background and current upstream scope independently.
4. The manual IPK flow depended on the external `ar` command and extracted untrusted archives directly to temporary directories.
5. Self-update replaced the live plugin directory without a staging transaction or rollback.
6. Network work and large package operations could make the GUI less responsive.
7. The UI did not match the current AIO Panel / IPTV Dream family and had no project QR/footer integration.
8. `python3-requests` was a package dependency despite the task being achievable with the Python standard library.
9. Upstream picons packages use a logo store plus aliases (symlink/hardlink). A naïve installer that copies only regular PNG members can silently lose service-reference/name aliases.

## Remediation in 2.0.0

The new architecture separates catalog/network logic (`catalog.py`), storage/package installation (`storage.py`) and Enigma2 UI (`ui.py`). GitHub Releases are parsed at runtime and normalized into a variant key. Local state records installed variants and the newest release the user has already seen. Package installation preserves upstream aliases when supported, falls back to dereferenced copies when necessary, blocks archive path traversal, uses a pure-Python IPK/ar reader, and verifies SHA256 when available. The repository installer validates the downloaded ZIP, compiles Python source with built-in `compile()`, stages the new plugin next to the live directory, and can restore the previous directory if replacement fails.


## Addendum 2.0.1 — test na rzeczywistym tunerze

Po teście wersji 2.0.0 na Enigma2 ujawniono cztery problemy praktyczne, których nie dało się potwierdzić bez rzeczywistego GUI i istniejącego katalogu piconów:

1. Teksty na kolorowych klawiszach były zasłaniane przez belki `eLabel`; 2.0.1 wymusza kolejność warstw (`zPosition`) i biały tekst.
2. Podgląd pokazywał tylko tło. 2.0.1 zawiera gotowe przykładowe picony z logo dla obsługiwanych teł.
3. Zakres `13e.19e.23e.28e` nie pozwalał użytkownikowi wybrać jednej pozycji orbitalnej. 2.0.1 dodaje filtr konkretnego satelity.
4. Kontrola wolnego miejsca była wykonywana przy nadal obecnym starym zestawie. 2.0.1 najpierw pobiera i waliduje archiwum, następnie usuwa stare picony i dopiero wtedy ponownie sprawdza wolne miejsce oraz instaluje nowy zestaw.

Dla SRP filtr satelity jest wykonywany bez zgadywania: pozycja orbitalna jest odczytywana z pola namespace w nazwie service-reference (`..._<namespace>_...png`). Dzięki temu z dużej paczki upstream instalowane są tylko aliasy należące do wybranej pozycji, bez całego katalogu `logos/` i bez piconów pozostałych satelitów.
