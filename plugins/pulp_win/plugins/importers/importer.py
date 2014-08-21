import shutil
import os
import logging
import hashlib
from pulp.plugins.importer import Importer
#from pulp.plugins.model import SyncReport
from gettext import gettext as _

_LOG = logging.getLogger(__name__)

def entry_point():
    return WinImporter, {}

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

    def validate_config(self, repo, config):
        #return configuration.validate(config)
        return True, None

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        try:
            num_units_saved = 0
            status, summary, details = self._upload_unit(repo, type_id, unit_key, metadata, file_path, conduit, config)
            if summary.has_key("num_units_saved"):
                num_units_saved = int(summary["num_units_saved"])
            if status:
                report = {'success_flag': True, 'summary': summary, 'details': details}
                #report = SyncReport(True, num_units_saved, 0, 0, summary, details)
            else:
                report = {'success_flag': False, 'summary': summary, 'details': details}
                #report = SyncReport(False, num_units_saved, 0, 0, summary, details)
        except Exception, e:
            _LOG.exception("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = {'success_flag': False, 'summary': summary, 'details': {}}
            #report = SyncReport(False, 0, 0, 0, summary, None)
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

        file_checksum = get_file_checksum(filename=file_path, hashtype=unit_key['checksumtype'])
        if file_checksum != unit_key['checksum']:
            msg = "File checksum [%s] missmatch" % file_path
            _LOG.error(msg)
            details['errors'].append(msg)
            return False, summary, details

        relative_path = "%s/%s/%s/%s" % (unit_key['name'], unit_key['version'],
                                         unit_key['checksum'], metadata['filename'])
        u = conduit.init_unit(type_id, unit_key, metadata, relative_path)
        new_path = u.storage_path
        try:
            if os.path.exists(new_path):
                existing_checksum = get_file_checksum(filename=new_path, hashtype=unit_key['checksumtype'])
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

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        if not units:
            # If no units are passed in, assume we will use all units from source repo
            units = import_conduit.get_source_units()
        _LOG.info("Importing %s units from %s to %s" % (len(units), source_repo.id, dest_repo.id))
        for u in units:
            if u.type_id == 'msi':
                import_conduit.associate_unit(u)
        _LOG.debug("%s units from %s have been associated to %s" % (len(units), source_repo.id, dest_repo.id))

    def get_file_checksum(filename=None, fd=None, file=None, buffer_size=None, hashtype="sha256"):
        """
        Compute a file's checksum.
        """
        if hashtype in ['sha', 'SHA']:
            hashtype = 'sha1'

        if buffer_size is None:
            buffer_size = 65536

        if filename is None and fd is None and file is None:
            raise Exception("no file specified")
        if file:
            f = file
        elif fd is not None:
            f = os.fdopen(os.dup(fd), "r")
        else:
            f = open(filename, "r")
        # Rewind it
        f.seek(0, 0)
        m = hashlib.new(hashtype)
        while 1:
            buffer = f.read(buffer_size)
            if not buffer:
                break
            m.update(buffer)

        # cleanup time
        if file is not None:
            file.seek(0, 0)
        else:
            f.close()
        return m.hexdigest()
