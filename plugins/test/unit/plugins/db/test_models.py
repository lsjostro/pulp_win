"""
Contains tests for pulp_win.plugins.importers.importer.
"""

from __future__ import unicode_literals

import mock
import os
# Important to import testbase, since it mocks the server's config import snafu
from .... import testbase
from pulp_win.plugins.db import models

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '../../../data'))


class TestModel(testbase.TestCase):
    def test_from_file_no_metadata(self):
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.MSI.from_file(msi_path)
        self.assertTrue(isinstance(pkg, models.MSI))
        self.assertEquals(pkg.unit_key, {
            'name': 'lorem-ipsum',
            'version': '0.0.1',
            'checksum': '6fab18ef14a41010b1c865a948bbbdb41ce0779a4520acabb936d931410fac07',  # noqa
            'checksumtype': 'sha256',
            })

    def test_from_file_different_checksumtype(self):
        metadata = dict(checksumtype='sha1',
                        checksum='e9c828cfeddb8768cbf37b95deb234b383d91e2f')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.MSI.from_file(msi_path, metadata)
        self.assertTrue(isinstance(pkg, models.MSI))
        self.assertEquals(pkg.unit_key['name'], 'lorem-ipsum')

    def test_from_file_no_file(self):
        with self.assertRaises(ValueError) as cm:
            models.MSI.from_file('/missing-file')
        self.assertEquals(
            "[Errno 2] No such file or directory: u'/missing-file'",
            str(cm.exception))

    def test_from_file_bad_msi(self):
        with self.assertRaises(ValueError):
            models.MSI.from_file(__file__)

    def test_from_file_bad_msm__msi(self):
        metadata = dict(checksumtype='sha1',
                        checksum='e9c828cfeddb8768cbf37b95deb234b383d91e2f')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        with self.assertRaises(models.InvalidPackageError) as ctx:
            models.MSM.from_file(msi_path, metadata)
        self.assertEquals("Attempt to handle an MSI as an MSM",
                          str(ctx.exception))

    @classmethod
    def _make_msi_property(cls, **properties):
        l = [('Property', 'Value'), ('s72', 'l0')]
        l.extend(sorted(properties.items()))
        return '\n'.join('{}\t{}'.format(k, v) for (k, v) in l)

    @classmethod
    def _make_msi_table(cls, *tables):
        return '\n'.join(tables)

    @mock.patch("pulp_win.plugins.db.models.subprocess.Popen")
    def test_from_file_msi(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        msi_properties = self._make_msi_property(
            ProductName='lorem-ipsum',
            ProductVersion='0.0.1',
            Manufacturer='Cicero Enterprises',
            ProductCode='{0FE5FDB7-1DA6-44D2-8C17-10510D12D0EE}',
            UpgradeCode='{12345678-1234-1234-1234-111111111111}',
        )
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            (self._make_msi_table("ModuleSignature", "Property"), ""),
            (msi_properties, ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.MSI.from_file(msi_path, metadata)
        self.assertEquals("lorem-ipsum",
                          pkg.unit_key['name'])
        self.assertEquals("0.0.1",
                          pkg.unit_key['version'])
        self.assertEquals(
            [
                dict(guid='8E012345_0123_4567_0123_0123456789AB',
                     version='1.2.3.4', name='foobar'),
            ],
            pkg.ModuleSignature)

    @mock.patch("pulp_win.plugins.db.models.subprocess.Popen")
    def test_from_file_msi_no_module_signature(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        msi_properties = self._make_msi_property(
            ProductName='lorem-ipsum',
            ProductVersion='0.0.1',
            Manufacturer='Cicero Enterprises',
            ProductCode='{0FE5FDB7-1DA6-44D2-8C17-10510D12D0EE}',
            UpgradeCode='{12345678-1234-1234-1234-111111111111}',
        )
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            (self._make_msi_table("Property"), ""),
            (msi_properties, ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.MSI.from_file(msi_path, metadata)
        self.assertEquals("lorem-ipsum",
                          pkg.unit_key['name'])
        self.assertEquals("0.0.1",
                          pkg.unit_key['version'])
        self.assertEquals(
            [],
            pkg.ModuleSignature)

    @mock.patch("pulp_win.plugins.db.models.subprocess.Popen")
    def test_from_file_msm(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            ("ModuleSignature", ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.MSM.from_file(msi_path, metadata)
        self.assertEquals("foobar",
                          pkg.unit_key['name'])
        self.assertEquals("1.2.3.4",
                          pkg.unit_key['version'])
        self.assertEquals("8E012345_0123_4567_0123_0123456789AB",
                          pkg.guid)

    def test_render_primary_msi(self):
        pkg = models.MSI(name="burgundy", version="1.1.1984.0",
                         checksumtype="sha256", checksum="chksum",
                         size=42)
        pkg.filename = pkg.filename_from_unit_key(pkg.unit_key)
        xml_str = pkg.render_primary("sha256")
        self.assertEquals(
            '<package type="msi"><checksum pkgid="YES" type="sha256">chksum</checksum><name>burgundy</name><version>1.1.1984.0</version><size package="42" /><location href="burgundy-1.1.1984.0.msi" /></package>',  # noqa
            xml_str)

        # With ProductCode and UpgradeCode
        pkg = models.MSI(name="burgundy", version="1.1.1984.0",
                         checksumtype="sha256", checksum="chksum",
                         size=42,
                         ProductCode="prodcode",
                         UpgradeCode="upgrcode")
        pkg.filename = pkg.filename_from_unit_key(pkg.unit_key)
        xml_str = pkg.render_primary("sha256")
        self.assertEquals(
            '<package type="msi"><ProductCode>prodcode</ProductCode><UpgradeCode>upgrcode</UpgradeCode><checksum pkgid="YES" type="sha256">chksum</checksum><name>burgundy</name><version>1.1.1984.0</version><size package="42" /><location href="burgundy-1.1.1984.0.msi" /></package>',  # noqa
            xml_str)
