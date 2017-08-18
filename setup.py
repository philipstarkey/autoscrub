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


VERSION = '0.1.3'
# Auto generate a __version__ package for the package to import
with open(os.path.join('autoscrub', '__version__.py'), 'w') as f:
    f.write("__version__ = '%s'\n" % VERSION)

setup(
    name='autoscrub',
    version=VERSION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        autoscrub=autoscrub.scripts.cli:cli
    ''',
)