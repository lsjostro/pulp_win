from setuptools import setup, find_packages

setup(
    name='pulp_win_extensions_admin',
    version='2.4.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Lars Sjostrom',
    author_email='lars@radicore.se',
    entry_points={
        'pulp.extensions.admin': [
            'win_repo_admin = pulp_win.extensions.admin.rpm_repo.pulp_cli:initialize',
        ]
    }
)
