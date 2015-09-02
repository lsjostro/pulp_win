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
        metadata = dict(checksumtype="sha256")
        m = hashlib.sha256()
        f = open(filename, 'rb')
        while 1:
            buffer = f.read(65536)
            if not buffer:
                break
            m.update(buffer)
        f.close()
        metadata.update(checksum=m.hexdigest()
        return {}, metadata
