"""
Contains tests for pulp_win.plugins.importers.importer.
"""
from gettext import gettext as _
import hashlib
import os
import shutil
import tempfile
import unittest
import uuid

import mock

from pulp_win.common import ids
from pulp_win.plugins import models
from pulp_win.plugins.importers import importer


class TestEntryPoint(unittest.TestCase):
    """
    Tests for the entry_point() function.
    """
    def test_return_value(self):
        """
        Assert the correct return value for the entry_point() function.
        """
        return_value = importer.entry_point()

        expected_value = (importer.WinImporter, {})
        self.assertEqual(return_value, expected_value)


class TestWinImporter(unittest.TestCase):
    """
    This class contains tests for the WinImporter class.
    """
    def setUp(self):
        super(TestWinImporter, self).setUp()
        self.work_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        return super(TestWinImporter, self).tearDown()

    def test_import_units_units_none(self):
        """
        Assert correct behavior when units == None.
        """
        win_importer = importer.WinImporter()
        import_conduit = mock.MagicMock()
        units = ['unit_a', 'unit_b', 'unit_3']
        import_conduit.get_source_units.return_value = units

        imported_units = win_importer.import_units(mock.MagicMock(), mock.MagicMock(),
                                                      import_conduit, mock.MagicMock(), units=None)

        # Assert that the correct criteria was used
        self.assertEqual(import_conduit.get_source_units.mock_calls[0][2], {})
        import_conduit.get_source_units.assert_called_once_with()
        # Assert that the units were associated correctly
        associate_unit_call_args = [c[1] for c in import_conduit.associate_unit.mock_calls]
        self.assertEqual(associate_unit_call_args, [(u,) for u in units])
        # Assert that the units were returned
        self.assertEqual(imported_units, units)

    def test_import_units_units_not_none(self):
        """
        Assert correct behavior when units != None.
        """
        win_importer = importer.WinImporter()
        import_conduit = mock.MagicMock()
        units = ['unit_a', 'unit_b', 'unit_3']

        imported_units = win_importer.import_units(mock.MagicMock(), mock.MagicMock(),
                                                      import_conduit, mock.MagicMock(), units=units)

        # Assert that no criteria was used
        self.assertEqual(import_conduit.get_source_units.call_count, 0)
        # Assert that the units were associated correctly
        associate_unit_call_args = [c[1] for c in import_conduit.associate_unit.mock_calls]
        self.assertEqual(associate_unit_call_args, [(u,) for u in units])
        # Assert that the units were returned
        self.assertEqual(imported_units, units)

    def test_metadata(self):
        """
        Test the metadata class method's return value.
        """
        metadata = importer.WinImporter.metadata()

        expected_value = {
            'id': ids.TYPE_ID_IMPORTER_WIN, 'display_name': _('Windows importer'),
            'types': [ids.TYPE_ID_EXE, ids.TYPE_ID_MSI], }
        self.assertEqual(metadata, expected_value)

    @mock.patch('pulp_win.plugins.importers.importer.verification.verify_checksum')
    @mock.patch('pulp_win.plugins.models.Package.from_file')
    @mock.patch('pulp_win.plugins.models.Package.init_unit', autospec=True)
    @mock.patch('pulp_win.plugins.models.Package.move_unit', autospec=True)
    @mock.patch('pulp_win.plugins.models.Package.save_unit', autospec=True)
    @mock.patch('shutil.move')
    def test_upload_unit(self, move, save_unit, move_unit, init_unit, from_file,
            verify_checksum):
        """
        Assert correct operation of upload_unit().
        """
        msi_file = os.path.join(self.work_dir, 'foo.msi')
        data = str(uuid.uuid4())
        file(msi_file, "wb").write(data)

        unit_key = dict()
        metadata = dict(
                checksumtype = "sha1",
                checksum=hashlib.sha1(data).hexdigest())
        package = models.MSI(unit_key, metadata)
        from_file.return_value = package
        storage_path = '/some/path/name-version.msi'

        def init_unit_side_effect(self, conduit):
            class Unit(object):
                def __init__(self, *args, **kwargs):
                    self.storage_path = storage_path
            self._unit = Unit()
        init_unit.side_effect = init_unit_side_effect

        win_importer = importer.WinImporter()
        repo = mock.MagicMock()
        type_id = ids.TYPE_ID_MSI
        conduit = mock.MagicMock()
        config = {}

        report = win_importer.upload_unit(repo, type_id, unit_key, metadata,
                msi_file, conduit, config)

        self.assertEqual(report, {'success_flag': True, 'summary': {}, 'details': {}})
        from_file.assert_called_once_with(msi_file, metadata)
        init_unit.assert_called_once_with(package, conduit)
        move_unit.assert_called_once_with(package, msi_file)
        save_unit.assert_called_once_with(package, conduit)

    def test_validate_config(self):
        """
        There is no config, so we'll just assert that validation passes.
        """
        win_importer = importer.WinImporter()
        return_value = win_importer.validate_config(mock.MagicMock(), {})

        self.assertEqual(return_value, (True, None))
