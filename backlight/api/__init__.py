"""Backlight API."""

from contextlib import suppress
from typing import Union

from backlight.api.i2c import I2C_CARDS, syshash, ChrontelCH7511B, I2CBacklight
from backlight.api.linux import LinuxBacklight
from backlight.api.xrandr import Xrandr
from backlight.exceptions import DoesNotExist, DoesNotSupportAPI
from backlight.types import Backlight


__all__ = [
    'I2C_CARDS',
    'load',
    'autoload',
    'brightness',
    'ChrontelCH7511B',
    'GraphicsCard',
    'I2CBacklight'
]


GraphicsCard = Union[I2CBacklight, LinuxBacklight, Xrandr]


def load(name: str = None) -> GraphicsCard:
    """Loads the backlight by the respective names."""

    if name is None:
        try:
            return I2C_CARDS[syshash()]()
        except (KeyError, DoesNotExist):
            return LinuxBacklight.any()

    return LinuxBacklight(name)


def autoload(search: bool = False) -> GraphicsCard:
    """Automatically loads a fitting graphics card."""

    with suppress(DoesNotExist, DoesNotSupportAPI):
        return LinuxBacklight('acpi_video0')

    with suppress(KeyError, DoesNotExist):
        return I2C_CARDS[syshash()]()

    if search:
        return LinuxBacklight.any()

    return Xrandr()


def brightness(percent: int) -> Backlight:
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
