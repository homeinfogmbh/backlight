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
"""Miscellaneous functions."""

from collections import namedtuple
from contextlib import suppress

from backlight.api.exceptions import DoesNotExist, DoesNotSupportAPI
from backlight.api.i2c import I2C_CARDS, syshash, I2CBacklight
from backlight.api.linux import LinuxBacklight
from backlight.api.xrandr import Xrandr


__all__ = ['load', 'autoload', 'brightness']


Backlight = namedtuple('Backlight', ('percent', 'method'))


def load(name=None):
    """Loads the backlight by the respective names."""

    if name is None:
        try:
            return I2C_CARDS[syshash()]
        except KeyError:
            return LinuxBacklight.any()

    return LinuxBacklight(name)


def autoload(search=False):
    """Automatically loads a fitting graphics card."""

    with suppress(DoesNotExist, DoesNotSupportAPI):
        return LinuxBacklight('acpi_video0')

    with suppress(KeyError, DoesNotExist):
        return I2C_CARDS[syshash()]()

    if search:
        return LinuxBacklight.any()

    return Xrandr()


def brightness(percent):
    """Set backlight in percent."""

    backlight = autoload()

    try:
        backlight.percent = percent
    except ValueError:
        # Compensate for possible minimal value.
        backlight.raw = min(backlight.values)

    if isinstance(backlight, LinuxBacklight):
        method = 'Linux'
    elif isinstance(backlight, I2CBacklight):
        method = 'I2C / SMBus'
    else:
        method = 'xrandr'

    return Backlight(backlight.percent, method)
