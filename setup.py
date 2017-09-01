#! /usr/bin/env python3

from distutils.core import setup

setup(
    name='backlight',
    version='latest',
    author='HOMEINFO - Digitale Informationssysteme GmbH',
    packages=['backlight'],
    data_files=[
        ('/usr/bin/', ('files/backlight', 'files/backlightd')),
        ('/usr/share/licenses/backlight/', ['LICENSE'])],
    description='A screen backlight API and daemon.')
