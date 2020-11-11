"""Backlight setting via xrandr."""

from contextlib import suppress
from os import environ
from subprocess import check_output

from backlight.exceptions import NoOutputFound


__all__ = ['Xrandr']


XRANDR = '/usr/bin/xrandr'


def _xrandr(display: int, verbose: bool = False, output: str = None,
            brightness: int = None) -> str:
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
        return check_output(command, text=True)


def _get_output(display: int) -> str:
    """Determines the active output."""

    for line in _xrandr(display).split('\n'):
        if 'connected' in line:
            output, state, *_ = line.split()

            if state == 'connected':
                return output

    raise NoOutputFound()


def _get_brightness(display: int) -> float:
    """Determines the active output."""

    active_output = _get_output(display)
    output = None

    for line in _xrandr(display, verbose=True).split('\n'):
        if output == active_output and line.startswith('\t'):
            try:
                key, value = line.split(':', maxsplit=1)
            except ValueError:
                continue

            if key.strip() == 'Brightness':
                return float(value.strip())
        else:
            with suppress(ValueError):
                output, _ = line.split(maxsplit=1)

    return None


class Display(int):
    """Context manager for setting and un-setting
    DISPLAY environment variable.
    """

    def __init__(self, *_):
        """Sets the previous display."""
        super().__init__()
        self._previous = None

    def __str__(self):
        """Returns a colon, followed by the display ID."""
        return f':{int(self)}'

    def __enter__(self):
        """Stores the previously set display and sets the
        DISPLAY environment variable to the current display.
        """
        self._previous, environ['DISPLAY'] = environ.get('DISPLAY'), str(self)

    def __exit__(self, *_):
        """Resets the DISPLAY environment variable."""
        if self._previous is None:
            del environ['DISPLAY']
        else:
            environ['DISPLAY'] = self._previous


class Xrandr:
    """Backlight client using xrandr."""

    def __init__(self, display: int = 0):
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
