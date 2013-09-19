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

import os
from gettext import gettext as _

from pulp.client.commands.repo import cudl, sync_publish, upload
from pulp.client.commands.repo.query import RepoSearchCommand
from pulp.client.upload import manager as upload_lib

from pulp_win.extension.admin import (contents, copy, remove, repo,
                                      status, structure)
from pulp_win.common import constants, ids
from pulp_win.extension.admin.upload import package

def initialize(context):
    structure.ensure_repo_structure(context.cli)
    upload_manager = _upload_manager(context)

    repo_section = structure.repo_section(context.cli)
    repo_section.add_command(repo.MsiRepoCreateCommand(context))
    repo_section.add_command(repo.MsiRepoUpdateCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(repo.MsiRepoListCommand(context))
    repo_section.add_command(RepoSearchCommand(context, constants.REPO_NOTE_WIN))

    #copy_section = structure.repo_copy_section(context.cli)
    #copy_section.add_command(copy.MsiCopyCommand(context))

    remove_section = structure.repo_remove_section(context.cli)
    remove_section.add_command(remove.MsiRemoveCommand(context))

    contents_section = structure.repo_contents_section(context.cli)
    contents_section.add_command(contents.SearchMsisCommand(context))

    uploads_section = structure.repo_uploads_section(context.cli)
    uploads_section.add_command(package.CreateMsiCommand(context, upload_manager))
    uploads_section.add_command(upload.ResumeCommand(context, upload_manager))
    uploads_section.add_command(upload.CancelCommand(context, upload_manager))
    uploads_section.add_command(upload.ListCommand(context, upload_manager))

    publish_section = structure.repo_publish_section(context.cli)
    renderer = status.MsiStatusRenderer(context)
    distributor_id = ids.TYPE_ID_DISTRIBUTOR_WIN
    publish_section.add_command(sync_publish.RunPublishRepositoryCommand(context, renderer, distributor_id))
    publish_section.add_command(sync_publish.PublishStatusCommand(context, renderer))

def _upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    :return: initialized and ready to run upload manager instance
    :rtype: UploadManager
    """
    upload_working_dir = context.config['filesystem']['upload_working_dir']
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['server']['upload_chunk_size'])
    upload_manager = upload_lib.UploadManager(upload_working_dir, context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
