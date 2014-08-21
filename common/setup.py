from setuptools import setup, find_packages

setup(
    name='pulp_win_common',
    version='2.4.0',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Lars Sjostrom',
    author_email='lars@radicore.se'
)
