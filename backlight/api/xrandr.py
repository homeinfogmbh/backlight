"""Backlight setting via xrandr."""

from os import environ
from subprocess import check_output

from backlight.api.exceptions import NoOutputFound


__all__ = ['Xrandr']


XRANDR = '/usr/bin/xrandr'


def _xrandr(display, *options):
    """Runs the respective xrandr command."""

    with Display(display):
        return check_output((XRANDR,) + options).decode()


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

    for line in _xrandr(display, '--verbose').split('\n'):
        if line.startswith(' '):
            key, value = line.split(maxsplit=1)

            if key == 'Brightness:' and output == active_output:
                return (output, float(value))
        else:
            output, *_ = line.split(maxsplit=1)

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
        _xrandr(
            self.display, '--output', _get_output(self.display),
            '--brightness', str(value))

    @property
    def percent(self):
        """Returns the brightness in percent."""
        return round(self.raw * 100)

    @percent.setter
    def percent(self, percent):
        """Sets the brightness in percent."""
        self.raw = percent / 100
