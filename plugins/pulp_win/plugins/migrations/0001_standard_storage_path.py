import logging

from pulp.server.db import connection

from pulp.plugins.migration.standard_storage_path import Migration, Plan


_logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Migrate content units to use the standard storage path introduced in pulp
    2.8.
    """
    msg = ('* NOTE: This migration may take a long time depending on the size '
           'of your Pulp content *')
    stars = '*' * len(msg)

    _logger.info(stars)
    _logger.info(msg)
    _logger.info(stars)

    migration = Migration()
    migration.add(msi_plan())
    migration.add(msm_plan())
    migration()


def msi_plan():
    collection = connection.get_collection('units_msi')
    key_fields = ("name", "version", "checksumtype", "checksum")
    return Plan(collection, key_fields)


def msm_plan():
    collection = connection.get_collection('units_msm')
    key_fields = ("name", "version", "checksumtype", "checksum")
    return Plan(collection, key_fields)
