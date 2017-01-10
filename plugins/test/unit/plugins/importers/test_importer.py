"""
Contains tests for pulp_win.plugins.importers.importer.
"""
from gettext import gettext as _
import json
import os

import mock

from pulp_win.common import ids
from .... import testbase
from pulp_win.plugins.db import models
from pulp_win.plugins.importers import importer


class TestEntryPoint(testbase.TestCase):
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
        self.assertEquals({
            models.MSI.TYPE_ID: models.MSI,
            models.MSM.TYPE_ID: models.MSM,
        }, importer.WinImporter.Type_Class_Map)


class ModelMixIn(object):
    def test__compute_checksum(self):
        file_path, checksum = self.new_file()
        self.assertEquals(
            checksum,
            self.__class__.Model._compute_checksum(open(file_path)))

    def test_filename_from_unit_key(self):
        unit_key = dict(name="aaa", version="1", extra="bbb")
        self.assertEquals(
            "aaa-1.%s" % self.__class__.Model.TYPE_ID,
            self.__class__.Model.filename_from_unit_key(unit_key))

    def test_unit_keys(self):
        type_file = os.path.join(os.path.dirname(__file__),
                                 '..', '..', '..', '..',
                                 'types', 'win.json')
        contents = json.load(open(type_file))
        types = dict((x['id'], x) for x in contents['types'])
        tlist = types[self.__class__.Model.TYPE_ID]['unit_key']
        self.assertEquals(
            sorted(self.__class__.Model.unit_key_fields),
            sorted(tlist))

    def test_ids(self):
        self.assertEquals(self.UNIT_KEY_FIELDS,
                          self.__class__.Model.unit_key_fields)


class TestModel_MSI(ModelMixIn, testbase.TestCase):
    Model = models.MSI
    Sample_Unit = dict()
    UNIT_KEY_FIELDS = ids.UNIT_KEY_MSI


class TestModel_MSM(ModelMixIn, testbase.TestCase):
    Model = models.MSM
    Sample_Unit = dict()
    UNIT_KEY_FIELDS = ids.UNIT_KEY_MSM


class TestWinImporter(testbase.TestCase):
    """
    This class contains tests for the WinImporter class.
    """
    @mock.patch("pulp_win.plugins.importers.importer.platform_models")
    @mock.patch("pulp_win.plugins.db.models.repo_controller")
    def test_import_units_units_none(self, _repo_controller, _platform_models):
        """
        Assert correct behavior when units == None.
        """
        src_repo = mock.MagicMock()
        dst_repo = mock.MagicMock()
        _platform_models.Repository.objects.get.side_effect = [src_repo,
                                                               dst_repo]
        units = [
            models.MSI(name="unit_a", version="1"),
            models.MSI(name="unit_b", version="1"),
            models.MSI(name="unit_3", version="1"),
        ]

        _repo_controller.find_repo_content_units.return_value = units

        pulpimp = importer.WinImporter()
        import_conduit = mock.MagicMock()

        imported_units = pulpimp.import_units(mock.MagicMock(),
                                              mock.MagicMock(),
                                              import_conduit,
                                              mock.MagicMock(),
                                              units=None)

        # Assert that the correct criteria was used
        _repo_controller.find_repo_content_units.assert_called_once_with(
            src_repo, yield_content_unit=True)
        # Assert that the units were associated correctly
        _u = sorted(units)
        self.assertEquals(
            [
                mock.call(repository=dst_repo, unit=_u[0]),
                mock.call(repository=dst_repo, unit=_u[1]),
                mock.call(repository=dst_repo, unit=_u[2]),
            ],
            _repo_controller.associate_single_unit.call_args_list)
        self.assertEqual(imported_units, sorted(units))

    @mock.patch("pulp_win.plugins.importers.importer.platform_models")
    @mock.patch("pulp_win.plugins.db.models.repo_controller")
    def test_import_units_units_not_none(self, _repo_controller,
                                         _platform_models):
        """
        Assert correct behavior when units != None.
        """
        src_repo = mock.MagicMock()
        dst_repo = mock.MagicMock()
        _platform_models.Repository.objects.get.side_effect = [src_repo,
                                                               dst_repo]
        pulpimp = importer.WinImporter()
        import_conduit = mock.MagicMock()
        units = [
            models.MSI(name="unit_a", version="1"),
            models.MSI(name="unit_b", version="1"),
            models.MSI(name="unit_3", version="1"),
        ]

        imported_units = pulpimp.import_units(mock.MagicMock(),
                                              mock.MagicMock(),
                                              import_conduit,
                                              mock.MagicMock(),
                                              units=units)

        # Assert that no criteria was used
        self.assertEqual(
            0, _repo_controller.find_repo_content_units.call_count)
        # Assert that the units were associated correctly
        _u = sorted(units)
        self.assertEquals(
            [
                mock.call(repository=dst_repo, unit=_u[0]),
                mock.call(repository=dst_repo, unit=_u[1]),
                mock.call(repository=dst_repo, unit=_u[2]),
            ],
            _repo_controller.associate_single_unit.call_args_list)
        # Assert that the units were returned
        self.assertEqual(imported_units, sorted(units))

    def test_metadata(self):
        """
        Test the metadata class method's return value.
        """
        metadata = importer.WinImporter.metadata()

        expected_value = {
            'id': ids.TYPE_ID_IMPORTER_WIN,
            'display_name': _('Windows importer'),
            'types': [ids.TYPE_ID_MSI, ids.TYPE_ID_MSM], }
        self.assertEqual(metadata, expected_value)

    @mock.patch("pulp_win.plugins.db.models.repo_controller")
    @mock.patch('pulp_win.plugins.db.models.MSI._get_db')
    @mock.patch('pulp_win.plugins.db.models.MSI.from_file')
    @mock.patch("pulp_win.plugins.importers.importer.plugin_api")
    def test_upload_unit_msi(self, _plugin_api, from_file,
                             _get_db, _repo_controller):
        """
        Assert correct operation of upload_unit().
        """
        _plugin_api.get_unit_model_by_id.return_value = models.MSI
        file_path, checksum = self.new_file("foo.msi")
        msi_file, checksum = self.new_file('foo.msi')

        unit_key = dict()
        metadata = dict(
            name="foo", version="1.1",
            Manufacturer="ACME Inc.",
            ProductCode="aaa",
            UpgradeCode="bbb",
            filename=os.path.basename(file_path),
            checksumtype="sha256",
            checksum=checksum)
        package = models.MSI(**metadata)
        from_file.return_value = package

        pulpimp = importer.WinImporter()
        repo = mock.MagicMock()
        type_id = ids.TYPE_ID_MSI
        conduit = mock.MagicMock()
        config = {}
        models.MSI.attach_signals()

        report = pulpimp.upload_unit(repo, type_id, unit_key, metadata,
                                     msi_file, conduit, config)

        from_file.assert_called_once_with(file_path, metadata)

        obj_id = _get_db.return_value.__getitem__.return_value.save.return_value.decode.return_value  # noqa

        metadata.update(
            id=obj_id,
            ModuleSignature=[],
            downloaded=True,
            pulp_user_metadata=dict(),
            relativepath=None,
            size=None,
        )
        unit_key = dict((x, metadata[x])
                        for x in models.MSI.unit_key_fields)

        self.assertEqual(report,
                         {'success_flag': True,
                          'details': dict(
                              unit=dict(unit_key=unit_key, metadata=metadata)
                          ),
                          'summary': ''})

    @mock.patch("pulp_win.plugins.db.models.repo_controller")
    @mock.patch('pulp_win.plugins.db.models.MSM._get_db')
    @mock.patch('pulp_win.plugins.db.models.MSM.from_file')
    @mock.patch("pulp_win.plugins.importers.importer.plugin_api")
    def test_upload_unit_msm(self, _plugin_api, from_file,
                             _get_db, _repo_controller):
        """
        Assert correct operation of upload_unit().
        """
        _plugin_api.get_unit_model_by_id.return_value = models.MSM
        file_path, checksum = self.new_file("foo.msm")
        msi_file, checksum = self.new_file('foo.msm')

        unit_key = dict()
        metadata = dict(
            name="foo", version="1.1",
            guid="aaa",
            filename=os.path.basename(file_path),
            checksumtype="sha256",
            checksum=checksum)
        package = models.MSM(**metadata)
        from_file.return_value = package

        pulpimp = importer.WinImporter()
        repo = mock.MagicMock()
        type_id = ids.TYPE_ID_MSM
        conduit = mock.MagicMock()
        config = {}
        models.MSM.attach_signals()

        report = pulpimp.upload_unit(repo, type_id, unit_key, metadata,
                                     msi_file, conduit, config)

        from_file.assert_called_once_with(file_path, metadata)

        obj_id = _get_db.return_value.__getitem__.return_value.save.return_value.decode.return_value  # noqa

        metadata.update(
            id=obj_id,
            downloaded=True,
            pulp_user_metadata=dict(),
            relativepath=None,
            size=None,
        )
        unit_key = dict((x, metadata[x])
                        for x in models.MSM.unit_key_fields)

        self.assertEqual(report,
                         {'success_flag': True,
                          'details': dict(
                              unit=dict(unit_key=unit_key, metadata=metadata)
                          ),
                          'summary': ''})

    def test_validate_config(self):
        """
        There is no config, so we'll just assert that validation passes.
        """
        pulpimp = importer.WinImporter()
        return_value = pulpimp.validate_config(mock.MagicMock(), {})

        self.assertEqual(return_value, (True, None))

    @mock.patch("pulp_win.plugins.importers.importer.sync.RepoSync")
    def test_sync(self, _RepoSync):
        # Basic test to make sure we're passing information correctly into
        # RepoSync, which itself is tested in test_sync
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        cfg = mock.MagicMock()

        pulpimp = importer.WinImporter()
        pulpimp.sync_repo(repo, conduit, cfg)

        self.assertEquals(pulpimp._current_sync,
                          _RepoSync.return_value)
        _RepoSync.assert_called_once_with(
            repo.repo_obj, conduit, cfg)
        self.assertEquals(repo.repo_obj, conduit.repo)
