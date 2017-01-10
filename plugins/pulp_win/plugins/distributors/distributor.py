import errno
import itertools
import logging
import os
import shutil

from gettext import gettext as _
from pulp.plugins.util import misc
from pulp.plugins.util.publish_step import AtomicDirectoryPublishStep
from pulp.plugins.util.publish_step import PluginStep, UnitModelPluginStep
from pulp.plugins.distributor import Distributor
from pulp_win.common import ids, constants
from pulp_win.plugins.db import models
from . import configuration

# Unfortunately, we need to reach into pulp_rpm in order to generate repomd
from pulp_rpm.plugins.distributors.yum.metadata.repomd import RepomdXMLFileContext  # noqa
from pulp_rpm.plugins.distributors.yum.metadata.primary import PrimaryXMLFileContext  # noqa


_LOG = logging.getLogger(__name__)


def entry_point():
    return WinDistributor, {}


class WinDistributor(Distributor):
    @classmethod
    def metadata(cls):
        return {
            'id': ids.TYPE_ID_DISTRIBUTOR_WIN,
            'display_name': 'Windows Distributor',
            'types': sorted(ids.SUPPORTED_TYPES)
        }

    def validate_config(self, repo, config, config_conduit):
        return configuration.validate_config(repo, config, config_conduit)

    def publish_repo(self, repo, conduit, config):
        publisher = Publisher(
            repo=repo, conduit=conduit,
            config=config, plugin_type=ids.TYPE_ID_DISTRIBUTOR_WIN)
        return publisher.process_lifecycle()

    def distributor_removed(self, repo, config):
        repo_dir = configuration.get_master_publish_dir(
            repo, ids.TYPE_ID_DISTRIBUTOR_WIN)
        shutil.rmtree(repo_dir, ignore_errors=True)
        # remove the symlinks that might have been created for this
        # repo/distributor
        rel_path = configuration.get_repo_relative_path(repo, config)
        rel_path = rel_path.rstrip(os.sep)
        pub_dirs = [
            configuration.get_http_publish_dir(config),
            configuration.get_https_publish_dir(config),
        ]
        for pub_dir in pub_dirs:
            symlink = os.path.join(pub_dir, rel_path)
            try:
                os.unlink(symlink)
            except OSError as error:
                if error.errno != errno.ENOENT:
                    raise


class Publisher(PluginStep):
    description = _("Publishing windows artifacts")

    def __init__(self, repo, conduit, config,
                 plugin_type, **kwargs):
        super(Publisher, self).__init__(step_type=constants.PUBLISH_REPO_STEP,
                                        repo=repo,
                                        conduit=conduit,
                                        config=config,
                                        plugin_type=plugin_type)

        self.add_child(ModulePublisher(conduit=conduit,
                       config=config, repo=repo))
        master_publish_dir = configuration.get_master_publish_dir(
            repo, plugin_type)
        target_directories = []
        if config.get(constants.PUBLISH_HTTP_KEYWORD):
            target_directories.append(
                configuration.get_http_publish_dir(config))
        if config.get(constants.PUBLISH_HTTPS_KEYWORD):
            target_directories.append(
                configuration.get_https_publish_dir(config))
        repo_path = configuration.get_repo_relative_path(repo, config)
        target_directories = [('/', os.path.join(x, repo_path))
                              for x in target_directories]
        atomic_publish_step = AtomicDirectoryPublishStep(
            self.get_working_dir(),
            target_directories,
            master_publish_dir)
        self.add_child(atomic_publish_step)
        self.description = self.__class__.description


class RepomdStep(PluginStep):
    def __init__(self):
        super(RepomdStep, self).__init__(constants.PUBLISH_REPOMD)

    def process_main(self, unit=None):
        wd = self.get_working_dir()
        total = len(self.parent.publish_msi.units +
                    self.parent.publish_msm.units)
        checksum_type = 'sha256'
        with PrimaryXMLFileContext(wd, total, checksum_type) as primary:
            units = itertools.chain(self.parent.publish_msi.units,
                                    self.parent.publish_msm.units)
            for unit in units:
                primary.add_unit_metadata(unit)

        with RepomdXMLFileContext(wd, checksum_type) as repomd:
            repomd.add_metadata_file_metadata('primary',
                                              primary.metadata_file_path,
                                              primary.checksum)


class _PublishStep(UnitModelPluginStep):
    ID_PUBLISH_STEP = None
    Model = None

    def __init__(self, work_dir, **kwargs):
        super(_PublishStep, self).__init__(
            self.ID_PUBLISH_STEP, [self.Model], **kwargs)
        self.working_dir = work_dir
        self.units = []
        self.units_latest = dict()

    def process_main(self, item=None):
        unit = item
        self.units.append(unit)
        dest_path = os.path.join(self.get_working_dir(), unit.filename)
        misc.create_symlink(unit.storage_path, dest_path)


class PublishMSIStep(_PublishStep):
    ID_PUBLISH_STEP = constants.PUBLISH_MSI_STEP
    Model = models.MSI


class PublishMSMStep(_PublishStep):
    ID_PUBLISH_STEP = constants.PUBLISH_MSM_STEP
    Model = models.MSM


class ModulePublisher(PluginStep):
    description = _("Publishing modules")

    def __init__(self, **kwargs):
        kwargs.setdefault('step_type', constants.PUBLISH_MODULES_STEP)
        super(ModulePublisher, self).__init__(**kwargs)
        self.description = self.__class__.description
        work_dir = self.get_working_dir()
        self.publish_msi = PublishMSIStep(work_dir)
        self.publish_msm = PublishMSMStep(work_dir)
        self.add_child(self.publish_msi)
        self.add_child(self.publish_msm)
        self.add_child(RepomdStep())

        if self.non_halting_exceptions is None:
            self.non_halting_exceptions = []

    def _get_total(self):
        return len(self.publish_msi.units) + len(self.publish_msm.units)
