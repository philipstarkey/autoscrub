# Copyright 2017 Russell Anderson, Philip Starkey
#
# This file is part of autoscrub.
#
# autoscrub is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# autoscrub is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with autoscrub.  If not, see <http://www.gnu.org/licenses/>.

import os
from setuptools import setup, find_packages


VERSION = '0.7.0'
# Auto generate a __version__ package for the package to import
with open(os.path.join('autoscrub', '__version__.py'), 'w') as f:
    f.write("__version__ = '%s'\n" % VERSION)

setup(
    name='autoscrub',
    version=VERSION,
    description='Hastens silent intervals of videos using FFmpeg',
    url='https://bitbucket.org/philipstarkey/autoscrub',
    license='GPLv3',
    author='Russell Anderson, Philip Starkey',
    classifiers=['Development Status :: 4 - Beta',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Environment :: Console',
                 'Intended Audience :: Education',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Natural Language :: English',
                ],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'six',
        'requests',
        'subprocess32;python_version<"3.2"',
    ],
    entry_points='''
        [console_scripts]
        autoscrub=autoscrub.scripts.cli:cli
    ''',
)