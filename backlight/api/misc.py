"""Miscellaneous functions."""

from collections import namedtuple
from contextlib import suppress

from backlight.api.exceptions import DoesNotExist, DoesNotSupportAPI
from backlight.api.i2c import I2C_CARDS, syshash, I2CBacklight
from backlight.api.linux import LinuxBacklight
from backlight.api.xrandr import Xrandr


__all__ = ['load', 'autoload', 'brightness']


Backlight = namedtuple('Backlight', ('percent', 'method'))


def load(name):
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
