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
        """Returns the maximum value."""
        return self.values[-1]

    @property
    def raw(self):
        """Returns the raw set value."""
        return i2cget(
            self.i2c_bus, self.chip_address, data_address=self.offset)

    @raw.setter
    def raw(self, value):
        """Sets the raw value."""
        if value in self.values:
            return i2cset(
                self.i2c_bus, self.chip_address, self.offset, value)

        raise ValueError(value)

    value = raw

    @property
    def factor(self):
        """Percentage factor."""
        return 100 / (len(self.values) - 1)

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        return round(self.raw * self.factor)

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.raw = round(percent * self.max / 100)
        else:
            raise ValueError(f'Invalid percentage: {percent}.')


class ChrontelCH7511B(I2CBacklight):
    """Backlight API for Chrontel CH7511B."""

    def __init__(self, i2c_bus=0):
        """Initializes the Chrontel CH7511B client."""
        super().__init__(i2c_bus, 0x21, 0x6E, range(18))
        # Initialize duty cycle for PWM1.
        i2cset(self.i2c_bus, self.chip_address, 0x7F, 0xED)
