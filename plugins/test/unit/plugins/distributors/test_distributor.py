import os
import shutil
import sys
import time
import uuid
import hashlib
from xml.etree import ElementTree

import mock
from .... import testbase

from pulp.plugins.util.manifest_writer import get_sha256_checksum

from pulp_win.common import ids
from pulp_win.plugins.db import models


class BaseTest(testbase.TestCase):
    def setUp(self):
        super(BaseTest, self).setUp()
        self._meta_path = sys.meta_path
        from pulp_win.plugins.distributors import distributor
        self.Module = distributor
        self.Configuration = distributor.configuration
        root = os.path.join(self.work_dir, "root")
        self._confmock = mock.patch.dict(
            distributor.configuration.__dict__,
            ROOT_PUBLISH_DIR=root,
            MASTER_PUBLISH_DIR=os.path.join(root, "master"),
            HTTP_PUBLISH_DIR=os.path.join(root, "http", "repos"),
            HTTPS_PUBLISH_DIR=os.path.join(root, "https", "repos"),
        )
        self._confmock.start()

    def tearDown(self):
        self._confmock.stop()
        sys.meta_path = self._meta_path
        shutil.rmtree(self.work_dir)
        super(BaseTest, self).tearDown()

    def _config_conduit(self):
        ret = mock.MagicMock()
        ret.get_repo_distributors_by_relative_url.return_value = []
        return ret


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
        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = {}
        distributor = self.Module.WinDistributor()
        self.assertEquals(
            (False, '\n'.join([
                'Configuration key [http] is required, but was not provided',
                'Configuration key [https] is required, but was not provided',
                'Configuration key [relative_url] is required, but was not provided',  # noqa
                'Settings serve via http and https are both set to false. At least one option should be set to true.',  # noqa
            ])),
            distributor.validate_config(repo, config, conduit))

    def test_validate_config(self):
        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = dict(http=True, https=False, relative_url=None)
        distributor = self.Module.WinDistributor()
        self.assertEquals(
            distributor.validate_config(repo, config, conduit),
            (True, None))


class PublishRepoMixIn(object):
    @classmethod
    def _units(cls, storage_dir):
        units = [
            cls.Model(
                _storage_path=None,
                **x)
            for x in cls.Sample_Units]
        for unit in units:
            unit.filename = unit.filename_from_unit_key(unit.unit_key)
            _p = unit._storage_path = os.path.join(
                storage_dir, unit.filename)
            file(_p, "wb").write(str(uuid.uuid4()))
            unit.checksumtype = 'sha256'
            unit.checksum = hashlib.sha256(
                open(_p, "rb").read()).hexdigest()
        return units

    @mock.patch("pulp_win.plugins.distributors.distributor.RepomdXMLFileContext")  # noqa
    @mock.patch("pulp_win.plugins.distributors.distributor.PrimaryXMLFileContext")  # noqa
    @mock.patch("pulp.server.managers.repo._common.task.current")
    @mock.patch('pulp.plugins.util.publish_step.repo_controller')
    def test_publish_repo(self, _repo_controller,
                          _task_current, PrimaryXMLFileContext,
                          RepomdXMLFileContext):
        task_id = _task_current.request.id = 'aabb'
        worker_name = "worker01"
        _task_current.request.configure_mock(hostname=worker_name)
        os.makedirs(os.path.join(self.pulp_working_dir, worker_name))
        # Set up some files
        storage_dir = os.path.join(self.work_dir, 'storage_dir')
        publish_dir = os.path.join(self.work_dir, 'publish_dir')
        os.makedirs(storage_dir)
        units = self._units(storage_dir)

        unit_dict = dict()
        unit_counts = dict()
        for type_id in sorted(ids.SUPPORTED_TYPES):
            _l = unit_dict[type_id] = [u for u in units
                                       if u.type_id == type_id]
            unit_counts[type_id] = len(_l)

        distributor = self.Module.WinDistributor()
        repo = mock.Mock()
        repo_id = "repo-%d-win-level0" % int(time.time())
        repo.configure_mock(
            working_dir=os.path.join(self.work_dir, 'work_dir'),
            content_unit_counts=unit_counts,
            id=repo_id)

        def mock_get_units(repo_id, model_class, *args, **kwargs):
            units = unit_dict[model_class.TYPE_ID]
            query = mock.MagicMock()
            query.count.return_value = len(units)
            query.__iter__.return_value = iter(units)
            return [query]
        _repo_controller.get_unit_model_querysets.side_effect = mock_get_units
        conduit = self._config_conduit()
        repo_config = dict(
            http=True, https=False,
            relative_url='level1/' + repo.id,
            http_publish_dir=publish_dir+'/http/repos',
            https_publish_dir=publish_dir+'/https/repos')

        distributor.publish_repo(repo, conduit, config=repo_config)
        self.assertEquals(
            [x[0][0] for x in conduit.build_success_report.call_args_list],
            [{'publish_directory': 'FINISHED', 'publish_modules': 'FINISHED'}])
        self.assertEquals(
            [x[0][1][0]['num_processed']
             for x in conduit.build_success_report.call_args_list],
            [1])
        self.assertEquals(
            [len(x[0][1][0]['sub_steps'])
             for x in conduit.build_success_report.call_args_list],
            [3])
        # Make sure symlinks got created
        for unit in units:
            published_path = os.path.join(
                repo_config['http_publish_dir'],
                repo_config['relative_url'],
                unit.filename)
            self.assertEquals(os.readlink(published_path), unit.storage_path)

        exp = [
            mock.call(repo.id, models.MSI, None),
            mock.call(repo.id, models.MSM, None),
        ]
        self.assertEquals(
            exp,
            _repo_controller.get_unit_model_querysets.call_args_list)

        publish_dir = os.path.join(repo_config['http_publish_dir'],
                                   repo_config['relative_url'])

        # Make sure we've invoked the repomd publisher
        wdir = os.path.join(self.pulp_working_dir, worker_name, task_id)
        RepomdXMLFileContext.assert_called_once_with(wdir, 'sha256')
        exp_units = units
        count = len(exp_units)
        PrimaryXMLFileContext.assert_called_once_with(wdir, count, 'sha256')
        cargs = PrimaryXMLFileContext.return_value.__enter__.return_value.add_unit_metadata.call_args_list  # noqa
        self.assertEquals(
            [mock.call(u) for u in exp_units],
            cargs
        )

        processed_units = [x[0][0] for x in cargs]
        checksum_nodes = [
            self._xml_path(u.render_primary(None),
                           'checksum')
            for u in processed_units]
        self.assertEquals(
            [x.checksum for x in exp_units],
            [node.text for node in checksum_nodes])
        self.assertEquals(
            [dict(pkgid='YES', type='sha256')
             for x in exp_units],
            [node.attrib for node in checksum_nodes])
        self.assertEquals(
            ['sha256'] * len(cargs),
            [self._xml_path(x[0][0].render_primary(None),
                            'checksum').attrib['type']
             for x in cargs]
        )
        exp_filenames = [x.filename for x in exp_units]
        self.assertEquals(
            exp_filenames,
            [self._xml_path(x[0][0].render_primary(None),
                            'location').get('href')
             for x in cargs]
        )
        self.assertEquals(
            [str(x.size) for x in exp_units],
            [self._xml_path(x[0][0].render_primary(None),
                            'size').get('package')
             for x in cargs]
        )
        self.assertEquals(
            [get_sha256_checksum(
                os.path.join(publish_dir, x))
             for x in exp_filenames],
            [self._xml_path(x[0][0].render_primary(None),
                            'checksum').text
             for x in cargs]
        )

        # Delete distributor
        master_repo_dir = self.Configuration.get_master_publish_dir(
            repo, ids.TYPE_ID_DISTRIBUTOR_WIN)
        self.assertTrue(os.path.exists(master_repo_dir))
        self.assertTrue(os.path.exists(publish_dir))
        distributor.distributor_removed(repo, repo_config)
        self.assertFalse(os.path.exists(master_repo_dir))
        self.assertFalse(os.path.exists(publish_dir))

    @classmethod
    def _xml_path(cls, strxml, *paths):
        el = ElementTree.fromstring(strxml)
        for p in paths:
            el = el.find(p)
        return el

class TestPublishRepoMSI(PublishRepoMixIn, BaseTest):
    Model = models.MSI
    Sample_Units = [
        dict(name='burgundy', version='0.1938.0',
             checksum='abcde', checksumtype='sha3.14'),
        dict(name='chablis', version='0.2013.0',
             checksum='yz', checksumtype='sha3.14'),
        ]

class TestPublishRepoMSM(PublishRepoMixIn, BaseTest):
    Model = models.MSM
    Sample_Units = [
        dict(name='sugar', version='0.1.0',
             checksum='0000s', checksumtype='sha3.14'),
        dict(name='yeast', version='0.2.0',
             checksum='0000y', checksumtype='sha3.14'),
        ]
