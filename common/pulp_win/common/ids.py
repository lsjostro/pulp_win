# Copyright (c) 2012-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

TYPE_ID_DISTRIBUTOR_WIN = "win_distributor"
TYPE_ID_IMPORTER_WIN = "win_importer"

# The server will use the type ID as the importer ID, but have it as a separate
# constant in case that changes
WIN_IMPORTER_ID = TYPE_ID_IMPORTER_WIN

# Set when the distributor is added to the repo and later to refer to it specifically
WIN_DISTRIBUTOR_ID = 'win_distributor'

TYPE_ID_MSI = "msi"
UNIT_KEY_MSI = (
    "name", "version", "release", "checksum", "checksumtype")

TYPE_ID_EXE = "exe"
UNIT_KEY_EXE = UNIT_KEY_MSI

SUPPORTED_TYPES = set([TYPE_ID_MSI, TYPE_ID_EXE])
