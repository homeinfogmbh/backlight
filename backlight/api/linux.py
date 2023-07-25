"""This module provides an API to retrieve and set the backlight
brightness of screens."

Therefor it reads information from device files in
'/sys/class/backlight/<graphics_card>/', provided they implement
the files 'brightness', 'actual_brightness' and 'max_brightness'
in the respective folder.
"""
from __future__ import annotations
from contextlib import suppress
from pathlib import Path
from typing import Iterator

from backlight.exceptions import DoesNotExist
from backlight.exceptions import DoesNotSupportAPI
from backlight.exceptions import NoSupportedGraphicsCards


__all__ = ["LinuxBacklight"]


BASEDIR = Path("/sys/class/backlight")


class LinuxBacklight:
    """Backlight handler for graphics cards."""

    def __init__(self, graphics_card: str, *, omit_actual: bool = False):
        """Sets the respective graphics card."""
        self._graphics_card = graphics_card
        self.omit_actual = omit_actual

        if not self._path.exists():
            raise DoesNotExist()

        if not all(file.is_file() for file in self._files):
            raise DoesNotSupportAPI()

    def __str__(self):
        """Returns the respective graphics card's name."""
        return self._graphics_card

    @classmethod
    def all(cls, *, omit_actual: bool = False) -> Iterator[LinuxBacklight]:
        """Seeks BASEDIR for available graphics card and yields them."""
        for graphics_card in BASEDIR.iterdir():
            with suppress(DoesNotExist, DoesNotSupportAPI):
                yield cls(str(graphics_card), omit_actual=omit_actual)

    @classmethod
    def any(cls, *, omit_actual: bool = False) -> LinuxBacklight:
        """Seeks BASEDIR for available graphics card and returns
        backlight for the first graphics card that implements the API.
        """
        for linux_backlight in cls.all(omit_actual=omit_actual):
            return linux_backlight

        raise NoSupportedGraphicsCards()

    @property
    def _path(self):
        """Returns the absolute path to the
        graphics card's device folder.
        """
        return BASEDIR.joinpath(self._graphics_card)

    @property
    def _max_file(self):
        """Returns the path of the maximum brightness file."""
        return self._path.joinpath("max_brightness")

    @property
    def _setter_file(self):
        """Returns the path of the backlight file."""
        return self._path.joinpath("brightness")

    @property
    def _getter_file(self):
        """Returns the file to read the current brightness from."""
        if self.omit_actual:
            return self._setter_file

        return self._path.joinpath("actual_brightness")

    @property
    def _files(self):
        """Yields the graphics cards API's files."""
        return (self._max_file, self._setter_file, self._getter_file)

    @property
    def max(self):
        """Returns the maximum brightness as integer."""
        with self._max_file.open("r") as file:
            return int(file.read().strip())

    @property
    def raw(self):
        """Returns the raw brightness."""
        with self._getter_file.open("r") as file:
            return int(file.read().strip())

    @raw.setter
    def raw(self, brightness):
        """Sets the raw brightness."""
        with self._setter_file.open("w") as file:
            file.write(f"{brightness}\n")

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        return self.raw * 100 // self.max

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.raw = self.max * percent // 100
        else:
            raise ValueError(f"Invalid percentage: {percent}.")
