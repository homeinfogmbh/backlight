#! /usr/bin/env python3
"""A linux screen backlight API and daemon.

This module supports getting and setting of the backlight brightness
of graphics cards unter '/sys/class/backlight/<graphics_card>/',
provided they implement both files 'brightness' and 'max_brightness'
in the respective folder.
"""
from contextlib import suppress
from datetime import datetime, time
from json import load
from os import listdir
from os.path import isfile, join
from sys import stderr
from time import sleep

try:
    from docopt import docopt
except ImportError:
    print('WARNING: "docopt" not installed. Daemon unavailable.',
          file=stderr, flush=True)


__all__ = [
    'DEFAULT_CONFIG',
    'BACKLIGHT_BASEDIR',
    'NoSupportedGraphicsCards',
    'Backlight',
    'Daemon']


TIME_FORMAT = '%H:%M'
DEFAULT_CONFIG = '/etc/backlight.json'
BACKLIGHT_BASEDIR = '/sys/class/backlight'
DAEMON_USAGE = '''backlightd

A screen backlight daemon.

Usage:
    backlightd [options]

Options:
    --config=<config_file>, -c  Sets the configuration file.
    --tick=<seconds>, -t        Sets the daemon's interval [default: 1].
    --reset, -r                 Reset the brightness before terminating.
    --help                      Shows this page.
'''


class NoSupportedGraphicsCards(Exception):
    """Indicates that the available graphics cards are not supported."""

    pass


class NoLatestEntry(Exception):
    """Indicates that no latest entry could
    be determined from the configuration.
    """

    pass


def error(*msgs):
    """Logs error messages."""

    print(*msgs, file=stderr, flush=True)


def log(*msgs):
    """Logs informational messages."""

    print(*msgs, flush=True)


def current_time():
    """Returns the current time with hours and minutes only."""

    now = datetime.now().time()
    return time(hour=now.hour, minute=now.minute)


def read_brightness(path):
    """Reads the raw brightness from the respective file."""

    with open(path, 'r') as file:
        return file.read().strip()


def write_brightness(path, brightness):
    """Reads the raw brightness from the respective file."""

    with open(path, 'w') as file:
        return file.write('{}\n'.format(brightness))


def load_config(path):
    """Loads the configuration"""

    try:
        with open(path, 'r') as config_file:
            return load(config_file)
    except PermissionError:
        error('Cannot read config file: {}.'.format(path))
    except FileNotFoundError:
        error('Config file does not exist: {}.'.format(path))
    except ValueError:
        error('Config file has invalid content: {}.'.format(path))

    return {}


def parse_config(config):
    """Parses the configuration dictionary."""

    for timestamp_string, brightness in config.items():
        try:
            timestamp = datetime.strptime(timestamp_string, TIME_FORMAT).time()
        except ValueError:
            error('Skipping invalid timestamp: {}.'.format(timestamp_string))
        else:
            yield (timestamp, brightness)


def get_latest(config, now=None):
    """Returns the last config entry from the provided configuration."""

    now = now or current_time()
    sorted_values = sorted(config.items())
    latest = None

    for timestamp, brightness in sorted_values:
        if timestamp <= now:
            latest = (timestamp, brightness)
        else:
            # Since values are sorted by timestamp,
            # stop seeking if timstamp is in the future.
            break

    # Fall back to latest value (of previous day).
    if latest is None:
        try:
            return sorted_values[-1]
        except IndexError:
            raise NoLatestEntry() from None

    return latest


def backlightd():
    """backlight daemon function."""

    options = docopt(DAEMON_USAGE)
    config_file = options['--config'] or DEFAULT_CONFIG
    tick = int(options['--tick'])
    reset = options['--reset']

    try:
        daemon = Daemon(config_file, reset=reset, tick=tick)
    except NoSupportedGraphicsCards:
        error('No supported graphics cards found.')
        return 3
    else:
        if daemon.run():
            return 0

        return 1


class Backlight():
    """Backlight API handler."""

    def __init__(self, *graphics_cards):
        """Tries the specified graphics cards until
        a working one is found.

        If none are specified, tries all graphics cards within
        BACKLIGHT_BASEDIR until a working one is found.
        """
        if not graphics_cards:
            graphics_cards = listdir(BACKLIGHT_BASEDIR)

        for self.graphics_card in graphics_cards:
            if all(isfile(file) for file in self._files):
                break
        else:
            raise NoSupportedGraphicsCards() from None

        self._max_brightness = None

    @property
    def _device_path(self):
        """Returns the absolute path to the graphics card."""
        return join(BACKLIGHT_BASEDIR, self.graphics_card)

    @property
    def _max_brightness_file(self):
        """Returns the path of the maximum brightness file."""
        return join(self._device_path, 'max_brightness')

    @property
    def _brightness_file(self):
        """Returns the path of the backlight file."""
        return join(self._device_path, 'brightness')

    @property
    def _files(self):
        """Yields files of the graphics cards API."""
        yield self._max_brightness_file
        yield self._brightness_file

    @property
    def max_brightness(self):
        """Returns the raw maximum brightness."""
        if self._max_brightness is None:
            self._max_brightness = int(read_brightness(
                self._max_brightness_file))

        return self._max_brightness

    @property
    def brightness(self):
        """Returns the brightness' absolute value."""
        return int(read_brightness(self._brightness_file))

    @brightness.setter
    def brightness(self, brightness):
        """Sets the brightness' absolute value."""
        write_brightness(self._brightness_file, brightness)

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        return self.brightness * 100 // self.max_brightness

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.brightness = self.max_brightness * percent // 100
        else:
            raise ValueError('Invalid percentage: {}.'.format(percent))


class Daemon():
    """Backlight daemon."""

    def __init__(self, config_file, reset=False, tick=1):
        """Sets configuration file, reset flag and tick interval."""
        self.config = dict(parse_config(load_config(config_file)))
        self.reset = reset
        self.tick = tick
        self.backlight = Backlight()
        self._initial_brightness = self.backlight.percent
        self._current_brightness = None

    @property
    def brightness(self):
        """Returns the current brightness."""
        if self._current_brightness is None:
            self._current_brightness = self.backlight.percent

        return self._current_brightness

    @brightness.setter
    def brightness(self, percent):
        """Sets the current brightness."""
        try:
            self.backlight.percent = self._current_brightness = percent
        except ValueError:
            error('Invalid brightness: {}.'.format(percent))
        else:
            log('Set brightness to {}%.'.format(percent))

    def _startup(self):
        """Starts up the daemon."""
        log('Starting up...')
        log('Tick is {} second(s).'.format(self.tick))
        log('Detected graphics card: {}.'.format(self.backlight.graphics_card))
        log('Initial brightness is {}%.'.format(self._initial_brightness))

        try:
            timestamp, self.brightness = get_latest(self.config)
        except NoLatestEntry:
            error('Latest entry could not be determined.')
            error('Falling back to 100%.')
            self.brightness = 100
        else:
            log('Loaded latest setting from {}.'.format(
                timestamp.strftime(TIME_FORMAT)))

    def _shutdown(self):
        """Performs shutdown tasks."""
        if self.reset:
            log('Resetting brightness...')
            self.brightness = self._initial_brightness

        log('Terminating...')
        return True

    def run(self):
        """Runs the daemon."""
        self._startup()

        while True:
            with suppress(KeyError):
                self.brightness = self.config[current_time()]

            try:
                sleep(self.tick)
            except KeyboardInterrupt:
                break

        return self._shutdown()


if __name__ == '__main__':
    exit(backlightd())
