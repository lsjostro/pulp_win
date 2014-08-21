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
import sys

from pulp.bindings.exceptions import BadRequestException
from pulp.client import parsers
from pulp.client.commands.unit import UnitCopyCommand
from pulp.client.extensions.extensions import PulpCliOption

from pulp_win.common import ids, constants
from pulp_win.common.ids import TYPE_ID_MSI

# -- constants ----------------------------------------------------------------

DESC_MSI = _('copy MSIs from one repository to another')

# -- commands -----------------------------------------------------------------

class MsiCopyCommand(UnitCopyCommand):

    def __init__(self, context):
        self.context = context
        def msi_copy(**kwargs):
            # let's not load ALL of the metadata, as that could take a tremendous
            # amount of RAM
            kwargs['fields'] = ids.UNIT_KEY_MSI
            return _copy(self.context, TYPE_ID_MSI, **kwargs)
        super(MsiCopyCommand, self).__init__(msi_copy, name='msi', description=DESC_MSI)



def _copy(context, type_id, **kwargs):
    """
    This is a generic command that will perform a search for any type of
    content and copy it from one repository to another

    :param type_id: type of unit being copied
    :type  type_id: str

    :param kwargs:  CLI options as input by the user and passed in by
                    okaara. These are search options defined elsewhere that
                    also
    :type  kwargs:  dict
    """
    from_repo = kwargs['from-repo-id']
    to_repo = kwargs['to-repo-id']
    kwargs['type_ids'] = [type_id]

    # If rejected an exception will bubble up and be handled by middleware.
    # The only caveat is if the source repo ID is invalid, it will come back
    # from the server as source_repo_id. The client-side name for this value
    # is from-repo-id, so do a quick substitution in the exception and then
    # reraise it for the middleware to handle like normal.
    try:
        response = context.server.repo_unit.copy(from_repo, to_repo, **kwargs)
    except BadRequestException, e:
        if 'source_repo_id' in e.extra_data.get('property_names', []):
            e.extra_data['property_names'].remove('source_repo_id')
            e.extra_data['property_names'].append('from-repo-id')
        raise e, None, sys.exc_info()[2]

    progress_msg = _('Progress on this task can be viewed using the '
                     'commands under "repo tasks".')

    if response.response_body.is_postponed():
        d = _('Unit copy postponed due to another operation on the destination '
              'repository.')
        d += progress_msg
        context.prompt.render_paragraph(d)
        context.prompt.render_reasons(response.response_body.reasons)
    else:
        context.prompt.render_paragraph(progress_msg)
