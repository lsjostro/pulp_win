# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# -- progress states ----------------------------------------------------------

STATE_NOT_STARTED = 'NOT_STARTED'
STATE_RUNNING = 'IN_PROGRESS'
STATE_COMPLETE = 'FINISHED'
STATE_FAILED = 'FAILED'
STATE_SKIPPED = 'SKIPPED'

COMPLETE_STATES = (STATE_COMPLETE, STATE_FAILED, STATE_SKIPPED)

REPO_NOTE_WIN = 'win-repo'

# Importer configuration key names
CONFIG_COPY_CHILDREN                = 'copy_children'
CONFIG_MAX_SPEED                    = 'max_speed'
CONFIG_NUM_THREADS                  = 'num_threads'
CONFIG_NUM_THREADS_DEFAULT          = 5
CONFIG_REMOVE_MISSING_UNITS         = 'remove_missing_units'
CONFIG_REMOVE_MISSING_UNITS_DEFAULT = False

# Distributor configuration key names
CONFIG_SERVE_HTTP      = 'serve_http'
CONFIG_SERVE_HTTPS     = 'serve_https'

# Profiler configuration key name
#CONFIG_APPLICABILITY_REPORT_STYLE = 'report_style'
#APPLICABILITY_REPORT_STYLE_BY_UNITS = 'by_units'
#APPLICABILITY_REPORT_STYLE_BY_CONSUMERS = 'by_consumers'
