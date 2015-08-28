import errno
import logging
import os

from gettext import gettext as _
from pulp.plugins.util.publish_step import PublishStep
from pulp.plugins.distributor import Distributor
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp_win.common import ids, constants

_LOG = logging.getLogger(__name__)
HTTP_PUBLISH_DIR = "/var/www/pub/win/http/repos"

def entry_point():
    return WinDistributor, {}

class SymlinkError(Exception):
    pass

class WinDistributor(Distributor):
    @classmethod
    def metadata(cls):
        return {
            'id' : 'win_distributor',
            'display_name' : 'Windows Distributor',
            'types' : ['msi','exe'],
        }
    def validate_config(self, repo, config, config_conduit):
        if config.get('http') is None and config.get('https') is None:
            return False, 'At least one of "serve-http" or "serve-https" must be specified'
        return True, None

    def publish_repo(self, repo, publish_conduit, config):
        publisher = Publisher(repo=repo, publish_conduit=publish_conduit,
                config=config, distributor_type=ids.TYPE_ID_DISTRIBUTOR_WIN)
        return publisher.publish()

class Publisher(PublishStep):
    description = _("Publishing windows artifacts")
    def __init__(self, *args, **kwargs):
        super(Publisher, self).__init__(step_type=constants.PUBLISH_REPO_STEP,
                *args, **kwargs)
        self.add_child(ModulePublisher(publish_conduit=self.get_conduit(),
            config=self.get_config(), repo=self.get_repo()))
        self.description = self.__class__.description

class ModulePublisher(PublishStep):
    description = _("Publishing modules")

    def __init__(self, **kwargs):
        kwargs.setdefault('step_type', constants.PUBLISH_MODULES_STEP)
        super(ModulePublisher, self).__init__(**kwargs)
        self.description = self.__class__.description
        self._symlinks = set()
        self._items = None

    def get_iterator(self):
        if self._items is not None:
            return self._items
        search = UnitAssociationCriteria(type_ids=[ids.TYPE_ID_MSI, ids.TYPE_ID_EXE])
        conduit = self.get_conduit()
        self._items = conduit.get_units(criteria=search)
        return self._items

    def _get_total(self):
        return len(self.get_iterator())

    def process_main(self, item=None):
        if item is None:
            return
        _LOG.debug("Processing %s", item)
        config = self.get_config()
        if config.get('http') is not None:
            publish_file = self.get_publish_file(item)
            # Create symlink from module.storage_path to HTTP-enabled directory
            self._create_symlink(item.storage_path, publish_file)
            self._symlinks.add(publish_file)
        self.progress_details = "Published %s=%s" % (item.unit_key['name'], item.unit_key['version'])

    def post_process(self):
        _LOG.debug("Post-processing")
        # Make sure we remove extra files
        repo_dir = self.get_repo_dir()
        try:
            dir_contents = os.listdir(repo_dir)
        except OSError, e:
            if e.errno != errno.ENOENT:
                # "No such file or directory" if the repo is empty and its
                # directory hasn't been created
                raise
        for f in dir_contents:
            fpath = os.path.join(repo_dir, f)
            if os.path.isdir(fpath):
                continue
            if fpath not in self._symlinks:
                os.unlink(fpath)

    def get_http_publish_dir(self, config=None):
        if config:
            publish_dir = config.get("http_publish_dir")
            if publish_dir:
                _LOG.debug("Override HTTP publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTP_PUBLISH_DIR

    def get_repo_dir(self):
        config = self.get_config()
        return os.path.join(self.get_http_publish_dir(config),
                self.get_repo().id, constants.CONFIG_REPO_SUBDIR)

    def get_publish_file(self, item):
        return os.path.join(self.get_repo_dir(), os.path.basename(item.storage_path))
