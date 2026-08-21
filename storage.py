# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import posixpath
import shutil
import tarfile
import tempfile

try:
    from .catalog import satellite_orbital
except ImportError:
    from catalog import satellite_orbital

FLASH_PICON = "/usr/share/enigma2/picon"


def _mount_points():
    points = []
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    points.append(parts[1].replace("\\040", " "))
    except Exception:
        pass
    return points


def storage_targets():
    out = [{"id": "flash", "label": "Flash /usr/share/enigma2/picon", "path": FLASH_PICON}]
    seen = set([FLASH_PICON])
    mounts = _mount_points()
    preferred = ["/media/hdd", "/media/usb", "/media/mmc", "/media/sd", "/media/cf"]
    candidates = preferred + [m for m in mounts if m.startswith("/media/")]
    for root in candidates:
        if root in seen:
            continue
        if not (os.path.isdir(root) and os.access(root, os.W_OK)):
            continue
        seen.add(root)
        ident = "ext:" + root
        label = "%s /picon" % (os.path.basename(root).upper() or root)
        out.append({"id": ident, "label": label, "path": os.path.join(root, "picon")})
    return out


def target_by_id(target_id):
    for item in storage_targets():
        if item["id"] == target_id:
            return item
    return storage_targets()[0]


def ensure_target(target):
    path = target["path"]
    if not os.path.isdir(path):
        os.makedirs(path)
    symlink_message = ""
    if target.get("id") != "flash":
        try:
            if os.path.islink("/picon"):
                current = os.path.realpath("/picon")
                if current != os.path.realpath(path):
                    os.unlink("/picon")
                    os.symlink(path, "/picon")
                    symlink_message = "/picon -> %s" % path
            elif not os.path.exists("/picon"):
                os.symlink(path, "/picon")
                symlink_message = "/picon -> %s" % path
            else:
                symlink_message = "/picon istnieje jako katalog; nie zmieniono"
        except Exception as e:
            symlink_message = "symlink pominięty: %s" % e
    return path, symlink_message


def free_space(path):
    try:
        probe = path
        while probe and not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        st = os.statvfs(probe or "/")
        return int(st.f_bavail * st.f_frsize)
    except Exception:
        return 0


def _copy_stream(src, dst, chunk=1024 * 256):
    parent = os.path.dirname(dst)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(dst, "wb") as f:
        while True:
            data = src.read(chunk)
            if not data:
                break
            f.write(data)


def _extract_data_tar_from_ar(ipk_path, tmp_dir):
    out_path = None
    with open(ipk_path, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise ValueError("Nieprawidłowy format IPK/ar")
        while True:
            header = f.read(60)
            if not header:
                break
            if len(header) != 60 or header[58:60] != b"`\n":
                raise ValueError("Uszkodzony nagłówek ar")
            raw_name = header[0:16].decode("utf-8", "ignore").strip()
            name = raw_name.rstrip("/")
            try:
                size = int(header[48:58].decode("ascii", "ignore").strip())
            except Exception:
                raise ValueError("Nieprawidłowy rozmiar elementu ar")
            if name.startswith("data.tar"):
                out_path = os.path.join(tmp_dir, os.path.basename(name))
                remaining = size
                with open(out_path, "wb") as out:
                    while remaining > 0:
                        data = f.read(min(1024 * 256, remaining))
                        if not data:
                            raise IOError("Nieoczekiwany koniec IPK")
                        out.write(data)
                        remaining -= len(data)
            else:
                f.seek(size, 1)
            if size % 2:
                f.seek(1, 1)
            if out_path:
                return out_path
    raise ValueError("Brak data.tar.* w IPK")


def _safe_archive_name(name):
    name = (name or "").replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    name = name.lstrip("/")
    norm = posixpath.normpath(name)
    if not norm or norm == "." or norm == ".." or norm.startswith("../"):
        return None
    return norm


def _picon_relative_path(member_name):
    """Map package paths to the selected picon directory without path traversal."""
    clean = _safe_archive_name(member_name)
    if not clean:
        return None
    parts = clean.split("/")
    # Official picons packages install below /picon. Keep their logos/ tree and aliases.
    if "picon" in parts:
        idx = parts.index("picon")
        rel_parts = parts[idx + 1:]
        if not rel_parts:
            return None
        rel = "/".join(rel_parts)
    else:
        # Older/custom sets are commonly a flat folder. Preserve only the PNG filename
        # to remain compatible with the previous PiconUpdater behaviour.
        rel = posixpath.basename(clean)
    rel = _safe_archive_name(rel)
    return rel


def _resolved_link_archive_name(member):
    link = (getattr(member, "linkname", "") or "").replace("\\", "/")
    if not link or link.startswith("/"):
        return None
    if member.issym():
        base = posixpath.dirname(_safe_archive_name(member.name) or "")
        candidate = posixpath.normpath(posixpath.join(base, link))
    else:  # hardlink target is stored relative to archive root
        candidate = posixpath.normpath(link)
    return _safe_archive_name(candidate)


def _replace_path(path):
    try:
        if os.path.lexists(path):
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
    except Exception:
        pass


def _srp_orbital_from_rel(rel):
    """Return Enigma2 orbital position (tenths of degree) from an SRP filename."""
    try:
        base = posixpath.basename(rel or "")
        if base.lower().endswith(".png"):
            base = base[:-4]
        parts = base.split("_")
        if len(parts) < 7:
            return None
        namespace = int(parts[6], 16)
        return int((namespace >> 16) & 0xFFFF)
    except Exception:
        return None


def _filtered_srp_members(tf, satellite):
    """Select only service-reference aliases belonging to one orbital position.

    Official picons packages contain a large shared logos/ tree plus aliases. When a
    concrete satellite is selected we deliberately do not install the shared logos/
    tree. Instead we dereference only matching aliases, which avoids installing
    thousands of unrelated files.
    """
    wanted = satellite_orbital(satellite)
    if wanted is None:
        return []
    out = []
    for member in tf.getmembers():
        rel = _picon_relative_path(member.name)
        if not rel or not rel.lower().endswith(".png"):
            continue
        if rel.lower().startswith("logos/"):
            continue
        if not (member.isfile() or member.issym() or member.islnk()):
            continue
        if _srp_orbital_from_rel(rel) == wanted:
            out.append((member, rel))
    return out


def _copy_member_dereferenced(tf, member, dst):
    """Copy a regular file or an internal tar link as a plain PNG."""
    try:
        src = tf.extractfile(member)
    except Exception:
        src = None
    if src is None:
        return False
    _replace_path(dst)
    try:
        _copy_stream(src, dst)
        return True
    finally:
        try:
            src.close()
        except Exception:
            pass


def _install_srp_satellite(tar_path, target_path, satellite, progress=None):
    count = 0
    with tarfile.open(tar_path, "r:*") as tf:
        members = _filtered_srp_members(tf, satellite)
        total = len(members)
        if total == 0:
            raise ValueError("Brak piconów SRP dla wybranego satelity: %s" % satellite)
        for idx, (member, rel) in enumerate(members):
            # SRP aliases are stored in picon root. Preserve relative path if upstream
            # ever nests them, but do not copy the shared logos/ directory.
            dst = os.path.join(target_path, *rel.split("/"))
            if _copy_member_dereferenced(tf, member, dst):
                count += 1
            if progress and (idx % 100 == 0):
                progress(idx + 1, total)
        if progress:
            progress(total, total)
    return count


def _estimate_srp_satellite(tar_path, satellite):
    total = 0
    with tarfile.open(tar_path, "r:*") as tf:
        members = _filtered_srp_members(tf, satellite)
        if not members:
            return 0
        by_name = {}
        for m in tf.getmembers():
            clean = _safe_archive_name(m.name)
            if clean:
                by_name[clean] = m
        for member, _rel in members:
            if member.isfile():
                total += int(member.size or 0)
                continue
            target_name = _resolved_link_archive_name(member)
            target_member = by_name.get(target_name or "")
            if target_member is not None:
                total += int(target_member.size or 0)
        # Direct copies need no logos/ tree and no filesystem link overhead.
        return int(total * 1.08) + (512 * 1024)


def _install_tar_members(tar_path, target_path, progress=None):
    """Install PNGs while preserving official picons symlink/hardlink layout.

    The upstream project deliberately builds a logos/ directory plus service-name/
    service-reference aliases. Flattening only regular PNG members loses those aliases,
    so links are recreated when possible and safely dereferenced as a fallback.
    """
    count = 0
    link_jobs = []
    with tarfile.open(tar_path, "r:*") as tf:
        members = []
        for m in tf.getmembers():
            rel = _picon_relative_path(m.name)
            if not rel or not rel.lower().endswith(".png"):
                continue
            if m.isfile() or m.issym() or m.islnk():
                members.append((m, rel))
        total = len(members)

        # Regular files first, so link targets normally already exist.
        for idx, (member, rel) in enumerate(members):
            if member.isfile():
                src = tf.extractfile(member)
                if src is not None:
                    dst = os.path.join(target_path, *rel.split("/"))
                    _replace_path(dst)
                    try:
                        _copy_stream(src, dst)
                        count += 1
                    finally:
                        try:
                            src.close()
                        except Exception:
                            pass
            else:
                link_jobs.append((member, rel))
            if progress and (idx % 250 == 0):
                progress(idx + 1, total)

        for member, rel in link_jobs:
            dst = os.path.join(target_path, *rel.split("/"))
            parent = os.path.dirname(dst)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            archive_target = _resolved_link_archive_name(member)
            target_rel = _picon_relative_path(archive_target) if archive_target else None
            linked = False
            if target_rel:
                target_dst = os.path.join(target_path, *target_rel.split("/"))
                _replace_path(dst)
                try:
                    if member.issym():
                        # Use a relative filesystem link so moving /picon to USB/HDD remains valid.
                        link_text = os.path.relpath(target_dst, parent or target_path)
                        os.symlink(link_text, dst)
                    else:
                        os.link(target_dst, dst)
                    linked = True
                    count += 1
                except Exception:
                    linked = False
            if not linked:
                # FAT-like external media may not support links. TarFile can resolve
                # internal links; copy their content instead of silently losing picons.
                try:
                    src = tf.extractfile(member)
                except Exception:
                    src = None
                if src is not None:
                    _replace_path(dst)
                    try:
                        _copy_stream(src, dst)
                        count += 1
                    finally:
                        try:
                            src.close()
                        except Exception:
                            pass

        if progress:
            progress(total, total)
    return count



def _filesystem_supports_links(path):
    """Probe link support without touching user picons."""
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
        src = os.path.join(path, ".piconupdater_linkprobe_src")
        dst = os.path.join(path, ".piconupdater_linkprobe_dst")
        with open(src, "wb") as f:
            f.write(b"x")
        try:
            os.symlink(os.path.basename(src), dst)
            return os.path.islink(dst)
        finally:
            try:
                os.unlink(dst)
            except Exception:
                pass
            try:
                os.unlink(src)
            except Exception:
                pass
    except Exception:
        return False


def _tar_required_bytes(tar_path, target_path):
    """Estimate final disk usage for PNG payload in the selected filesystem."""
    link_ok = _filesystem_supports_links(target_path)
    total = 0
    with tarfile.open(tar_path, "r:*") as tf:
        members = tf.getmembers()
        by_name = {}
        for m in members:
            clean = _safe_archive_name(m.name)
            if clean:
                by_name[clean] = m
        for member in members:
            rel = _picon_relative_path(member.name)
            if not rel or not rel.lower().endswith(".png"):
                continue
            if member.isfile():
                total += int(member.size or 0)
            elif (member.issym() or member.islnk()) and not link_ok:
                target_name = _resolved_link_archive_name(member)
                target_member = by_name.get(target_name or "")
                if target_member is not None and target_member.isfile():
                    total += int(target_member.size or 0)
    # Small safety margin for filesystem allocation/metadata.
    return int(total * 1.10) + (2 * 1024 * 1024)


def validate_package(package_path, item):
    """Validate archive structure before any existing picons are removed.

    Returns the number of installable PNG aliases/files visible for the requested
    mode. This deliberately does not touch the destination filesystem.
    """
    tmp_dir = tempfile.mkdtemp(prefix="piconupdater-validate-")
    try:
        fmt = (item.get("format") or "ipk").lower()
        satellite = (item.get("selected_satellite") or "*").lower()
        ptype = (item.get("type") or "").lower()
        if fmt == "ipk" or package_path.lower().endswith(".ipk"):
            tar_path = _extract_data_tar_from_ar(package_path, tmp_dir)
        elif fmt in ("tar.xz", "txz") or package_path.lower().endswith(".tar.xz"):
            tar_path = package_path
        else:
            raise ValueError("Nieobsługiwany format: %s" % fmt)
        with tarfile.open(tar_path, "r:*") as tf:
            if ptype == "srp" and satellite != "*":
                count = len(_filtered_srp_members(tf, satellite))
            else:
                count = 0
                for member in tf.getmembers():
                    rel = _picon_relative_path(member.name)
                    if rel and rel.lower().endswith(".png") and (member.isfile() or member.issym() or member.islnk()):
                        count += 1
            if count <= 0:
                if ptype == "srp" and satellite != "*":
                    raise ValueError("Brak piconów SRP dla wybranego satelity: %s" % satellite)
                raise ValueError("Paczka nie zawiera piconów PNG.")
            return count
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def estimate_install_bytes(package_path, item, target):
    target_path, _ = ensure_target(target)
    tmp_dir = tempfile.mkdtemp(prefix="piconupdater-estimate-")
    try:
        fmt = (item.get("format") or "ipk").lower()
        satellite = (item.get("selected_satellite") or "*").lower()
        ptype = (item.get("type") or "").lower()
        if fmt == "ipk" or package_path.lower().endswith(".ipk"):
            data_tar = _extract_data_tar_from_ar(package_path, tmp_dir)
            if ptype == "srp" and satellite != "*":
                return _estimate_srp_satellite(data_tar, satellite)
            return _tar_required_bytes(data_tar, target_path)
        if fmt in ("tar.xz", "txz") or package_path.lower().endswith(".tar.xz"):
            if ptype == "srp" and satellite != "*":
                return _estimate_srp_satellite(package_path, satellite)
            return _tar_required_bytes(package_path, target_path)
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def install_package(package_path, item, target, progress=None):
    target_path, symlink_message = ensure_target(target)
    tmp_dir = tempfile.mkdtemp(prefix="piconupdater-install-")
    try:
        fmt = (item.get("format") or "ipk").lower()
        satellite = (item.get("selected_satellite") or "*").lower()
        ptype = (item.get("type") or "").lower()
        if fmt == "ipk" or package_path.lower().endswith(".ipk"):
            data_tar = _extract_data_tar_from_ar(package_path, tmp_dir)
            if ptype == "srp" and satellite != "*":
                count = _install_srp_satellite(data_tar, target_path, satellite, progress=progress)
            else:
                count = _install_tar_members(data_tar, target_path, progress=progress)
        elif fmt in ("tar.xz", "txz") or package_path.lower().endswith(".tar.xz"):
            if ptype == "srp" and satellite != "*":
                count = _install_srp_satellite(package_path, target_path, satellite, progress=progress)
            else:
                count = _install_tar_members(package_path, target_path, progress=progress)
        else:
            raise ValueError("Nieobsługiwany format: %s" % fmt)
        try:
            marker = os.path.join(target_path, ".piconupdater_reload")
            with open(marker, "w") as f:
                f.write("reload\n")
        except Exception:
            pass
        return {"count": count, "path": target_path, "symlink": symlink_message, "satellite": satellite}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def clear_picons(target):
    path, _ = ensure_target(target)
    removed = 0
    if not os.path.isdir(path):
        return 0
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            full = os.path.join(root, name)
            if name.lower().endswith(".png") or (os.path.islink(full) and name.lower().endswith(".png")):
                try:
                    os.unlink(full)
                    removed += 1
                except Exception:
                    pass
        for name in dirs:
            full = os.path.join(root, name)
            try:
                if not os.listdir(full):
                    os.rmdir(full)
            except Exception:
                pass
    return removed
