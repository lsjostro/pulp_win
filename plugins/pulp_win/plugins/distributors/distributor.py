import logging
import os

from pulp.plugins.distributor import Distributor
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp_win.common.ids import TYPE_ID_MSI, TYPE_ID_EXE

_LOG = logging.getLogger(__name__)
HTTP_PUBLISH_DIR = "/var/www/pulp_win/http/repos"

def entry_point():
    return WinDistributor, {}

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
        publish_conduit.set_progress('Publishing modules')

        progress_status = {
            "packages":           {"state": "NOT_STARTED"},
            "publish_http":       {"state": "NOT_STARTED"},
            "publish_https":      {"state": "NOT_STARTED"},
        }

        def progress_callback(type_id, status):
            progress_status[type_id] = status
            publish_conduit.set_progress(progress_status)

        pkg_errors = []
        summary = {}
        details = {}

        search = UnitAssociationCriteria(type_ids=[TYPE_ID_MSI, TYPE_ID_EXE])
        pkg_units = publish_conduit.get_source_units(criteria=search)

        packages_progress_status = self.init_progress()
        self.set_progress("packages", packages_progress_status, progress_callback)
        packages_progress_status["items_total"] = len(pkg_units)
        packages_progress_status["items_left"] =  len(pkg_units)

        for u in pkg_units:
            if config.get('http') is not None:
                self.set_progress("publish_http", {"state" : "IN_PROGRESS"}, progress_callback)
                filename = os.path.basename(u.storage_path)
                http_publish_file = os.path.join(self.get_http_publish_dir(config), repo.id, filename)
                # Create symlink from module.storage_path to HTTP-enabled directory
                if not self.create_symlink(u.storage_path, http_publish_file):
                    packages_progress_status["num_error"] += 1
                    _LOG.error("Failed to create symlink: %s -> %s" % (u.storage_path, http_publish_file))
                    pkg_errors += u
                else:
                    packages_progress_status["num_success"] += 1
                packages_progress_status["items_left"] -= 1
                #publish_conduit.set_progress('Unit published')
        packages_progress_status["state"] = "FINISHED"
        self.set_progress("packages", packages_progress_status, progress_callback)
        self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
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
        return True

    def get_http_publish_dir(self, config=None):
        if config:
            publish_dir = config.get("http_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTP publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTP_PUBLISH_DIR

    def init_progress(self):
        return  {
            "state": "IN_PROGRESS",
            "num_success" : 0,
            "num_error" : 0,
            "items_left" : 0,
            "items_total" : 0,
            "error_details" : [],
        }

    def set_progress(self, type_id, status, progress_callback=None):
        if progress_callback:
            progress_callback(type_id, status)
