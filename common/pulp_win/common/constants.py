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

REPO_NOTE_PKG = 'win-repo'

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

DEFAULT_SERVE_HTTP = False
DEFAULT_SERVE_HTTPS = True

# Copy operation config
CONFIG_RECURSIVE = 'recursive'
DISPLAY_UNITS_THRESHOLD = 100

# Profiler configuration key name
#CONFIG_APPLICABILITY_REPORT_STYLE = 'report_style'
#APPLICABILITY_REPORT_STYLE_BY_UNITS = 'by_units'
#APPLICABILITY_REPORT_STYLE_BY_CONSUMERS = 'by_consumers'

PUBLISH_REPO_STEP = 'publish_repo'
PUBLISH_MODULES_STEP = "publish_modules"
PUBLISH_MSI_STEP = "publish_msi"
PUBLISH_MSM_STEP = "publish_msm"
PUBLISH_REPOMD = "publish_repomd"

PUBLISH_STEPS = (PUBLISH_REPO_STEP, PUBLISH_MODULES_STEP,
                 PUBLISH_MSI_STEP, PUBLISH_MSM_STEP, PUBLISH_REPOMD)

REPO_NODE_PKG = 'win-repo'

# Configuration constants for export distributors
PUBLISH_HTTP_KEYWORD = 'http'
PUBLISH_HTTPS_KEYWORD = 'https'
PUBLISH_RELATIVE_URL_KEYWORD = 'relative_url'
