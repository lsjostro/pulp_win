import logging
from pulp.plugins.importer import Importer
from pulp.plugins.util import verification
#from pulp.plugins.model import SyncReport
from gettext import gettext as _
from pulp_win.common.ids import SUPPORTED_TYPES
from pulp_win.plugins import models

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
            'types': sorted(SUPPORTED_TYPES),
        }

    def validate_config(self, repo, config):
        #return configuration.validate(config)
        return True, None

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        if type_id not in SUPPORTED_TYPES:
            return self.fail_report("Unsupported unit type {0}".format(type_id))
        checksum_type = metadata.get('checksumtype')
        checksum = metadata.get('checksum', '')
        verification.sanitize_checksum_type(unit_key.get('checksumtype'))
        checksum = checksum.lower()
        try:
            verification.verify_checksum(file(file_path, "rb"),
                    checksum_type=checksum_type,
                    checksum_value=checksum)
        except verification.InvalidChecksumType, e:
            _LOG.error(str(e))
            return self.fail_report(str(e))
        except verification.VerificationException:
            msg = "File checksum [%s] missmatch" % file_path
            _LOG.error(msg)
            return self.fail_report("Checksum mismatch")

        try:
            pkg = models.Package.from_file(file_path, metadata)
        except models.InvalidPackageError, e:
            return self.fail_report(str(e))

        pkg.init_unit(conduit)
        pkg.move_unit(file_path)
        pkg.save_unit(conduit)
        return dict(success_flag=True, summary={}, details={})

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        if not units:
            # If no units are passed in, assume we will use all units from source repo
            units = import_conduit.get_source_units()
        _LOG.info("Importing %s units from %s to %s" % (len(units), source_repo.id, dest_repo.id))
        for u in units:
            import_conduit.associate_unit(u)
        _LOG.debug("%s units from %s have been associated to %s" % (len(units), source_repo.id, dest_repo.id))
        return units


    @classmethod
    def fail_report(cls, message):
        # this is the format returned by the original importer. I'm not sure if
        # anything is actually parsing it
        details = {'errors': [message]}
        return {'success_flag': False, 'summary': '', 'details': details}

