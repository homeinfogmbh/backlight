#! /usr/bin/env python3

from distutils.core import setup

setup(
    name='backlight',
    version='latest',
    author='HOMEINFO - Digitale Informationssysteme GmbH',
    author_email='<info at homeinfo dot de>',
    maintainer='Richard Neumann',
    maintainer_email='<r dot neumann at homeinfo priod de>',
    license='GPLv3',
    packages=['backlight'],
    scripts=['files/backlight', 'files/backlightd'],
    data_files=[('/usr/share/licenses/backlight/', ['LICENSE'])],
    description='A screen backlight API and daemon.')
