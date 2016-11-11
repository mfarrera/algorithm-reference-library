#!/usr/bin/env python

from setuptools import setup
import os

setup(name='crocodile',
      version='0.5',
      description='Algorithm Reference Library for Radio Interferometry',
      long_description=open('README.md').read(),
      author='Tim Cornwell, Peter Wortmann, Bojan Nikolic',
      author_email='realtimcornwell@gmail.com',
      url='https://github.com/SKA-ScienceDataProcessor/crocodile',
      license='Apache License Version 2.0',
      packages=['arl', 'examples', 'tests'],
      test_suite="tests",
      tests_require=['pytest'],
      )
