"""Backlight API."""

from backlight.api.exceptions import DoesNotExist, DoesNotSupportAPI, \
    NoSupportedGraphicsCards
from backlight.api.i2c import I2C_CARDS, I2CBacklight, ChrontelCH7511B
from backlight.api.linux import LinuxBacklight


__all__ = [
    'I2C_CARDS',
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoSupportedGraphicsCards',
    'load',
    'I2CBacklight',
    'ChrontelCH7511B',
    'LinuxBacklight']


def load(name):
    """Loads the backlight by the respective names."""

    if name is None:
        return LinuxBacklight.any()

    try:
        return I2C_CARDS[name]
    except KeyError:
        return LinuxBacklight(name)
