# This file is part of backlight.
#
# backlight is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# backlight is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with backlight.  If not, see <http://www.gnu.org/licenses/>.
"""Backlight API."""

from backlight.api.datastructures import IntegerDifferential
from backlight.api.exceptions import DoesNotExist
from backlight.api.exceptions import DoesNotSupportAPI
from backlight.api.exceptions import NoSupportedGraphicsCards
from backlight.api.i2c import I2C_CARDS, I2CBacklight, ChrontelCH7511B
from backlight.api.linux import LinuxBacklight
from backlight.api.misc import load, autoload, brightness


__all__ = [
    'I2C_CARDS',
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoSupportedGraphicsCards',
    'load',
    'autoload',
    'brightness',
    'IntegerDifferential',
    'I2CBacklight',
    'ChrontelCH7511B',
    'LinuxBacklight'
]
