#! /usr/bin/env python3

from distutils.core import setup

setup(
    name='backlight',
    version='latest',
    author='HOMEINFO - Digitale Informationssysteme GmbH',
    py_modules=['backlight'],
    data_files=[('/usr/bin/', ('backlight', 'backlightd'))],
    description='A screen backlight API and daemon.')
