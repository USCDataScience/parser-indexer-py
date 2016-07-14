#!/usr/bin/env python
# encoding: utf-8

import os.path

try:
    from ez_setup import use_setuptools
    use_setuptools()
except ImportError:
    pass

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

version = '1.0'

_descr = '''
Python port of Parser-Indexer
'''
_keywords = 'parser, indexer, content detection, tika, lucene, solr'
_classifiers = [
    'Development Status :: 1 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: Information Technology',
    'Intended Audience :: Science/Research',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Database :: Front-Ends',
    'Topic :: Scientific/Engineering',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = _descr

setup(
    name='parser-indexer',
    version=version,
    description='Parser-Indexer',
    long_description=long_description,
    classifiers=_classifiers,
    keywords=_keywords,
    author='',
    author_email='',
    url='',
    download_url='',
    license=read('LICENSE.txt'),
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=True,
    test_suite='',
    entry_points={
        'console_scripts': [],
    },
    package_data = {
        # And include any *.conf files found in the 'conf' subdirectory
        # for the package
    },
    install_requires=[
        'setuptools'
    ],
    extras_require={
    },
)