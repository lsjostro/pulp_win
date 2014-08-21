# Copyright (c) 2012 Red Hat, Inc.
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
import logging

from pulp.client.extensions.extensions import PulpCliOptionGroup, PulpCliOption
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand

# -- constants ----------------------------------------------------------------

# Must correspond to the IDs in the type definitions
TYPE_MSI = 'msi'

# Intentionally does not include distributions; they should be looked up specifically
ALL_TYPES = (TYPE_MSI)

# List of all fields that the user can elect to display for each supported type
FIELDS_MSI = ('checksum', 'checksumtype',
              'filename', 'name', 'release', 'version')

# Used when generating the --fields help text so it can be customized by type
FIELDS_BY_TYPE = {
    TYPE_MSI : FIELDS_MSI,
    }

# Ordering of metadata fields in each type. Keep in mind these are the display
# ordering within a unit; the order of the units themselves in the returned
# list from the server is dictated by the --ascending/--descending options.
ORDER_MSI = ['name', 'version', 'release' ]

# Used to lookup the right order list based on type
ORDER_BY_TYPE = {
    TYPE_MSI : ORDER_MSI,
    }

LOG = logging.getLogger(__name__)

# -- constants ----------------------------------------------------------------

DESC_MSIS = _('search for MSIs in a repository')

# -- commands -----------------------------------------------------------------

class SearchMsisCommand(DisplayUnitAssociationsCommand):

    def __init__(self, context):
        super(SearchMsisCommand, self).__init__(self.msi, name='msi',
                                                description=DESC_MSIS)
        self.context = context

    def msi(self, **kwargs):
        def out_func(document_list, filter=FIELDS_MSI):
            """Inner function to filter msi fields to display to the end user"""

            order = []

            # if the --details option has been specified, we need to manually
            # apply filtering to the unit data itself, since okaara's filtering
            # only operates at the top level of the document.
            if kwargs.get(self.ASSOCIATION_FLAG.keyword):
                # including most fields
                filter = ['updated', 'repo_id', 'created', 'unit_id', 'metadata',
                          'unit_type_id', 'owner_type', 'id', 'owner_id']
                # display the unit info first
                order = ['metadata']

                # apply the same filtering that would normally be done by okaara
                for doc in document_list:
                    for key in doc['metadata'].keys():
                        if key not in FIELDS_MSI:
                            del doc['metadata'][key]

            self.context.prompt.render_document_list(
                document_list, filters=filter, order=order)

        _content_command(self.context, [TYPE_MSI], out_func=out_func, **kwargs)

# -- utility ------------------------------------------------------------------

def _content_command(context, type_ids, out_func=None, **kwargs):
    """
    This is a generic command that will perform a search for any type or
    types of content.

    :param type_ids:    list of type IDs that the command should operate on
    :type  type_ids:    list, tuple

    :param out_func:    optional callable to be used in place of
                        prompt.render_document. must accept one dict
    :type  out_func:    callable

    :param kwargs:  CLI options as input by the user and passed in by okaara
    :type  kwargs:  dict
    """
    out_func = out_func or context.prompt.render_document_list

    repo_id = kwargs.pop('repo-id')
    kwargs['type_ids'] = type_ids
    units = context.server.repo_unit.search(repo_id, **kwargs).response_body

    if not kwargs.get(DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword):
        units = [u['metadata'] for u in units]

    out_func(units)
