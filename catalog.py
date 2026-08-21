# -*- coding: utf-8 -*-
from __future__ import print_function

import datetime
import json
import os
import re
import ssl
import hashlib
import tempfile

try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlparse
except ImportError:  # Python 2 fallback for a few older images
    from urllib2 import Request, urlopen
    from urlparse import urlparse

PLUGIN_VERSION = "2.0.1"
GITHUB_RELEASES_API = "https://api.github.com/repos/picons/picons/releases?per_page=20"
PLUGIN_VERSION_URL = "https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/version"
CACHE_FILE = "/etc/enigma2/piconupdater_catalog.json"
STATE_FILE = "/etc/enigma2/piconupdater_state.json"
CACHE_TTL = 3600  # 1 h; Blue button can force immediate refresh
USER_AGENT = "PiconUpdater/%s Enigma2" % PLUGIN_VERSION
ALLOWED_HOSTS = (
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)

ASSET_RE = re.compile(
    r"^enigma2-plugin-picons-(utf8snp|snp|srp)-(.+)\.(\d+x\d+)-(\d+x\d+)\.([^.]+)\.on\.([^.]+)_(\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2})_all\.ipk$",
    re.I,
)

SCOPE_LABELS = {
    "full": "FULL – wszystkie dostępne pozycje",
    "13e.19e.23e.28e": "13.0°E + 19.2°E + 23.5°E + 28.2°E",
    "ziggo": "Ziggo (kablowe)",
    "iptv-pl": "IPTV Polska",
}

TYPE_LABELS = {
    "srp": "SRP (Service Reference)",
    "utf8snp": "UTF8 SNP (nazwa kanału)",
    "snp": "SNP (legacy)",
    "aioiptv": "AIO IPTV",
}

# picons/picons uses shortened scope tokens in release asset names.
# The values below are the real orbital positions used by Enigma2 (tenths of a degree).
SATELLITE_LABELS = {
    "13e": "13.0°E – Hot Bird",
    "19e": "19.2°E – Astra 1",
    "23e": "23.5°E – Astra 3",
    "28e": "28.2°E – Astra 2",
    "16e": "16.0°E – Eutelsat 16A",
    "9e": "9.0°E – Eutelsat 9B",
    "7e": "7.0°E – Eutelsat 7",
    "5e": "5.0°E",
    "1w": "1.0°W",
    "5w": "5.0°W",
    "30w": "30.0°W – Hispasat",
}

SATELLITE_ORBITAL = {
    "13e": 130, "19e": 192, "23e": 235, "28e": 282,
    "16e": 160, "9e": 90, "7e": 70, "5e": 50,
    "1w": 3590, "5w": 3550, "30w": 3300,
}


def scope_satellites(scope):
    """Return concrete satellite tokens encoded in a picons release scope.

    FULL intentionally returns an empty list: it contains many orbital positions and
    can still be filtered at installation time when a satellite is selected from a
    concrete release available in the catalog.
    """
    scope = (scope or "").lower().strip()
    if not scope or scope in ("full", "iptv-pl", "ziggo"):
        return []
    parts = [x for x in scope.split(".") if x]
    out = []
    for part in parts:
        if re.match(r"^\d+(?:e|w)$", part):
            out.append(part)
    return out


def satellite_label(value):
    value = (value or "").lower()
    if not value:
        return "—"
    return SATELLITE_LABELS.get(value, value.upper())


def satellite_orbital(value):
    value = (value or "").lower()
    if value in SATELLITE_ORBITAL:
        return SATELLITE_ORBITAL[value]
    m = re.match(r"^(\d+)(e|w)$", value)
    if not m:
        return None
    deg = int(m.group(1)) * 10
    return deg if m.group(2) == "e" else (3600 - deg) % 3600


def item_supports_satellite(item, satellite):
    satellite = (satellite or "*").lower()
    if satellite == "*":
        return True
    if (item or {}).get("type") != "srp":
        # Satellite-safe filtering is deterministic for SRP because the namespace is
        # encoded in every service-reference filename. Name based SNP variants do not
        # carry orbital information and must not pretend to be satellite filtered.
        return False
    scope = ((item or {}).get("scope") or "").lower()
    if scope == "full":
        return True
    return satellite in scope_satellites(scope)


def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso(value):
    if not value:
        return datetime.datetime.min
    value = value.strip().replace("Z", "")
    try:
        return datetime.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return datetime.datetime.min


def _atomic_json_write(path, data):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    fd, tmp = tempfile.mkstemp(prefix=".piconupdater-", dir=parent or None)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def _safe_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and (
            host in ALLOWED_HOSTS or host.endswith(".githubusercontent.com")
        )
    except Exception:
        return False


def _open_https(url, timeout=15):
    if not _safe_url(url):
        raise ValueError("Blocked URL: %s" % url)
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json, application/json;q=0.9, */*;q=0.1",
    })
    try:
        return urlopen(req, timeout=timeout)
    except Exception as first_error:
        # Older Enigma2 images can ship an outdated CA bundle. Retry only HTTPS
        # to GitHub hosts with TLS verification disabled rather than disabling it globally.
        try:
            ctx = ssl._create_unverified_context()
            return urlopen(req, timeout=timeout, context=ctx)
        except TypeError:
            raise first_error


def fetch_text(url, timeout=12):
    response = _open_https(url, timeout=timeout)
    try:
        data = response.read()
    finally:
        try:
            response.close()
        except Exception:
            pass
    if not isinstance(data, str):
        data = data.decode("utf-8", "replace")
    return data


def fetch_json(url, timeout=15):
    return json.loads(fetch_text(url, timeout=timeout))


def parse_asset_name(name):
    m = ASSET_RE.match(name or "")
    if not m:
        return None
    ptype, scope, canvas, padded, logotype, background, stamp = m.groups()
    return {
        "type": ptype.lower(),
        "scope": scope.lower(),
        "canvas": canvas.lower(),
        "padded": padded.lower(),
        "logotype": logotype.lower(),
        "background": background.lower(),
        "stamp": stamp,
    }


def variant_key(item):
    fields = (
        item.get("source", "picons/picons"),
        item.get("type", ""),
        item.get("scope", ""),
        item.get("canvas", ""),
        item.get("padded", ""),
        item.get("logotype", ""),
        item.get("background", ""),
    )
    return "|".join([str(x).lower() for x in fields])


def normalize_item(item):
    out = dict(item)
    out["variant_key"] = variant_key(out)
    out.setdefault("format", "ipk")
    out.setdefault("source", "picons/picons")
    out.setdefault("published_at", "")
    out.setdefault("release_tag", "")
    out.setdefault("size", 0)
    out.setdefault("asset_id", 0)
    out.setdefault("digest", "")
    return out


def scope_label(scope):
    scope = (scope or "").lower()
    if scope in SCOPE_LABELS:
        return SCOPE_LABELS[scope]
    parts = scope.split(".")
    mapped = []
    orbital = {
        "13e": "13.0°E", "19e": "19.2°E", "23e": "23.5°E", "28e": "28.2°E",
        "30w": "30.0°W", "5w": "5.0°W", "9e": "9.0°E", "16e": "16.0°E",
    }
    for p in parts:
        mapped.append(orbital.get(p, p.upper()))
    return " + ".join(mapped) if mapped else "—"


def type_label(ptype):
    return TYPE_LABELS.get((ptype or "").lower(), (ptype or "—").upper())


def background_label(value):
    labels = {
        "transparent": "Transparent",
        "reflection": "Reflection",
        "blue": "Blue",
        "black": "Black",
        "white": "White",
        "grey": "Grey",
        "custom": "Custom",
    }
    return labels.get((value or "").lower(), (value or "—").title())


def logo_label(value):
    value = (value or "").lower()
    if value == "dark":
        return "Dark logo"
    if value == "light":
        return "Light logo"
    return value or "—"


def _custom_items(plugin_path):
    path = os.path.join(plugin_path, "custom_sources.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return [normalize_item(x) for x in data if isinstance(x, dict) and x.get("download_url")]
    except Exception:
        return []


def _fallback_items(plugin_path):
    path = os.path.join(plugin_path, "catalog_fallback.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return [normalize_item(x) for x in data if isinstance(x, dict) and x.get("download_url")]
    except Exception:
        return []


def _catalog_from_releases(releases):
    by_variant = {}
    for rel in releases or []:
        if not isinstance(rel, dict) or rel.get("draft"):
            continue
        rel_tag = str(rel.get("tag_name") or "")
        published = str(rel.get("published_at") or rel.get("created_at") or "")
        for asset in rel.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            parsed = parse_asset_name(name)
            if not parsed:
                continue
            url = str(asset.get("browser_download_url") or "")
            if not url or not _safe_url(url):
                continue
            item = {
                "name": name,
                "download_url": url,
                "source": "picons/picons",
                "format": "ipk",
                "release_tag": rel_tag,
                "published_at": published,
                "size": int(asset.get("size") or 0),
                "asset_id": int(asset.get("id") or 0),
                "digest": str(asset.get("digest") or ""),
            }
            item.update(parsed)
            item = normalize_item(item)
            key = item["variant_key"]
            old = by_variant.get(key)
            if old is None or _parse_iso(item["published_at"]) > _parse_iso(old.get("published_at")):
                by_variant[key] = item
    return list(by_variant.values())


def newest_published(items):
    best = ""
    for item in items or []:
        val = item.get("published_at", "")
        if _parse_iso(val) > _parse_iso(best):
            best = val
    return best


def save_cache(items, source="github"):
    _atomic_json_write(CACHE_FILE, {
        "schema": 2,
        "fetched_at": _now_iso(),
        "source": source,
        "items": items,
    })


def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        items = [normalize_item(x) for x in data.get("items", []) if isinstance(x, dict)]
        return data, items
    except Exception:
        return {}, []


def cache_is_fresh(meta):
    fetched = _parse_iso(meta.get("fetched_at", ""))
    if fetched == datetime.datetime.min:
        return False
    return (datetime.datetime.utcnow() - fetched).total_seconds() < CACHE_TTL


def get_catalog(plugin_path, force=False):
    """Return (items, status_dict). Network failure falls back to cache / bundled manifest."""
    meta, cached = load_cache()
    custom = _custom_items(plugin_path)
    if cached and cache_is_fresh(meta) and not force:
        return _merge_catalog(cached, custom), {
            "online": False,
            "cached": True,
            "message": "cache",
            "fetched_at": meta.get("fetched_at", ""),
        }

    try:
        releases = fetch_json(GITHUB_RELEASES_API, timeout=15)
        online_items = _catalog_from_releases(releases)
        if not online_items:
            raise ValueError("GitHub catalog is empty")
        merged_remote = _merge_catalog(online_items, [])
        save_cache(merged_remote, "github")
        return _merge_catalog(merged_remote, custom), {
            "online": True,
            "cached": False,
            "message": "github",
            "fetched_at": _now_iso(),
        }
    except Exception as e:
        if cached:
            return _merge_catalog(cached, custom), {
                "online": False,
                "cached": True,
                "message": "cache after error: %s" % e,
                "fetched_at": meta.get("fetched_at", ""),
            }
        fallback = _fallback_items(plugin_path)
        return _merge_catalog(fallback, custom), {
            "online": False,
            "cached": False,
            "message": "fallback: %s" % e,
            "fetched_at": "",
        }


def _merge_catalog(primary, extra):
    by_key = {}
    for item in list(primary or []) + list(extra or []):
        item = normalize_item(item)
        key = item["variant_key"]
        old = by_key.get(key)
        if old is None or _parse_iso(item.get("published_at")) >= _parse_iso(old.get("published_at")):
            by_key[key] = item
    items = list(by_key.values())
    items.sort(key=lambda x: (
        0 if x.get("source") == "picons/picons" else 1,
        x.get("type", ""), x.get("scope", ""), x.get("canvas", ""),
        x.get("logotype", ""), x.get("background", "")
    ))
    return items


def load_state():
    default = {
        "schema": 2,
        "seen_published_at": "",
        "installed": {},
        "last_location": "flash",
    }
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        default.update(data)
        if not isinstance(default.get("installed"), dict):
            default["installed"] = {}
        return default
    except Exception:
        return default


def save_state(state):
    state = dict(state or {})
    state["schema"] = 2
    _atomic_json_write(STATE_FILE, state)


def semver_tuple(value):
    nums = re.findall(r"\d+", value or "")
    nums = [int(x) for x in nums[:4]]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)


def remote_plugin_version():
    try:
        return fetch_text(PLUGIN_VERSION_URL, timeout=7).strip()
    except Exception:
        return ""


def item_flags(item, state, newest=""):
    flags = []
    key = item.get("variant_key") or variant_key(item)
    installed = (state or {}).get("installed", {}).get(key)
    if installed:
        if installed.get("name") == item.get("name"):
            flags.append("INSTALLED")
        elif _parse_iso(item.get("published_at")) > _parse_iso(installed.get("published_at")):
            flags.append("UPDATE")
    seen = (state or {}).get("seen_published_at", "")
    if item.get("source") == "picons/picons":
        if seen and _parse_iso(item.get("published_at")) > _parse_iso(seen):
            flags.append("NEW")
        elif not seen and item.get("published_at") == newest:
            flags.append("LATEST")
    return flags


def download_file(url, dest_path, progress=None, timeout=60, expected_digest=""):
    response = _open_https(url, timeout=timeout)
    hasher = hashlib.sha256()
    try:
        try:
            total = int(response.headers.get("Content-Length") or 0)
        except Exception:
            total = 0
        done = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                f.write(chunk)
                hasher.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        digest = (expected_digest or "").strip().lower()
        if digest.startswith("sha256:"):
            digest = digest.split(":", 1)[1]
        if digest and re.match(r"^[0-9a-f]{64}$", digest):
            actual = hasher.hexdigest().lower()
            if actual != digest:
                try:
                    os.unlink(dest_path)
                except Exception:
                    pass
                raise IOError("SHA256 mismatch: expected %s, got %s" % (digest, actual))
        return done
    finally:
        try:
            response.close()
        except Exception:
            pass
