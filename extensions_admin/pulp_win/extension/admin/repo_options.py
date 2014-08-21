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

"""
Contains option definitions for MSI repository configuration and update, pulled
out of the repo commands module itself to keep it from becoming unwieldy.
"""

from gettext import gettext as _

from pulp.client import parsers
from pulp.client.commands import options as std_options
from pulp.client.extensions.extensions import PulpCliOption, PulpCliOptionGroup

from pulp_win.common import ids

# -- data ---------------------------------------------------------------------

# Used to validate user entered skip types
VALID_SKIP_TYPES = [ids.TYPE_ID_MSI]

# -- validators ---------------------------------------------------------------

def parse_skip_types(t):
    """
    The user-entered value is comma separated and will be the full list of
    types to skip; there is no concept of a diff.

    :param t: user entered value or None
    """
    if t is None:
        return

    parsed = t.split(',')
    parsed = [p.strip() for p in parsed]

    unmatched = [p for p in parsed if p not in VALID_SKIP_TYPES]
    if len(unmatched) > 0:
        msg = _('Types must be a comma-separated list using only the following values: %(t)s')
        msg = msg % {'t' : ', '.join(VALID_SKIP_TYPES)}
        raise ValueError(msg)

    return parsed

# -- group names --------------------------------------------------------------

NAME_BASIC = _('Basic')
NAME_PUBLISHING = _('Publishing')

ALL_GROUP_NAMES = (NAME_BASIC, NAME_PUBLISHING)

# -- publish options ----------------------------------------------------------

d = _('if "true", on each successful sync the repository will automatically be '
      'published on the configured protocols; if "false" synchronized content '
      'will only be available after manually publishing the repository; '
      'defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False, parse_func=parsers.parse_boolean)

d = _('relative path the repository will be served from. Only alphanumeric characters, forward slashes, underscores '
      'and dashes are allowed. It defaults to the relative path of the feed URL')
OPT_RELATIVE_URL = PulpCliOption('--relative-url', d, required=False)

d = _('if "true", the repository will be served over HTTP; defaults to false')
OPT_SERVE_HTTP = PulpCliOption('--serve-http', d, required=False, parse_func=parsers.parse_boolean)

d = _('if "true", the repository will be served over HTTPS; defaults to true')
OPT_SERVE_HTTPS = PulpCliOption('--serve-https', d, required=False, parse_func=parsers.parse_boolean)

d = _('type of checksum to use during metadata generation')
OPT_CHECKSUM_TYPE = PulpCliOption('--checksum-type', d, required=False)

# -- public methods -----------------------------------------------------------

def add_to_command(command):
    """
    Adds the repository configuration related options to the given command,
    organizing them into the appropriate groups.

    :param command: command to add options to
    :type  command: pulp.clients.extensions.extensions.PulpCliCommand
    """

    # Groups
    basic_group = PulpCliOptionGroup(NAME_BASIC)
    publish_group = PulpCliOptionGroup(NAME_PUBLISHING)

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(basic_group)
    command.add_option_group(publish_group)

    # Metadata Options - Reorganized using standard commands
    basic_group.add_option(std_options.OPTION_REPO_ID)
    basic_group.add_option(std_options.OPTION_NAME)
    basic_group.add_option(std_options.OPTION_DESCRIPTION)
    basic_group.add_option(std_options.OPTION_NOTES)

    # Publish Options
    publish_group.add_option(OPT_RELATIVE_URL)
    publish_group.add_option(OPT_SERVE_HTTP)
    publish_group.add_option(OPT_SERVE_HTTPS)
    publish_group.add_option(OPT_CHECKSUM_TYPE)
