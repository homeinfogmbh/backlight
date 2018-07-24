"""Dimming via i2c."""

from subprocess import check_call, check_output


__all__ = ['i2cget', 'i2cset', 'I2CBacklight', 'ChrontelCH7511B']


I2CGET = '/usr/bin/i2cget'
I2CSET = '/usr/bin/i2cset'


def i2cget(i2c_bus, chip_address, data_address=None, mode=None):
    """Wrapper for i2cget."""

    command = [I2CGET, '-y', str(i2c_bus), str(chip_address)]

    if data_address is not None:
        command.append(str(data_address))

        if mode is not None:
            command.append(str(mode))

    return int(check_output(command).decode().strip(), 16)


def i2cset(i2c_bus, chip_address, data_address, *values, mode=None):
    """Wrapper for i2cget."""

    command = [
        I2CSET, '-y', str(i2c_bus), str(chip_address), str(data_address)]

    if values:
        for value in values:
            command.append(str(value))

        if mode is not None:
            command.append(str(mode))

    return check_call(command)


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
            next_percentage = round(percentage + percent_step)
            self[raw_value] = range(percentage, next_percentage)
            percentage = next_percentage

    def from_percent(self, percentage):
        """Returns the raw value for the given percentage."""
        for raw, percent in self.items():
            if percentage in percent:
                return raw

        raise KeyError(percentage)


class I2CBacklight:
    """Dimming by I2C / SMBUS."""

    def __init__(self, i2c_bus, chip_address, offset, values):
        """Sets the respective I2C configuration."""
        self.i2c_bus = i2c_bus
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
        return i2cget(self.i2c_bus, self.chip_address, self.offset)

    @raw.setter
    def raw(self, value):
        """Sets the raw value."""
        if value in self.values:
            return i2cset(self.i2c_bus, self.chip_address, self.offset, value)

        raise ValueError(value)

    value = raw

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


class ChrontelCH7511B(I2CBacklight):
    """Backlight API for Chrontel CH7511B."""

    VALUES = PercentageMap(range(1, 18), range(30, 100))

    def __init__(self, i2c_bus=0):
        """Initializes the Chrontel CH7511B client."""
        super().__init__(i2c_bus, 0x21, 0x6E, self.__class__.VALUES)
        # Initialize duty cycle for PWM1.
        i2cset(self.i2c_bus, self.chip_address, 0x7F, 0xED)
