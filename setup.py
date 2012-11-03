#!/usr/bin/env python
import os
import re
from setuptools import setup

PACKAGE_NAME = 'lazysusan'

HERE = os.path.abspath(os.path.dirname(__file__))
INIT = open(os.path.join(HERE, PACKAGE_NAME, '__init__.py')).read()
README = open(os.path.join(HERE, 'README.md')).read()
VERSION = re.search("__version__ = '([^']+)'", INIT).group(1)


setup(name=PACKAGE_NAME,
      author='Bryce Boe',
      author_email='bbzbryce@gmail.com',
      classifiers=['Environment :: Console',
                   'License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Natural Language :: English',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Utilities'],
      description='LazySusan is a pluginable bot for turntable.fm.',
      entry_points={'console_scripts': ['lazysusan = lazysusan:main']},
      install_requires=['ttapi>=1.1.0'],
      keywords='turntable bot',
      license='Simplified BSD License',
      long_description=README,
      packages=[PACKAGE_NAME, 'lazysusan.plugins'],
      url='https://github.com/bboe/lazysusan',
      version=VERSION)
