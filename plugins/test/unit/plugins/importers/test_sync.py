"""
Contains tests for plugins.importers.importer.
"""
import json
import mock
import os

from .... import testbase
from pulp_win.plugins.importers import sync


class TestSync(testbase.TestCase):
    def new_config(self, feed="http://example.com/repo"):
        cfgdict = dict(feed=feed)
        config = mock.MagicMock()
        config.configure_mock(**cfgdict)
        config.flatten.return_value = cfgdict
        config.get.side_effect = cfgdict.get
        return config

    @mock.patch("pulp_win.plugins.db.models.MSM.save_and_associate")
    @mock.patch("pulp_win.plugins.db.models.MSM.from_file")
    @mock.patch("pulp_win.plugins.db.models.MSI.save_and_associate")
    @mock.patch("pulp_win.plugins.db.models.MSI.from_file")
    @mock.patch("nectar.downloaders.threaded.requests.Session")
    @mock.patch("pulp.server.content.sources.container.managers.content_catalog_manager")  # noqa
    @mock.patch("pulp.server.content.sources.container.ContentSource",
                autospec=True)
    @mock.patch("pulp_rpm.plugins.importers.yum.sync.metadata.nectar_factory")
    @mock.patch("pulp.server.managers.repo._common.task.current")
    @mock.patch("pulp_win.plugins.importers.sync.units_controller")
    @mock.patch("pulp_rpm.plugins.importers.yum.sync.repo_controller")
    @mock.patch("pulp_win.plugins.db.models.repo_controller")
    def test_sync(self, _db_repo_controller,
                  _repo_controller, _units_controller, _task_current,
                  _nectar_factory, _ContentSource, _content_catalog_manager,
                  _Session,
                  _msi_from_file, _msi_save_and_associate,
                  _msm_from_file, _msm_save_and_associate):
        _task_current.request.id = 'aabb'
        worker_name = "worker01"
        _task_current.request.configure_mock(hostname=worker_name)
        os.makedirs(os.path.join(self.pulp_working_dir, worker_name))

        _ContentSource.return_value.load_all.return_value = []
        _content_catalog_manager.return_value.has_entries.return_value = True

        sess = _Session.return_value
        responses = [
            mock.MagicMock(
                status_code=200, headers={},
                **{"iter_content.return_value": [json.dumps(
                    dict(name='a', version='1.0'))]}),
            mock.MagicMock(
                status_code=200, headers={},
                **{"iter_content.return_value": [json.dumps(
                    dict(name='a', version='1.0'))]}),
        ]
        sess.get.side_effect = responses

        repo = mock.MagicMock()
        conduit = mock.MagicMock(**{"last_sync.return_value": None})
        config = self.new_config()

        _repo_controller.missing_unit_count.return_value = 10

        # An existing unit which should not be re-downloaded
        _units_controller.find_units.return_value = [
            sync.models.MSI(name="existing", version="1",
                            checksumtype="sha256", checksum="existing1")
        ]

        _xml_content = {
            "repomd.xml": REPOMD_XML,
            "CSUM1-primary.xml": REPODATA_PRIMARY_XML,
        }

        def mock_download(requests):
            for request in requests:
                data = _xml_content.get(os.path.basename(request.destination))
                if data is not None:
                    open(request.destination, "w").write(data)
                    continue
                raise Exception("Unknown metadata file requested")

        _nectar_factory.create_downloader.return_value.download.side_effect = \
            mock_download

        unit1 = sync.models.MSI(
            name='a', version='1', checksumtype='sha256',
            checksum='8158106e4b75399561fc30c6e486f3a78a3c221a1101dcf2edd0f1547c9bdd3f',
            filename='a-1.msi', _last_updated=1234567890,
            size=123,
        )
        _msi_from_file.return_value = unit1
        _msi_save_and_associate.return_value = unit1

        unit2 = sync.models.MSM(
            name='a', version='1', checksumtype='sha256',
            checksum='befd9977547415cccf82ac4e7f573f9cec1730dd124499c0a8f03b79ad73bf6a',
            filename='a-1.msm', _last_updated=1234567890,
            size=123,
        )
        _msm_from_file.return_value = unit2
        _msm_save_and_associate.return_value = unit2

        reposync = sync.RepoSync(repo, conduit, config)

        ret = reposync.run()
        self.assertEquals(
            conduit.build_success_report.return_value,
            ret)

        self.assertEquals(
            [
                mock.call({}, {}),
                mock.call(
                    {'content': {'state': 'FINISHED'},
                     'metadata': {'state': 'FINISHED'}},
                    {'content': {'size_total': 246, 'items_left': 0,
                                 'items_total': 2,
                                 'state': 'FINISHED', 'size_left': 0,
                                 'details': {'msm_done': 1, 'msi_total': 1,
                                             'msm_total': 1, 'msi_done': 1},
                                 'error_details': []},
                     'metadata': {'state': 'FINISHED'}}
                ),
            ],
            conduit.build_success_report.call_args_list)


REPOMD_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo"
    xmlns:rpm="http://linux.duke.edu/metadata/rpm">
  <revision>1476732856</revision>
  <data type="primary">
    <location href="repodata/CSUM1-primary.xml"/>
    <timestamp>1476732856</timestamp>
    <size>438</size>
    <checksum type="sha256">CSUM1</checksum>
    <open-size>895</open-size>
    <open-checksum type="sha256">CSUM2</open-checksum>
  </data>
</repomd>
"""

REPODATA_PRIMARY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="2">
  <package type="msi">
    <checksum pkgid="YES" type="sha256">8158106e4b75399561fc30c6e486f3a78a3c221a1101dcf2edd0f1547c9bdd3f</checksum>
    <name>a</name>
    <version>1.0</version>
    <size package="123"/>
    <location href="a-1.msi"/>
  </package>
  <package type="msi">
    <checksum pkgid="YES" type="sha256">existing1</checksum>
    <name>existing</name>
    <version>1</version>
    <size package="42"/>
    <location href="existing-1.msi"/>
  </package>
  <package type="msm">
    <checksum pkgid="YES" type="sha256">befd9977547415cccf82ac4e7f573f9cec1730dd124499c0a8f03b79ad73bf6a</checksum>
    <name>a</name>
    <version>1</version>
    <size package="123"/>
    <location href="a-1.msm"/>
  </package>
</metadata>
"""
