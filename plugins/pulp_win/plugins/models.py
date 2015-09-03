import hashlib
import os
import shutil
import subprocess
from pulp_win.common import ids

MSIINFO_PATH = '/usr/bin/msiinfo'
if not os.path.exists(MSIINFO_PATH):
    raise RuntimeError("msiinfo is not available")

class Error(Exception):
    pass

class InvalidPackageError(Error):
    pass

class Package(object):
    _ATTRS = set(['UpgradeCode', 'ProductCode', 'Manufacturer'])
    UNIT_KEY_NAMES = set(['ProductName', 'ProductVersion',
        'checksumtype', 'checksum'])
    def __init__(self, unit_key, metadata):
        self.unit_key = unit_key
        self.metadata = metadata
        self._unit = None

    @classmethod
    def from_file(cls, filename, user_metadata=None, calculate_checksum=False):
        if not user_metadata:
            user_metadata = {}
        cmd = [MSIINFO_PATH, 'export', filename, 'Property']
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
        except Exception, e:
            raise Error(str(e))
        if p.returncode != 0:
            raise InvalidPackageError(stderr)
        headers = ( h.rstrip().partition('\t')
            for h in stdout.split('\n') )
        headers = dict((x[0], x[2]) for x in headers if x[1] == '\t')
        unit_key = dict(checksumtype='sha256')
        checksum_type = user_metadata.get('checksumtype', '').lower()
        if checksum_type != unit_key['checksumtype']:
            # The client may choose whatever checksum it suits them.
            # Internally we will only use sha256
            checksum_type = None
        checksum = user_metadata.get('checksum', '').lower()
        if calculate_checksum or not (checksum_type and checksum):
            m = hashlib.sha256()
            with file(filename, "rb") as fobj:
                while 1:
                    buf = fobj.read(65536)
                    if not buf:
                        break
                    m.update(buf)
            unit_key.update(checksum=m.hexdigest())
        else:
            unit_key.update(checksum=checksum)
        for unit_key_name in cls.UNIT_KEY_NAMES:
            unit_key.setdefault(unit_key_name, headers.get(unit_key_name))
        metadata = {}
        for attr in cls._ATTRS:
            metadata[attr] = headers.get(attr)
        metadata['filename'] = "{0}-{1}.msi".format(unit_key['ProductName'],
                unit_key['ProductVersion'])
        # For now, not sure how to generate EXE
        return MSI(unit_key, metadata)

    @property
    def relative_path(self):
        return os.path.join(self.unit_key['ProductName'],
                self.unit_key['ProductVersion'], self.unit_key['checksum'],
                self.metadata['filename'])

    def init_unit(self, conduit):
        self._unit = conduit.init_unit(self.TYPE_ID, self.unit_key,
                self.metadata, self.relative_path)
        return self

    def move_unit(self, file_path):
        shutil.move(file_path, self._unit.storage_path)

    def save_unit(self, conduit):
        conduit.save_unit(self._unit)

class MSI(Package):
    TYPE_ID = ids.TYPE_ID_MSI

class EXE(Package):
    TYPE_ID = ids.TYPE_ID_EXE
