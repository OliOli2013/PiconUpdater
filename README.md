# PiconUpdater 2.0.1 for Enigma2

**PiconUpdater** is a rebuilt Enigma2 picon browser, updater and installer by **Paweł Pawełek**. Version 2.0.1 continues the rebuilt architecture introduced in 2.0.0 and replaces the old static package list with a dynamic catalog built from current releases of `picons/picons` and keeps the custom AIO IPTV source.

## Main functions

- dynamic detection of current `picons/picons` releases;
- labels for **NEW**, **UPDATE**, **INSTALLED** and **LATEST** packages;
- filters for picon naming type (**SRP**, **UTF8 SNP**, legacy **SNP**, AIO IPTV), **concrete satellite**, package/scope, canvas size, logo area, dark/light logo and background;
- deterministic per-satellite SRP installation (for example 13.0E, 19.2E, 23.5E or 28.2E) by filtering Enigma2 service-reference namespaces inside the upstream package;
- currently published FULL packages and dedicated channel-list releases such as 13E/19E/23E/28E when available upstream;
- Flash / USB / HDD / other `/media` targets;
- update-safe installation: the new package is downloaded and validated first, then old picons in the selected location are removed before writing the replacement set;
- for a concrete SRP satellite, only matching service-reference picons are dereferenced and installed — the huge shared `logos/` tree and unrelated satellites are skipped;
- support for official picons `logos/` + symlink/hardlink structure when installing a whole package;
- `.ipk` and `.tar.xz` sources;
- GitHub catalog cache and offline fallback metadata;
- SHA256 verification when a GitHub release asset exposes a digest;
- project QR code and AIO-style footer/UI.

## Installation — command remains unchanged

```sh
wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh
```

The public command, package name `enigma2-plugin-extensions-piconupdater`, plugin directory `Extensions/PiconUpdater`, and repository path remain compatible with existing installers and other Enigma2 plugins.

## Controls

- **OK / Green** — install selected picon set
- **Yellow** — filters, concrete satellite and install location
- **Blue** — force refresh of the GitHub catalog
- **Menu** — tools, plugin update/reinstall, QR, cache and picon cleanup
- **INFO / 0** — project website QR code
- **Red / Exit** — close

Project website: https://olioli2013.github.io/aio-iptv-projekt/

Author: **Paweł Pawełek**
