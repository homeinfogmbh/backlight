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
"""Backlight setting via xrandr."""

from contextlib import suppress
from os import environ
from subprocess import check_output

from backlight.api.exceptions import NoOutputFound


__all__ = ['Xrandr']


XRANDR = '/usr/bin/xrandr'


def _xrandr(display, verbose=False, output=None, brightness=None):
    """Runs the respective xrandr command."""

    command = [XRANDR]

    if verbose:
        command.append('--verbose')

    if output is not None:
        command.append('--output')
        command.append(output)

    if brightness is not None:
        command.append('--brightness')
        command.append(brightness)

    with Display(display):
        return check_output(command).decode()


def _get_output(display):
    """Determines the active output."""

    for line in _xrandr(display).split('\n'):
        if 'connected' in line:
            output, state, _ = line.split(maxsplit=2)
            if state == 'connected':
                return output

    raise NoOutputFound()


def _get_brightness(display):
    """Determines the active output."""

    active_output = _get_output(display)
    output = None

    for line in _xrandr(display, verbose=True).split('\n'):
        if line.startswith(' '):
            key, value = line.split(':', maxsplit=1)
            key = key.strip()
            value = value.strip()

            if key == 'Brightness' and output == active_output:
                return (output, float(value))
        else:
            with suppress(ValueError):
                output, _ = line.split(maxsplit=1)

    return None


class Display(int):
    """Context manager for setting and un-setting
    DISPLAY environment variable.
    """

    def __str__(self):
        return f':{int(self)}'

    def __enter__(self):
        environ['DISPLAY'] = str(self)

    def __exit__(self, *_):
        del environ['DISPLAY']


class Xrandr:
    """Backlight client using xrandr."""

    def __init__(self, display=0):
        """Sets the display to use."""
        self.display = display

    @property
    def raw(self):
        """Returns the raw value."""
        return _get_brightness(self.display) or 0   # Compensate for None.

    @raw.setter
    def raw(self, value):
        """Sets the raw value."""
        output = _get_output(self.display)
        _xrandr(self.display, output=output, brightness=str(value))

    @property
    def percent(self):
        """Returns the brightness in percent."""
        return round(self.raw * 100)

    @percent.setter
    def percent(self, percent):
        """Sets the brightness in percent."""
        self.raw = percent / 100
