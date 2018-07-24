"""Miscellaneous functions."""

from contextlib import suppress

from backlight.api.exceptions import DoesNotExist, DoesNotSupportAPI, \
    NoSupportedGraphicsCards
from backlight.api.i2c import I2C_CARDS, syshash
from backlight.api.linux import LinuxBacklight


__all__ = ['load', 'autoload']


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

    raise NoSupportedGraphicsCards()
