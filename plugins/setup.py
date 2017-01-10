#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pulp_win_plugins',
    version='2.4.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Lars Sjostrom',
    author_email='lars.sjostrom@svenskaspel.se',
    entry_points={
        'pulp.importers': [
            'importer = pulp_win.plugins.importers.importer:entry_point',
        ],
        'pulp.distributors': [
            'distributor = pulp_win.plugins.distributors.distributor:entry_point',  # noqa
        ],
        'pulp.server.db.migrations': [
            'pulp_win = pulp_win.plugins.migrations',
        ],
        'pulp.unit_models': [
            'msi=pulp_win.plugins.db.models:MSI',
            'msm=pulp_win.plugins.db.models:MSM',
        ],
    },
    include_package_data=True,
    data_files=[
        ('/etc/httpd/conf.d', ['etc/httpd/conf.d/pulp_win.conf']),
        ('/usr/lib/pulp/plugins/types', ['types/win.json']),
    ],
    install_requires=[
    ],
)
