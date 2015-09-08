"""
Contains tests for pulp_win.plugins.importers.importer.
"""

import os
import unittest
from pulp_win.plugins import models

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
    '../../data'))

class TestModel(unittest.TestCase):
    def test_from_file_no_metadata(self):
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.Package.from_file(msi_path)
        self.assertTrue(isinstance(pkg, models.MSI))
        self.assertEquals(pkg.unit_key, {
            'ProductName': 'lorem-ipsum',
            'ProductVersion': '0.0.1',
            'checksum': '6fab18ef14a41010b1c865a948bbbdb41ce0779a4520acabb936d931410fac07',
            'checksumtype': 'sha256',
            })
        self.assertEquals(pkg.relative_path,
                'lorem-ipsum/0.0.1/6fab18ef14a41010b1c865a948bbbdb41ce0779a4520acabb936d931410fac07/lorem-ipsum-0.0.1.msi')

    def test_from_file_different_checksumtype(self):
        metadata = dict(checksumtype='sha1',
                checksum='e9c828cfeddb8768cbf37b95deb234b383d91e2f')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.Package.from_file(msi_path, metadata)
        self.assertTrue(isinstance(pkg, models.MSI))
        self.assertEquals(pkg.unit_key['ProductName'], 'lorem-ipsum')

    def test_from_file_no_file(self):
        self.assertRaises(models.InvalidPackageError,
                models.Package.from_file, '/missing-file')

    def test_from_file_bad_msi(self):
        self.assertRaises(models.InvalidPackageError,
                models.Package.from_file, __file__)
