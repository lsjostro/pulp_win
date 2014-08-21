#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pulp_win_plugins',
    version='2.4.0',
    license='GPLv2+',
    packages=find_packages(),
    author='Lars Sjostrom',
    author_email='lars.sjostrom@svenskaspel.se',
    entry_points={
        'pulp.importers': [
            'importer = pulp_win.plugins.importers.importer:entry_point',
        ],
        'pulp.distributors': [
            'distributor = pulp_win.plugins.distributors.distributor:entry_point',
        ]
    }
)
