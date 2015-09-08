import os
import shutil
import sys
import tempfile
import unittest
import uuid
from types import ModuleType

import mock

from pulp.plugins.model import Unit

from pulp_win.common import ids, constants

class ImporterWrapper(ModuleType):
    def __init__(self, name):
        self.__path__ = '/fake-path/' + name.replace('.', '/') + ".py"

    def __getattr__(self, name):
        if name != 'config':
            raise AttributeError(name)
        return self

class BaseTest(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        super(BaseTest, self).setUp()
        import pulp.server
        sys.modules['pulp.server.config'] = cfg = ImporterWrapper('pulp.server.config')
        pulp.server.config = cfg
        from pulp_win.plugins.distributors import distributor
        self.Module = distributor
        self.publish_dir = os.path.join(self.work_dir, "publish_dir")
        distributor.HTTP_PUBLISH_DIR = self.publish_dir

    def tearDown(self):
        shutil.rmtree(self.work_dir)
        import pulp.server
        del pulp.server.config
        del sys.modules['pulp.server.config']

class TestEntryPoint(BaseTest):
    """
    Tests for the entry_point() function.
    """
    def test_entry_point(self):
        """
        Assert the correct return value for the entry_point() function.
        """
        return_value = self.Module.entry_point()

        expected_value = (self.Module.WinDistributor, {})
        self.assertEqual(return_value, expected_value)

class TestConfiguration(BaseTest):
    def test_validate_config_empty(self):
        repo = object()
        conduit = object()
        config = {}
        distributor = self.Module.WinDistributor()
        self.assertEquals(distributor.validate_config(repo, config, conduit),
                (False, 'At least one of "serve-http" or "serve-https" must be specified'))

    def test_validate_config(self):
        repo = object()
        conduit = object()
        config = dict(http="a")
        distributor = self.Module.WinDistributor()
        self.assertEquals(distributor.validate_config(repo, config, conduit),
                (True, None))

class TestPublishRepo(BaseTest):
    def test_publish_repo(self):
        # Set up some files
        storage_dir = os.path.join(self.work_dir, 'storage_dir')
        os.makedirs(storage_dir)
        units = [
            Unit(ids.TYPE_ID_MSI,
                unit_key=dict(ProductName='burgundy',
                    ProductVersion='0.1938.0',
                    checksum='abcde', checksum_type='sha3.14'),
                metadata={},
                storage_path=os.path.join(storage_dir, str(uuid.uuid4()))),
            Unit(ids.TYPE_ID_MSI,
                unit_key=dict(ProductName='chablis',
                    ProductVersion='0.2013.0',
                    checksum='yz', checksum_type='sha3.14'),
                metadata={},
                storage_path=os.path.join(storage_dir, str(uuid.uuid4()))),
                ]
        for unit in units:
            file(unit.storage_path, "wb").write(str(uuid.uuid4()))

        distributor = self.Module.WinDistributor()
        repo = mock.Mock()
        repo.configure_mock(working_dir=os.path.join(self.work_dir, 'work_dir'),
                id=str(uuid.uuid4()))
        conduit = mock.MagicMock()
        conduit.get_units.return_value = units
        distributor.publish_repo(repo, conduit, config=dict(http="a"))
        self.assertEquals(
            [ x[0][0] for x in conduit.build_success_report.call_args_list ],
            [{'publish_modules': 'FINISHED'}])
        self.assertEquals(
            [ x[0][1][0]['num_processed'] for x in conduit.build_success_report.call_args_list ],
            [2])
        # Make sure symlinks got created
        for unit in units:
            published_path = os.path.join(self.publish_dir,
                    repo.id, constants.CONFIG_REPO_SUBDIR,
                    os.path.basename(unit.storage_path))
            self.assertEquals(os.readlink(published_path), unit.storage_path)
