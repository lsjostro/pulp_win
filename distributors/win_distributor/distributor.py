import logging
import os

from pulp.plugins.distributor import Distributor
from pulp.plugins.conduits.mixins import UnitAssociationCriteria

_LOG = logging.getLogger(__name__)
HTTP_PUBLISH_DIR = "/var/www/pulp_win/http/repos"

class WinDistributor(Distributor):
    @classmethod
    def metadata(cls):
        return {
            'id' : 'win_distributor',
            'display_name' : 'Windows Distributor',
            'types' : ['msi','exe'],
        }
    def validate_config(self, repo, config, related_repos):
        if config.get('serve-http') is None and config.get('serve-https') is None:
            return False, 'At least one of "serve-http" or "serve-https" must be specified'
        return True, None

    def publish_repo(self, repo, publish_conduit, config):
        publish_conduit.set_progress('Publishing modules')
        pkg_units = []
        pkg_errors = []
        summary = {}
        details = {}

        for type_id in ['msi','exe']:
            criteria = UnitAssociationCriteria(type_id,
                       unit_fields=['id', 'name', 'version', 'filename', '_storage_path', "checksum", "checksumtype" ])
            pkg_units += publish_conduit.get_units(criteria=criteria)

        for u in pkg_units:
            if config.get('serve-http') == "true":
                http_publish_file = os.path.join(self.get_http_publish_dir(config), repo.id, u.unit_key['filename'])
                # Create symlink from module.storage_path to HTTP-enabled directory
                if not self.create_symlink(u.storage_path, http_publish_file):
                    _LOG.error("Failed to create symlink")
                    pkg_errors += u
                publish_conduit.set_progress('Unit published')
        summary["num_package_units_attempted"] = len(pkg_units)
        summary["num_package_units_published"] = len(pkg_units) - len(pkg_errors)
        summary["num_package_units_errors"] = len(pkg_errors)
        details["errors"] = pkg_errors
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (summary, details))
        if details["errors"]:
            return publish_conduit.build_failure_report(summary, details)
        return publish_conduit.build_success_report(summary, details)

    def create_symlink(self, source_path, symlink_path):
        if symlink_path.endswith("/"):
            symlink_path = symlink_path[:-1]
        if os.path.lexists(symlink_path):
            if not os.path.islink(symlink_path):
                _LOG.error("%s is not a symbolic link as expected." % (symlink_path))
                return False
            existing_link_target = os.readlink(symlink_path)
            if existing_link_target == source_path:
                return True
            _LOG.warning("Removing <%s> since it was pointing to <%s> and not <%s>"\
            % (symlink_path, existing_link_target, source_path))
            os.unlink(symlink_path)
            # Account for when the relativepath consists of subdirectories
        if not self.create_dirs(os.path.dirname(symlink_path)):
            return False
        _LOG.debug("creating symlink %s pointing to %s" % (symlink_path, source_path))
        os.symlink(source_path, symlink_path)
        return True

    def create_dirs(self, target):
        if not os.path.exists(target):
            try:
                os.makedirs(target)
                return True
            except OSError, e:
                _LOG.error("Failed to create directory: %s" % e)
                return False

    def get_http_publish_dir(self, config=None):
        if config:
            publish_dir = config.get("http_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTP publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTP_PUBLISH_DIR
