# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.unit import UnitCopyCommand
from pulp.client.extensions.extensions import PulpCliFlag

from pulp_win.extensions.admin import units_display, criteria_utils
from pulp_win.common.constants import (DISPLAY_UNITS_THRESHOLD,
                                       CONFIG_RECURSIVE)
from pulp_win.common.ids import (TYPE_ID_MSI, TYPE_ID_MSM)


# -- constants ----------------------------------------------------------------

DESC_MSI = _('copy MSI units from one repository to another')
DESC_MSM = _('copy MSM from one repository to another')
DESC_ALL = _('copy all content units from one repository to another')

DESC_RECURSIVE = _(
    'if specified, any dependencies of units being copied that are in the source repo '  # noqa
    'will be copied as well')
FLAG_RECURSIVE = PulpCliFlag('--recursive', DESC_RECURSIVE)

# -- commands -----------------------------------------------------------------


class NonRecursiveCopyCommand(UnitCopyCommand):
    """
    Base class for all copy commands in this module that need not support
    specifying a recursive option to the plugin.
    """
    TYPE_ID = None
    DESCRIPTION = None
    NAME = None

    def __init__(self, context, unit_threshold=None):
        name = self.NAME or self.TYPE_ID
        if unit_threshold is None:
            unit_threshold = DISPLAY_UNITS_THRESHOLD
        super(NonRecursiveCopyCommand, self).__init__(
            context, name=name, description=self.DESCRIPTION,
            type_id=self.TYPE_ID)

        self.unit_threshold = unit_threshold

    def get_formatter_for_type(self, type_id):
        """
        Hook to get a the formatter for a given type

        :param type_id: the type id for which we need to get the formatter
        :type type_id: str
        """
        return units_display.get_formatter_for_type(type_id)


class RecursiveCopyCommand(NonRecursiveCopyCommand):
    """
    Base class for all copy commands in this module that should support
    specifying a recursive option to the plugin.
    """

    def __init__(self, context, unit_threshold=None):
        super(RecursiveCopyCommand, self).__init__(
            context,
            unit_threshold=unit_threshold)

        self.add_flag(FLAG_RECURSIVE)

    def generate_override_config(self, **kwargs):
        override_config = {}

        if kwargs[FLAG_RECURSIVE.keyword]:
            override_config[CONFIG_RECURSIVE] = True

        return override_config


class PackageCopyCommand(RecursiveCopyCommand):
    """
    Used for only RPMs and SRPMs to intercept the criteria and use sort
    indexes when necessary.
    """

    @staticmethod
    def _parse_key_value(args):
        return criteria_utils.parse_key_value(args)

    @classmethod
    def _parse_sort(cls, sort_args):
        return criteria_utils.parse_sort(RecursiveCopyCommand, sort_args)


class MsiCopyCommand(PackageCopyCommand):
    TYPE_ID = TYPE_ID_MSI
    DESCRIPTION = DESC_MSI


class MsmCopyCommand(PackageCopyCommand):
    TYPE_ID = TYPE_ID_MSM
    DESCRIPTION = DESC_MSM


class AllCopyCommand(NonRecursiveCopyCommand):
    TYPE_ID = None
    DESCRIPTION = DESC_ALL
    NAME = 'all'
