#!/usr/bin/python
# coding=utf-8

from setuptools import setup, find_packages

setup(
    name = 'watchgit',
    version = '0.2.0',
    install_requires = ['python-daemon>=1.6', 'GitPython>=0.3.1'],
    description = 'Keep local git repositories in sync',
    author = 'Taylan Develioglu',
    author_email = 'taylan.develioglu@gmail.com',
    scripts=['watchgit.py'],
    data_files=[('/etc', ['watchgit.conf'])],
)
