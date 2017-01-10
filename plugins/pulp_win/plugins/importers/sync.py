import logging
import shutil
import tempfile
from gettext import gettext as _

from pulp.common.plugins import importer_constants
from pulp.plugins.util import verification
from pulp.server.controllers import units as units_controller
from pulp.server.exceptions import PulpCodedException
from pulp.server import util

from pulp_win.plugins.db import models
from pulp_win.plugins.importers.report import ContentReport

from pulp_rpm.plugins import error_codes
from pulp_rpm.plugins.importers.yum.listener import PackageListener
from pulp_rpm.plugins.importers.yum.repomd import alternate, packages, primary
from pulp_rpm.plugins.importers.yum import sync as yumsync

_logger = logging.getLogger(__name__)


class CancelException(Exception):
    pass


class RepoSync(yumsync.RepoSync):

    Type_Class_Map = {
        models.MSI.TYPE_ID: models.MSI,
        models.MSM.TYPE_ID: models.MSM,
    }

    def __init__(self, *args, **kwargs):
        super(RepoSync, self).__init__(*args, **kwargs)
        self.content_report = ContentReport()
        self.progress_report = {
            'metadata': {'state': 'NOT_STARTED'},
            'content': self.content_report,
        }
        # Enforce validation of downloaded content
        self.config.override_config[importer_constants.KEY_VALIDATE] = True

    def run(self):
        """
        Steps through the entire workflow of a repo sync.

        :return:    A SyncReport detailing how the sync went
        :rtype:     pulp.plugins.model.SyncReport
        """
        # Empty list could be returned in case _parse_as_mirrorlist()
        # was not able to find any valid url
        if not self.sync_feed:
            raise PulpCodedException(error_code=error_codes.RPM1004,
                                     reason='Not found')
        url_count = 0
        for url in self.sync_feed:
            # Verify that we have a feed url.
            # if there is no feed url, then we have nothing to sync
            if url is None:
                raise PulpCodedException(error_code=error_codes.RPM1005)
            # using this tmp dir ensures that cleanup leaves nothing behind,
            # since we delete below
            self.tmp_dir = tempfile.mkdtemp(dir=self.working_dir)
            url_count += 1
            try:
                with self.update_state(self.progress_report['metadata']):
                    metadata_files = self.check_metadata(url)
                    self.fix_metadata(metadata_files)
                    metadata_files = self.get_metadata(metadata_files)

                    # Save the default checksum from the metadata
                    self.save_default_metadata_checksum_on_repo(metadata_files)

                with self.update_state(self.content_report) as skip:
                    if not (skip or self.skip_repomd_steps):
                        self.update_content(metadata_files, url)

            except PulpCodedException, e:
                # Check if the caught exception indicates that the mirror is
                # bad.
                # Try next mirror in the list without raising the exception.
                # In case it was the last mirror in the list, raise the
                # exception.
                bad_mirror_exceptions = [error_codes.RPM1004, error_codes.RPM1006]  # noqa
                if (e.error_code in bad_mirror_exceptions) and \
                        url_count != len(self.sync_feed):
                            continue
                else:
                    self._set_failed_state(e)
                    raise

            except Exception, e:
                # In case other exceptions were caught that are not related to
                # the state of the mirror, raise the exception immediately and
                # do not iterate throught the rest of the mirrors.
                _logger.exception(e)
                self._set_failed_state(e)
                report = self.conduit.build_failure_report(
                    self._progress_summary, self.progress_report)
                return report

            finally:
                # clean up whatever we may have left behind
                shutil.rmtree(self.tmp_dir, ignore_errors=True)

            if self.config.override_config.get(importer_constants.KEY_FEED):
                self.erase_repomd_revision()
            else:
                self.save_repomd_revision()

            _logger.info(_('Sync complete.'))
            return self.conduit.build_success_report(self._progress_summary,
                                                     self.progress_report)

    def update_content(self, metadata_files, url):
        """
        Decides what to download and then downloads it

        :param metadata_files:  instance of MetadataFiles
        :type  metadata_files:  pulp_rpm.plugins.importers.yum.repomd.metadata.MetadataFiles
        :param url: curret URL we should sync
        :type: str
        """
        to_download, fileless = self._decide_what_to_download(metadata_files)
        self.download(metadata_files, to_download, url)
        self.save_fileless(metadata_files, fileless)
        self.conduit.build_success_report({}, {})

    def _decide_what_to_download(self, metadata_files):
        with metadata_files.get_metadata_file_handle(primary.METADATA_FILE_NAME) as primary_file_handle:  # noqa
            package_info_generator = packages.package_list_generator(
                primary_file_handle, primary.PACKAGE_TAG,
                self._process_package_element)

            sep_units = self._separate_units_by_type(package_info_generator)
        to_download = dict()
        for model_class, units in sorted(sep_units.items()):
            # Because models don't implement an __eq__, we can't simply throw
            # them in a set (even though they do implement __hash__)
            k2u = dict((u.unit_key_as_named_tuple, u)
                       for u in units)
            # Units from the database
            unit_generator = [model_class(**unit.unit_key)
                              for unit in sorted(units)]
            unit_generator = units_controller.find_units(unit_generator)
            upstream_unit_keys = set(k2u)
            # Compute the unit keys we need to download
            wanted = upstream_unit_keys.difference(
                u.unit_key_as_named_tuple for u in unit_generator)
            for existing_key in upstream_unit_keys.difference(wanted):
                existing = k2u[existing_key]
                # Existing units get re-associated
                yumsync.repo_controller.associate_single_unit(
                    self.conduit.repo, existing)
            to_download[model_class] = [k2u[k] for k in wanted]

        unit_counts = dict()
        flattened = set()
        fileless = set()
        for model_class, wanted in to_download.items():
            unit_counts[model_class.TYPE_ID] = len(wanted)
            if 'filename' in model_class._fields:
                flattened.update(wanted)
            else:
                fileless.update(wanted)

        total_size = sum(x.size for x in flattened if x.size)
        self.content_report.set_initial_values(unit_counts, total_size)
        self.set_progress()
        return flattened, fileless

    @classmethod
    def _separate_units_by_type(cls, units):
        ret = dict()
        for unit in units:
            ret.setdefault(unit.__class__, set()).add(unit)
        return ret

    def download(self, metadata_files, units_to_download, url):
        event_listener = CustomPackageListener(self, metadata_files)

        try:
            download_wrapper = alternate.Packages(
                url,
                self.nectar_config,
                units_to_download,
                self.tmp_dir,
                event_listener,
                self._url_modify)

            self.downloader = download_wrapper.downloader
            _logger.info(_('Downloading %(num)s units.') %
                         {'num': len(units_to_download)})
            download_wrapper.download_packages()
            self.downloader = None
        finally:
            pass

    @classmethod
    def _process_package_element(cls, el):
        pkg_type = el.attrib.get('type')
        if pkg_type not in cls.Type_Class_Map:
            raise error_codes.RPM1004(
                reason="Unsupported package type %s" % pkg_type)
        klass = cls.Type_Class_Map[pkg_type]
        package_info = dict()
        field_names = set(klass._fields.keys())
        field_names.add('size')
        for fname in field_names:
            if fname.startswith('_'):
                continue
            tag = '{%s}%s' % (primary.COMMON_SPEC_URL, fname)
            value = el.find(tag)
            if value is not None:
                package_info[fname] = value.text
                if fname == 'checksum' and 'type' in value.attrib:
                    package_info['checksumtype'] = value.attrib['type']
                if fname == 'size':
                    try:
                        size = int(value.attrib.get('package', 0))
                    except ValueError:
                        size = 0
                    package_info[fname] = size
        if 'relativepath' in klass._fields:
            location_element = el.find(primary.LOCATION_TAG)
            if location_element is not None:
                href = location_element.attrib['href']
                package_info['relativepath'] = href

        package_info['filename'] = klass.filename_from_unit_key(package_info)
        return klass(**package_info)

    def fix_metadata(self, metadata_files):
        metadata_files.generate_dbs = lambda *args, **kwargs: None

    def add_unit(self, metadata_files, unit, file_path):
        unit = unit.save_and_associate(file_path, self.conduit.repo)
        self.progress_report['content'].success(unit)
        self.set_progress()
        _logger.info("Added %r", unit)
        return unit

    def save_fileless(self, metadata_files, units):
        for unit in units:
            self.add_unit(metadata_files, unit, None)


class CustomPackageListener(PackageListener):
    def download_succeeded(self, report):
        _logger.info("%s: download succeeded", report.data._content_type_id)
        with util.deleting(report.destination):
            unit = report.data
            try:
                super(CustomPackageListener, self).download_succeeded(report)
            except (verification.VerificationException,
                    util.InvalidChecksumType):
                # verification failed, unit not added
                return

            # At this point, the checksum validation should have already
            # caught whether the unit is invalid, so we should be reasonably
            # sure the same unit is on disk
            unit_dl = unit.__class__.from_file(report.destination)

            _logger.info("Adding %s unit", unit_dl._content_type_id)
            added_unit = self.sync.add_unit(self.metadata_files, unit_dl,
                                            report.destination)
            if not added_unit.downloaded:
                added_unit.downloaded = True
                added_unit.save()

    def _verify_size(self, *args, **kwargs):
        # Since size is not part of the metadata saved in the repomd files, we
        # are bypassing this verification
        return
