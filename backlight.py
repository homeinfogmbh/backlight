#! /usr/bin/env python3
"""A linux screen backlight API and daemon.

This module supports getting and setting of the backlight brightness
of graphics cards unter '/sys/class/backlight/<graphics_card>/',
provided they implement both files 'brightness' and 'max_brightness'
in the respective folder.
"""
from datetime import datetime
from json import load
from os import listdir
from os.path import exists, join
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


def error(*msgs):
    """Logs error messages."""

    print(*msgs, file=stderr, flush=True)


def log(*msgs):
    """Logs informational messages."""

    print(*msgs, flush=True)


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

    for timestamp, brightness in config.items():
        try:
            time = datetime.strptime(timestamp, TIME_FORMAT).time()
        except ValueError:
            error('Skipping invalid timestamp: {}.'.format(timestamp))
        else:
            yield (time, brightness)


def get_latest_brightness(config, now=None):
    """Returns the last config entry from the provided configuration."""

    now = now or datetime.now().time()
    latest = (None, None)

    for time, brightness in config.items():
        if time <= now:
            if latest[0] is None or latest[0] < time:
                latest = (time, brightness)

    return latest[1]


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
        """Tries all specified graphics cards.

        If none are specified, tries all graphics
        cards within BACKLIGHT_BASEDIR.
        """
        if not graphics_cards:
            graphics_cards = listdir(BACKLIGHT_BASEDIR)

        for self.graphics_card in graphics_cards:
            if all(exists(file) for file in self._files):
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
        self.config_file = config_file
        self.reset = reset
        self.tick = tick
        self.backlight = Backlight()
        self.config = dict(parse_config(load_config(config_file)))
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
        if percent != self._current_brightness:
            try:
                self._current_brightness = self.backlight.percent = percent
            except ValueError:
                error('Invalid brightness: {}.'.format(percent))
            else:
                log('Set brightness to {}%.'.format(percent))

    def run(self):
        """Runs the daemon."""
        log('Starting up...')
        log('Tick is {} second(s).'.format(self.tick))
        log('Detected graphics card: {}.'.format(self.backlight.graphics_card))
        initial_brightness = self.backlight.percent
        log('Initial brightness is {}%.'.format(initial_brightness))

        while True:
            brightness = get_latest_brightness(self.config)

            if brightness is not None:
                self.brightness = brightness

            try:
                sleep(self.tick)
            except KeyboardInterrupt:
                break

        if self.reset:
            self.brightness = initial_brightness
            log('Reset brightness to {}%.'.format(initial_brightness))

        log('Terminating...')
        return True


if __name__ == '__main__':
    exit(backlightd())
