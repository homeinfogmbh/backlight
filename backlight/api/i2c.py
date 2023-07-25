"""Dimming via i2c."""

from hashlib import sha1
from subprocess import check_output

from smbus import SMBus  # pylint: disable=E0611

from backlight.exceptions import DoesNotExist
from backlight.types import PercentageMap


__all__ = ["syshash", "PercentageMap", "I2CBacklight", "ChrontelCH7511B", "I2C_CARDS"]


CHRONTEL_CH7511B_VALUES = PercentageMap(range(1, 18), range(30, 101))


def syshash() -> str:
    """Returns hashed PCI and CPU data."""

    hasher = sha1()
    lspci = check_output("/usr/bin/lspci")
    hasher.update(lspci)
    cpu_model = check_output(("/usr/bin/grep", "model", "/proc/cpuinfo"))
    hasher.update(cpu_model)
    return hasher.hexdigest()


class I2CBacklight:
    """Dimming by I2C / SMBUS."""

    def __init__(self, bus: int, address: int, offset: int, values: PercentageMap):
        """Sets the respective I2C configuration."""
        try:
            self.smbus = SMBus(bus)
        except FileNotFoundError:
            raise DoesNotExist() from None

        self.address = address
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
            raise ValueError(f"Invalid percentage: {percent}.")

    def _read(self, address: int) -> int:
        """Reads the respective address."""
        return self.smbus.read_i2c_block_data(self.address, address, 1)[0]

    def _write(self, address: int, value: int):
        """Reads the respective address."""
        return self.smbus.write_i2c_block_data(self.address, address, [value])


class ChrontelCH7511B(I2CBacklight):
    """Backlight API for Chrontel CH7511B."""

    def __init__(self, bus=0):
        """Initializes the Chrontel CH7511B client."""
        super().__init__(bus, 0x21, 0x6E, CHRONTEL_CH7511B_VALUES)
        self._write(0x7F, 0xED)  # Initialize duty cycle for PWM1.


I2C_CARDS = {"53af5eabb6e32c257237ff18b3f047e9fa5e42fd": ChrontelCH7511B}
