"""Dimming via i2c."""

from smbus import SMBus

from backlight.api import DoesNotExist


__all__ = ['I2CBacklight', 'ChrontelCH7511B']


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
        super().__init__(i2c_bus, 0x21, 0x6E, self.__class__.VALUES)
        # Initialize duty cycle for PWM1.
        self._write(0x7F, 0xED)
