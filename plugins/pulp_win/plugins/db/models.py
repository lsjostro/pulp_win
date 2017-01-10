import io
import logging
import os
import subprocess
import mongoengine
from pulp.server import util
from pulp.server.controllers import repository as repo_controller
from pulp.server.db.model import FileContentUnit
from pulp_rpm.plugins.db.fields import ChecksumTypeStringField
from pulp_win.common import ids
from xml.etree import ElementTree

MSIINFO_PATH = '/usr/bin/msiinfo'
if not os.path.exists(MSIINFO_PATH):
    raise RuntimeError("msiinfo is not available")

_LOGGER = logging.getLogger(__name__)

NotUniqueError = mongoengine.NotUniqueError


class Error(ValueError):
    pass


class InvalidPackageError(Error):
    pass


class Package(FileContentUnit):
    meta = dict(abstract=True)

    name = mongoengine.StringField(required=True)
    version = mongoengine.StringField(required=True)
    checksum = mongoengine.StringField(required=True)
    checksumtype = ChecksumTypeStringField(required=True)
    size = mongoengine.IntField()

    filename = mongoengine.StringField(required=True)
    relativepath = mongoengine.StringField()

    UNIT_KEY_TO_FIELD_MAP = dict()
    REPOMD_EXTRA_FIELDS = []

    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)
        # Additional data to be saved in the repodata representation
        self.repodata = None
        self.base_url = None
        # Needed by sync verification
        self.checksums = {}

    def __str__(self):
        return '<%s: %s>' % (
            self._content_type_id,
            '; '.join('%s=%r' % (name, getattr(self, name))
                      for name in self.unit_key_fields))

    @classmethod
    def from_file(cls, filename, user_metadata=None):
        if hasattr(filename, "read"):
            fobj = filename
        else:
            try:
                fobj = open(filename, "r")
            except IOError as e:
                raise Error(str(e))
        if not user_metadata:
            user_metadata = {}
        unit_md = cls._read_metadata(filename)
        unit_md.update(checksumtype=util.TYPE_SHA256,
                       checksum=cls._compute_checksum(fobj),
                       size=fobj.tell())

        ignored = set(['filename'])

        metadata = dict()
        user_md = dict()
        for attr, fdef in cls._fields.items():
            if attr == 'id' or attr.startswith('_'):
                continue
            prop_name = cls.UNIT_KEY_TO_FIELD_MAP.get(attr, attr)
            val = unit_md.get(prop_name)
            if val is None and fdef.required and attr not in ignored:
                raise Error('Required field is missing: {}'.format(attr))
            metadata[attr] = val
            if user_metadata and attr in user_metadata:
                # We won't be mapping fields like ProductVersion from
                # user_metadata, if the user wanted to overwrite something
                # they'd have done it with the properties pulp expects.
                user_md[attr] = user_metadata[attr]
        metadata['filename'] = cls.filename_from_unit_key(metadata)
        # Overwriting metadata extracted from the file with user-specified
        # metadata seems dangerous. If this statement is not correct,
        # uncomment the line below.
        # metadata.update(user_md)
        return cls(**metadata)

    @classmethod
    def _run_cmd(cls, cmd):
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
        except Exception, e:
            raise Error(str(e))
        if p.returncode != 0:
            raise InvalidPackageError(stderr)
        return stdout, stderr

    @classmethod
    def _compute_checksum(cls, fobj):
        cstype = util.TYPE_SHA256
        return util.calculate_checksums(fobj, [cstype])[cstype]

    @classmethod
    def filename_from_unit_key(cls, unit_key):
        return "{0}-{1}.{2}".format(
            unit_key['name'], unit_key['version'], cls.TYPE_ID)

    @property
    def download_path(self):
        """
        This should only be used during the initial sync
        """
        return self.relativepath

    def get_symlink_name(self):
        return self.filename

    @property
    def all_properties(self):
        ret = dict()
        for k in self.__class__._fields:
            if k.startswith('_'):
                continue
            ret[k] = getattr(self, k)
        return ret

    def associate(self, repo):
        repo_controller.associate_single_unit(
            repository=repo, unit=self)
        return self

    def save_and_associate(self, file_path, repo):
        with_filename = ('filename' in self.__class__._fields)
        if with_filename:
            filename = self.filename_from_unit_key(self.unit_key)
            self.set_storage_path(filename)
        unit = self
        try:
            self.save()
            if with_filename:
                self.safe_import_content(file_path)
        except NotUniqueError:
            unit = self.__class__.objects.filter(**unit.unit_key).first()
        unit.associate(repo)
        return unit

    @classmethod
    def _read_msi_module_signature(cls, filename):
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa370051(v=vs.85).aspx
        cmd = [MSIINFO_PATH, 'export', filename, 'ModuleSignature']
        stdout, _ = cls._run_cmd(cmd)
        # According to the document linked above, the ModuleID is always
        # name.GUID. msiinfo will return a bunch of header rows which are not
        # in that format, so the rpartition will skip them.
        metadata = []
        for row in stdout.split('\n'):
            arr = row.rstrip().split('\t', 2)
            if len(arr) != 3:
                continue
            name, sep, guid = arr[0].rpartition('.')
            if not sep:
                continue
            metadata.append(dict(name=name, guid=guid, version=arr[2]))
        metadata.sort(key=lambda x: (x['name'], x['version']))
        return metadata

    @classmethod
    def _read_msi_tables(cls, filename):
        cmd = [MSIINFO_PATH, 'tables', filename]
        stdout, _ = cls._run_cmd(cmd)
        tables = set(h.rstrip() for h in stdout.split('\n'))
        return tables

    def render_primary(self, checksumtype):
        sio = io.BytesIO()
        el = self._package_to_xml(checksumtype)
        et = ElementTree.ElementTree(el)
        et.write(sio, encoding="utf-8")
        return sio.getvalue()

    def _package_to_xml(self, checksumtype):
        unit_key = self.unit_key
        checksum_type = unit_key.pop('checksumtype',
                                     self.checksumtype or checksumtype)
        if self.checksum:
            unit_key['checksum'] = self.checksum
        for field in self.REPOMD_EXTRA_FIELDS:
            val = getattr(self, field)
            if val is not None:
                unit_key[field] = val
        el = self._to_xml_element("package",
                                  attrib=dict(type=self.type_id),
                                  content=unit_key)
        csum_nodes = el.findall('checksum')
        if csum_nodes:
            csum_node = csum_nodes[0]
            csum_node.attrib.update(pkgid="YES", type=checksum_type)
        ElementTree.SubElement(
            el, "size", attrib=dict(package=str(self.size)))
        ElementTree.SubElement(el, "location", attrib=dict(href=self.filename))
        return el

    @classmethod
    def _to_xml_element(cls, tag, attrib=None, content=None):
        if attrib is None:
            attrib = dict()
        if content is None:
            content = dict()
        el = ElementTree.Element(tag, attrib=attrib)
        for k, v in sorted(content.items()):
            ElementTree.SubElement(el, k).text = v
        return el


class MSI(Package):
    TYPE_ID = TYPE = ids.TYPE_ID_MSI
    meta = dict(collection='units_msi',
                indexes=list(ids.UNIT_KEY_MSI))

    unit_key_fields = ids.UNIT_KEY_MSI
    unit_display_name = 'MSI'
    unit_description = 'MSI'

    UNIT_KEY_TO_FIELD_MAP = dict(name='ProductName', version='ProductVersion')
    REPOMD_EXTRA_FIELDS = ['ProductCode', 'UpgradeCode']

    UpgradeCode = mongoengine.StringField()
    ProductCode = mongoengine.StringField()
    Manufacturer = mongoengine.StringField()
    ModuleSignature = mongoengine.ListField()

    # For backward compatibility
    _ns = mongoengine.StringField(default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True,
                                               default=TYPE_ID)

    @classmethod
    def _read_metadata(cls, filename):
        tables = cls._read_msi_tables(filename)
        if 'Property' not in tables:
            raise InvalidPackageError("MSI does not have a Property table")
        cmd = [MSIINFO_PATH, 'export', filename, 'Property']
        stdout, stderr = cls._run_cmd(cmd)
        headers = (h.rstrip().partition('\t')
                   for h in stdout.split('\n'))
        headers = dict((x[0], x[2]) for x in headers if x[1] == '\t')
        # Add the module signature, to link an MSI to an MSM
        if 'ModuleSignature' in tables:
            module_signature = cls._read_msi_module_signature(filename)
        else:
            module_signature = []
        headers['ModuleSignature'] = module_signature
        return headers


class MSM(Package):
    TYPE_ID = TYPE = ids.TYPE_ID_MSM

    meta = dict(collection='units_msm',
                indexes=list(ids.UNIT_KEY_MSM))

    unit_key_fields = ids.UNIT_KEY_MSM
    unit_display_name = 'MSM'
    unit_description = 'MSM'

    guid = mongoengine.StringField()

    # For backward compatibility
    _ns = mongoengine.StringField(default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True,
                                               default=TYPE_ID)

    @classmethod
    def _read_metadata(cls, filename):
        # First, dump tables. An MSM should not contain Property
        tables = cls._read_msi_tables(filename)
        if 'Property' in tables:
            raise InvalidPackageError("Attempt to handle an MSI as an MSM")
        if 'ModuleSignature' not in tables:
            # Theoretically impossible:
            # https://msdn.microsoft.com/en-us/library/windows/desktop/aa370051(v=vs.85).aspx
            raise InvalidPackageError("ModuleSignature is missing")

        # According to the document linked above, the ModuleID is always
        # name.GUID. msiinfo will return a bunch of header rows which are not
        # in that format, so the rpartition will skip them.
        module_signature = cls._read_msi_module_signature(filename)
        if len(module_signature) != 1:
            raise InvalidPackageError(
                "Not a valid MSM: more than one entry in ModuleSignature")
        metadata = module_signature[0]
        return metadata
