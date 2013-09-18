# -*- coding: utf-8 -*-
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _
import hashlib
import os
from sh import msiinfo
import sys

from pulp.client.commands.repo.upload import UploadCommand, MetadataException
from pulp_win.common.ids import TYPE_ID_MSI


NAME = 'msi'
DESC = _('uploads one or more MSIs into a repository')


class CreateMsiCommand(UploadCommand):
    """
    Handles initializing and uploading one or more RPMs.
    """

    def __init__(self, context, upload_manager, name=NAME, description=DESC):
        super(CreateMsiCommand, self).__init__(context, upload_manager, name=name, description=description)

    def determine_type_id(self, filename, **kwargs):
        return TYPE_ID_MSI

    def matching_files_in_dir(self, dir):
        all_files_in_dir = super(CreateMsiCommand, self).matching_files_in_dir(dir)
        msis = [f for f in all_files_in_dir if f.endswith('.msi')]
        return msis

    def generate_unit_key_and_metadata(self, filename, **kwargs):
        unit_key, metadata = _generate_msi_data(filename)
        return unit_key, metadata


def _generate_msi_data(msi_filename):
    """
    For the given MSI, analyzes its metadata to generate the appropriate unit
    key and metadata fields, returning both to the caller.

    @param msi_filename: full path to the MSI to analyze
    @type  msi_filename: str

    @return: tuple of unit key and unit metadata for the MSI
    @rtype:  tuple
    """

    # Expected unit key fields:
    # "name", "version", "checksumtype", "checksum", "filename"

    unit_key = dict()
    metadata = dict()

    # Read the MSI header attributes for use later
    try:
        msi_export = msiinfo(["export", msi_filename, "Property"]).rstrip()
        headers = dict([h.rstrip().split('\t') for h in msi_export.split('\n')])
    except:
        # Raised if the headers cannot be read
        msg = _('The given file is not a valid MSI')
        raise MetadataException(msg), None, sys.exc_info()[2]

    # -- Unit Key -----------------------

    # Checksum
    unit_key['checksumtype'] = 'md5' # hardcoded to this in v1 so leaving this way for now

    m = hashlib.new(unit_key['checksumtype'])
    f = open(msi_filename, 'r')
    while 1:
        buffer = f.read(65536)
        if not buffer:
            break
        m.update(buffer)
    f.close()

    unit_key['checksum'] = m.hexdigest()
    unit_key['name'] = headers['ProductName']
    unit_key['version'] = headers['ProductVersion']
    metadata['filename'] = os.path.basename(msi_filename)

    return unit_key, metadata
