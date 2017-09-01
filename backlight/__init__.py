#  backlight
#
#  Copyright (C) 2017  HOMEINFO - Digitale Informationssysteme GmbH
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
"""A linux screen backlight API, cli program and daemon.

This module supports getting and setting of the backlight brightness
of graphics cards unter '/sys/class/backlight/<graphics_card>/',
provided they implement the files 'brightness', 'actual_brightness'
and 'max_brightness' in the respective folder.
"""
from .api import Backlight
from .cli import CLI
from .daemon import Daemon

__all__ = ['Backlight', 'CLI', 'Daemon']
