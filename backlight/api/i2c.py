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
"""Dimming via i2c."""

from hashlib import sha1
from subprocess import check_output

from smbus import SMBus     # pylint: disable=E0611

from backlight.api.exceptions import DoesNotExist


__all__ = [
    'syshash',
    'PercentageMap',
    'I2CBacklight',
    'ChrontelCH7511B',
    'I2C_CARDS']


def syshash():
    """Returns hashed PCI and CPU data."""

    hasher = sha1()
    lspci = check_output('/usr/bin/lspci')
    hasher.update(lspci)
    cpu_model = check_output(('/usr/bin/grep', 'model', '/proc/cpuinfo'))
    hasher.update(cpu_model)
    return hasher.hexdigest()


class PercentageMap(dict):
    """Range of brightness raw and percentage values."""

    __slots__ = ()

    def __init__(self, raw, percent=range(0, 101)):
        """Sets raw and percentage ranges."""
        super().__init__()
        raw_span = max(raw) - min(raw)
        percent_span = max(percent) - min(percent)
        percent_step = percent_span / raw_span
        percentage = min(percent)

        for raw_value in raw:
            next_percentage = percentage + percent_step
            self[raw_value] = range(round(percentage), round(next_percentage))
            percentage = next_percentage

    def from_percent(self, percentage):
        """Returns the raw value for the given percentage."""
        for raw, percent in self.items():
            if percentage in percent:
                return raw

        raise ValueError(percentage)


class I2CBacklight:
    """Dimming by I2C / SMBUS."""

    def __init__(self, i2c_bus, chip_address, offset, values):
        """Sets the respective I2C configuration."""
        try:
            self.smbus = SMBus(i2c_bus)
        except FileNotFoundError:
            raise DoesNotExist()

        self.chip_address = chip_address
        self.offset = offset
        self.values = values

    @property
    def max(self):
        """Returns the maximum raw value."""
        return max(self.values)

    @property
    def raw(self):
        """Returns the raw set value."""
        return self._read(self.offset)

    @raw.setter
    def raw(self, value):
        """Sets the raw value."""
        if value in self.values:
            return self._write(self.offset, value)

        raise ValueError(value)

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        range_ = self.values[self.raw]
        return sum(range_) / len(range_)

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.raw = self.values.from_percent(percent)
        else:
            raise ValueError(f'Invalid percentage: {percent}.')

    def _read(self, address):
        """Reads the respective address."""
        return self.smbus.read_i2c_block_data(
            self.chip_address, address, 1)[0]

    def _write(self, address, value):
        """Reads the respective address."""
        return self.smbus.write_i2c_block_data(
            self.chip_address, address, [value])


class ChrontelCH7511B(I2CBacklight):
    """Backlight API for Chrontel CH7511B."""

    VALUES = PercentageMap(range(1, 18), range(30, 101))

    def __init__(self, i2c_bus=0):
        """Initializes the Chrontel CH7511B client."""
        super().__init__(i2c_bus, 0x21, 0x6E, type(self).VALUES)
        self._write(0x7F, 0xED)     # Initialize duty cycle for PWM1.


I2C_CARDS = {'53af5eabb6e32c257237ff18b3f047e9fa5e42fd': ChrontelCH7511B}
