#!/usr/bin/env python
from setuptools import setup, find_packages

NAME = 'pyphamas'
VERSION = '0.1.dev'

setup(
    name=NAME,
    version=VERSION,
    description='Python tools for analysing PHAMAS backend data',
    author='Gopal Narayanan <gopal@astro.umass.edu>',
    packages=find_packages(),
    scripts = ['bin/byu_slave',
               'bin/x64reinitialize',
               ],
    )

