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
Contains functionality related to rendering the progress report for a the MSI
plugins (both the sync and publish operations).
"""

from gettext import gettext as _

from pulp.client.commands.repo.sync_publish import StatusRenderer

from pulp_win.common import constants
from pulp_win.common.status_utils import render_general_spinner_step, render_itemized_in_progress_state

class MsiStatusRenderer(StatusRenderer):

    def __init__(self, context):
        super(MsiStatusRenderer, self).__init__(context)

        # Publish Steps
        self.packages_last_state = constants.STATE_NOT_STARTED
        self.publish_http_last_state = constants.STATE_NOT_STARTED
        self.publish_https_last_state = constants.STATE_NOT_STARTED

        self.packages_bar = self.prompt.create_progress_bar()
        self.publish_http_spinner = self.prompt.create_spinner()
        self.publish_https_spinner = self.prompt.create_spinner()

    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.
        """

        # There's a small race condition where the task will indicate it's
        # begun running but the importer has yet to submit a progress report
        # (or it has yet to be saved into the task). This should be alleviated
        # by the if statements below.

        # Publish Steps
        if 'win_distributor' in progress_report:
            self.render_packages_step(progress_report)
            self.render_publish_https_step(progress_report)
            self.render_publish_http_step(progress_report)

    def render_packages_step(self, progress_report):

        # Example Data:
        # "packages": {
        #    "num_success": 21,
        #    "items_left": 0,
        #    "items_total": 21,
        #    "state": "FINISHED",
        #    "error_details": [],
        #    "num_error": 0
        # },
        data = progress_report['win_distributor']['packages']
        state = data['state']

        if state in (constants.STATE_NOT_STARTED, constants.STATE_SKIPPED):
            return

        # Only render this on the first non-not-started state
        if self.packages_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Publishing packages...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.packages_last_state not in constants.COMPLETE_STATES:

            self.packages_last_state = state
            render_itemized_in_progress_state(self.prompt, data, _('packages'), self.packages_bar, state)

        elif state == constants.STATE_FAILED and self.packages_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.packages_last_state = constants.STATE_FAILED

    def render_publish_http_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['win_distributor']['publish_http']['state']
        def update_func(new_state):
            self.publish_http_last_state = new_state
        render_general_spinner_step(self.prompt, self.publish_http_spinner, current_state, self.publish_http_last_state, _('Publishing repository over HTTP'), update_func)

    def render_publish_https_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['win_distributor']['publish_https']['state']
        def update_func(new_state):
            self.publish_https_last_state = new_state
        render_general_spinner_step(self.prompt, self.publish_https_spinner, current_state, self.publish_https_last_state, _('Publishing repository over HTTPS'), update_func)

