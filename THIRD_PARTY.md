# Third-party sources

PiconUpdater does not redistribute the upstream `picons/picons` logo collection inside the plugin package. It discovers downloadable picon packages from the public GitHub Releases API and installs the package selected by the user.

Upstream project: `picons/picons` — https://github.com/picons/picons

The bundled `catalog_fallback.json` contains metadata and release URLs only, so the catalog remains usable if the GitHub Releases API is temporarily unavailable. Users should review the upstream project's license and terms for the downloaded picon assets.
