# -*- coding: utf-8 -*-
import io
import os
import shutil
import sys
import tarfile
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import catalog
import storage


def _ar_header(name, size):
    import time
    return ('%-16s%-12d%-6d%-6d%-8o%-10d`\n' % (name+'/', int(time.time()), 0, 0, 0o100644, size)).encode('ascii')


def build_test_ipk(path):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as tf:
        content = b'PNGDATA'
        info = tarfile.TarInfo('picon/logos/testlogo.png')
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
        sym = tarfile.TarInfo('picon/1_0_1_TEST.png')
        sym.type = tarfile.SYMTYPE
        sym.linkname = 'logos/testlogo.png'
        tf.addfile(sym)
        hard = tarfile.TarInfo('picon/1_0_1_HARD.png')
        hard.type = tarfile.LNKTYPE
        hard.linkname = 'picon/logos/testlogo.png'
        tf.addfile(hard)
        # Traversal-looking PNG must not be installed.
        evil = tarfile.TarInfo('../../evil.png')
        evil.size = len(content)
        tf.addfile(evil, io.BytesIO(content))
    data_bytes = data.getvalue()
    control = io.BytesIO()
    with tarfile.open(fileobj=control, mode='w:gz'):
        pass
    members = [('debian-binary', b'2.0\n'), ('control.tar.gz', control.getvalue()), ('data.tar.gz', data_bytes)]
    with open(path, 'wb') as f:
        f.write(b'!<arch>\n')
        for name, payload in members:
            f.write(_ar_header(name, len(payload)))
            f.write(payload)
            if len(payload) % 2:
                f.write(b'\n')


def build_satellite_test_ipk(path):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as tf:
        for logo_name, payload in [('hotbird', b'HOTBIRD'), ('astra', b'ASTRA')]:
            info = tarfile.TarInfo('picon/logos/%s.png' % logo_name)
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
        # 0x82 == 130 -> 13.0E ; 0xC0 == 192 -> 19.2E
        for ref, target in [
            ('1_0_1_100_200_300_820000_0_0_0.png', 'logos/hotbird.png'),
            ('1_0_1_101_201_301_C00000_0_0_0.png', 'logos/astra.png'),
        ]:
            sym = tarfile.TarInfo('picon/' + ref)
            sym.type = tarfile.SYMTYPE
            sym.linkname = target
            tf.addfile(sym)
    data_bytes = data.getvalue()
    control = io.BytesIO()
    with tarfile.open(fileobj=control, mode='w:gz'):
        pass
    members = [('debian-binary', b'2.0\n'), ('control.tar.gz', control.getvalue()), ('data.tar.gz', data_bytes)]
    with open(path, 'wb') as f:
        f.write(b'!<arch>\n')
        for name, payload in members:
            f.write(_ar_header(name, len(payload)))
            f.write(payload)
            if len(payload) % 2:
                f.write(b'\n')


class CatalogTests(unittest.TestCase):
    def test_parse_current_asset(self):
        name = 'enigma2-plugin-picons-srp-full.220x132-190x102.dark.on.transparent_2026-08-14--12-51-19_all.ipk'
        parsed = catalog.parse_asset_name(name)
        self.assertEqual(parsed['type'], 'srp')
        self.assertEqual(parsed['scope'], 'full')
        self.assertEqual(parsed['canvas'], '220x132')
        self.assertEqual(parsed['padded'], '190x102')
        self.assertEqual(parsed['logotype'], 'dark')
        self.assertEqual(parsed['background'], 'transparent')

    def test_variant_update_flags(self):
        item = catalog.normalize_item({
            'source':'picons/picons', 'type':'srp', 'scope':'full', 'canvas':'100x60',
            'padded':'86x46', 'logotype':'dark', 'background':'transparent',
            'name':'new.ipk', 'published_at':'2026-08-16T00:00:00Z'
        })
        state = {'seen_published_at':'2026-08-01T00:00:00Z', 'installed':{
            item['variant_key']:{'name':'old.ipk','published_at':'2026-08-01T00:00:00Z'}
        }}
        flags = catalog.item_flags(item, state, item['published_at'])
        self.assertIn('UPDATE', flags)
        self.assertIn('NEW', flags)

    def test_satellite_scope_helpers(self):
        self.assertEqual(catalog.scope_satellites('13e.19e.23e.28e'), ['13e', '19e', '23e', '28e'])
        self.assertEqual(catalog.satellite_orbital('13e'), 130)
        self.assertEqual(catalog.satellite_orbital('19e'), 192)
        item = {'type':'srp', 'scope':'13e.19e.23e.28e'}
        self.assertTrue(catalog.item_supports_satellite(item, '13e'))
        self.assertFalse(catalog.item_supports_satellite({'type':'snp','scope':'13e.19e.23e.28e'}, '13e'))

    def test_fallback_manifest(self):
        items = catalog._fallback_items(ROOT)
        self.assertGreaterEqual(len(items), 12)
        self.assertTrue(any(x['scope'] == '13e.19e.23e.28e' for x in items))
        self.assertTrue(any(x['type'] == 'utf8snp' for x in items))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='piconupdater-test-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ipk_symlink_and_hardlink_install(self):
        ipk = os.path.join(self.tmp, 'test.ipk')
        target_path = os.path.join(self.tmp, 'target')
        build_test_ipk(ipk)
        target = {'id':'flash', 'label':'test', 'path':target_path}
        estimate = storage.estimate_install_bytes(ipk, {'format':'ipk'}, target)
        self.assertGreater(estimate, 0)
        result = storage.install_package(ipk, {'format':'ipk'}, target)
        self.assertGreaterEqual(result['count'], 3)
        logo = os.path.join(target_path, 'logos', 'testlogo.png')
        srp = os.path.join(target_path, '1_0_1_TEST.png')
        hard = os.path.join(target_path, '1_0_1_HARD.png')
        self.assertTrue(os.path.isfile(logo))
        self.assertTrue(os.path.exists(srp))
        self.assertTrue(os.path.exists(hard))
        with open(srp, 'rb') as f:
            self.assertEqual(f.read(), b'PNGDATA')
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'evil.png')))

    def test_srp_satellite_filter_installs_only_selected_orbit(self):
        ipk = os.path.join(self.tmp, 'sat.ipk')
        target_path = os.path.join(self.tmp, 'target')
        build_satellite_test_ipk(ipk)
        target = {'id':'flash', 'label':'test', 'path':target_path}
        item = {'format':'ipk', 'type':'srp', 'selected_satellite':'13e'}
        estimate = storage.estimate_install_bytes(ipk, item, target)
        self.assertGreater(estimate, 0)
        result = storage.install_package(ipk, item, target)
        self.assertEqual(result['count'], 1)
        self.assertTrue(os.path.isfile(os.path.join(target_path, '1_0_1_100_200_300_820000_0_0_0.png')))
        self.assertFalse(os.path.exists(os.path.join(target_path, '1_0_1_101_201_301_C00000_0_0_0.png')))
        self.assertFalse(os.path.exists(os.path.join(target_path, 'logos')))
        with open(os.path.join(target_path, '1_0_1_100_200_300_820000_0_0_0.png'), 'rb') as f:
            self.assertEqual(f.read(), b'HOTBIRD')

    def test_clear_recursive(self):
        target_path = os.path.join(self.tmp, 'target')
        os.makedirs(os.path.join(target_path, 'logos'))
        for p in (os.path.join(target_path,'a.png'), os.path.join(target_path,'logos','b.png')):
            with open(p,'wb') as f: f.write(b'x')
        target = {'id':'flash','label':'test','path':target_path}
        self.assertEqual(storage.clear_picons(target), 2)


if __name__ == '__main__':
    unittest.main()
