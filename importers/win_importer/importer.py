import shutil
import os
import logging
from pulp_rpm.yum_plugin import util
from pulp.plugins.importer import Importer
from pulp.plugins.model import SyncReport
from gettext import gettext as _

_LOG = logging.getLogger(__name__)

class WinImporter(Importer):
    def __init__(self):
        super(WinImporter, self).__init__()
        self.sync_cancelled = False
    @classmethod
    def metadata(cls):
        return {
            'id': "win_importer",
            'display_name': _('Windows importer'),
            'types': ['msi', 'exe']
        }

    def validate_config(self, repo, config, related_repos):
        #return configuration.validate(config)
        return True, None

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        try:
            num_units_saved = 0
            status, summary, details = self._upload_unit(repo, type_id, unit_key, metadata, file_path, conduit, config)
            if summary.has_key("num_units_saved"):
                num_units_saved = int(summary["num_units_saved"])
            if status:
                report = SyncReport(True, num_units_saved, 0, 0, summary, details)
            else:
                report = SyncReport(False, num_units_saved, 0, 0, summary, details)
        except Exception, e:
            _LOG.exception("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = SyncReport(False, 0, 0, 0, summary, None)
        return report

    def _upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        summary = {}
        details = {'errors' : []}
        summary['filename'] = metadata['filename']
        summary['num_units_processed'] = len([file_path])
        summary['num_units_saved'] = 0

        if type_id not in ['msi','exe']:
            raise NotImplementedError()

        if not os.path.exists(file_path):
            msg = "File path [%s] missing" % file_path
            _LOG.error(msg)
            details['errors'].append(msg)
            return False, summary, details
        relative_path = "%s/%s/%s/%s" % (unit_key['name'], unit_key['version'],
                                         unit_key['checksum'], metadata['filename'])
        #metadata = {}
        u = conduit.init_unit(type_id, unit_key, metadata, relative_path)
        new_path = u.storage_path
        try:
            if os.path.exists(new_path):
                existing_checksum = util.get_file_checksum(filename=new_path, hashtype=unit_key['checksumtype'])
                if existing_checksum != unit_key['checksum']:
                    # checksums dont match, remove existing file
                    os.remove(new_path)
                else:
                    _LOG.debug("Existing file is the same ")
            if not os.path.isdir(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            # copy the unit to the final path
            shutil.copy(file_path, new_path)
        except (IOError, OSError), e:
            msg = "Error copying upload file to final location [%s]; Error %s" % (new_path, e)
            details['errors'].append(msg)
            _LOG.error(msg)
            return False, summary, details
        conduit.save_unit(u)
        summary['num_units_processed'] = len([file_path])
        summary['num_units_saved'] = len([file_path])
        _LOG.debug("unit %s successfully saved" % u)
        if len(details['errors']):
            summary['num_errors'] = len(details['errors'])
            summary["state"] = "FAILED"
            return False, summary, details
        _LOG.info("Upload complete with summary: %s; Details: %s" % (summary, details))
        return True, summary, details
