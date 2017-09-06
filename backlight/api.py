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
# along with pydialog.  If not, see <http://www.gnu.org/licenses/>.
"""This module provides an API to retrieve and set the backlight
brightness of screens."

Therefor it reads information from device files in
'/sys/class/backlight/<graphics_card>/', provided they implement
the files 'brightness', 'actual_brightness' and 'max_brightness'
in the respective folder.
"""
from contextlib import suppress
from os import listdir
from os.path import exists, isfile, join


__all__ = [
    'BASEDIR',
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoSupportedGraphicsCards',
    'Backlight']


BASEDIR = '/sys/class/backlight'


class DoesNotExist(Exception):
    """Indicates that the respective graphics card does not exist."""

    pass


class DoesNotSupportAPI(Exception):
    """Indicates that the respective graphics
    card does not implement this API.
    """

    pass


class NoSupportedGraphicsCards(Exception):
    """Indicates that the available graphics cards are not supported."""

    pass


class Backlight():
    """Backlight handler for graphics cards."""

    def __init__(self, graphics_card):
        """Sets the respective graphics card."""
        self._graphics_card = graphics_card

        if not exists(self._path):
            raise DoesNotExist()

        if not all(isfile(file) for file in self._files):
            raise DoesNotSupportAPI()

    def __str__(self):
        """Returns the respective graphics card's name."""
        return self._graphics_card

    @classmethod
    def load(cls, graphics_cards=None):
        """Loads the backlight from the respective graphics cards.

        If no graphics cards have been defined, seek BASEDIR for
        available graphics card and return backlight for the first
        graphics card that implements the API.
        """
        if not graphics_cards:
            graphics_cards = listdir(BASEDIR)

        for graphics_card in graphics_cards:
            with suppress(DoesNotExist, DoesNotSupportAPI):
                return cls(str(graphics_card))

        raise NoSupportedGraphicsCards() from None

    @property
    def _path(self):
        """Returns the absolute path to the
        graphics card's device folder.
        """
        return join(BASEDIR, self._graphics_card)

    @property
    def _max_file(self):
        """Returns the path of the maximum brightness file."""
        return join(self._path, 'max_brightness')

    @property
    def _setter_file(self):
        """Returns the path of the backlight file."""
        return join(self._path, 'brightness')

    @property
    def _getter_file(self):
        """Returns the file to read the current brightness from."""
        return join(self._path, 'actual_brightness')

    @property
    def _files(self):
        """Yields the graphics cards API's files."""
        return (self._max_file, self._setter_file, self._getter_file)

    @property
    def max(self):
        """Returns the maximum brightness as integer."""
        with open(self._max_file, 'r') as file:
            return int(file.read().strip())

    @property
    def raw(self):
        """Returns the raw brightness."""
        with open(self._getter_file, 'r') as file:
            return file.read().strip()

    @raw.setter
    def raw(self, brightness):
        """Sets the raw brightness."""
        with open(self._setter_file, 'w') as file:
            file.write('{}\n'.format(brightness))

    @property
    def value(self):
        """Returns the raw brightness as integer."""
        return int(self.raw)

    @value.setter
    def value(self, brightness):
        """Sets the raw brightness from an integer."""
        self.raw = str(brightness)

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        return self.value * 100 // self.max

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.value = self.max * percent // 100
        else:
            raise ValueError('Invalid percentage: {}.'.format(percent))
