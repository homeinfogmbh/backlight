#! /usr/bin/env python3
"""Install script."""

from setuptools import setup

setup(
    name='backlight',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author='HOMEINFO - Digitale Informationssysteme GmbH',
    author_email='<info at homeinfo dot de>',
    maintainer='Richard Neumann',
    maintainer_email='<r dot neumann at homeinfo priod de>',
    license='GPLv3',
    packages=['backlight', 'backlight.api'],
    entry_points={
        'console_scripts': [
            'backlight = backlight.cli:spawn',
            'backlightd = backlight.daemon:main'
        ]
    },
    description='A screen backlight API and daemon.'
)
