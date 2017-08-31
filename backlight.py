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
from os.path import exists, isfile, join
from sys import stderr
from time import sleep

try:
    from docopt import docopt
except ImportError:
    print('WARNING: "docopt" not installed. Daemon unavailable.',
          file=stderr, flush=True)


__all__ = [
    'DEFAULT_CONFIG',
    'BASEDIR',
    'NoSupportedGraphicsCards',
    'GraphicsCard',
    'Daemon']


TIME_FORMAT = '%H:%M'
DEFAULT_CONFIG = '/etc/backlight.json'
BASEDIR = '/sys/class/backlight'
DAEMON_USAGE = '''backlightd

A screen backlight daemon.

Usage:
    backlightd [<graphics_card>...] [options]

Options:
    --config=<config_file>, -c  Sets the JSON configuration file.
    --tick=<seconds>, -t        Sets the daemon's interval [default: 1].
    --reset, -r                 Reset the brightness before terminating.
    --help                      Shows this page.
'''


class DoesNotExist(Exception):
    """Indicates that the respective graphics card does not exist."""

    pass


class DoesNotSupportAPI(Exception):
    """Indicates that the respective graphics
    card does not implement this API.
    """

    pass


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


def strip_time(timestamp):
    """Returns the time with hours and minutes only."""

    return time(hour=timestamp.hour, minute=timestamp.minute)


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


def get_latest(config):
    """Returns the last config entry from the provided configuration."""

    now = strip_time(datetime.now().time())
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
    graphics_cards = options['<graphics_card>']
    config_file = options['--config'] or DEFAULT_CONFIG
    tick = int(options['--tick'])
    reset = options['--reset']

    try:
        daemon = Daemon(graphics_cards, config_file, reset=reset, tick=tick)
    except NoSupportedGraphicsCards:
        error('No supported graphics cards found.')
        return 3
    else:
        if daemon.run():
            return 0

        return 1


class GraphicsCard():
    """Graphics card API."""

    def __init__(self, name):
        """Sets the graphics card's name."""
        self.name = name

        if not exists(self.device_path):
            raise DoesNotExist()

        if not all(isfile(file) for file in self.files):
            raise DoesNotSupportAPI()

    @property
    def device_path(self):
        """Returns the absolute path to the
        graphics card's device folder.
        """
        return join(BASEDIR, self.name)

    @property
    def max_brightness_file(self):
        """Returns the path of the maximum brightness file."""
        return join(self.device_path, 'max_brightness')

    @property
    def brightness_file(self):
        """Returns the path of the backlight file."""
        return join(self.device_path, 'brightness')

    @property
    def files(self):
        """Yields the graphics cards API's files."""
        yield self.max_brightness_file
        yield self.brightness_file

    @property
    def max_brightness(self):
        """Returns the raw maximum brightness."""
        return int(read_brightness(self.max_brightness_file))

    @property
    def brightness(self):
        """Returns the brightness' absolute value."""
        return int(read_brightness(self.brightness_file))

    @brightness.setter
    def brightness(self, brightness):
        """Sets the brightness' absolute value."""
        write_brightness(self.brightness_file, brightness)

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

    def __init__(self, graphics_cards, config_file, reset=False, tick=1):
        """Tries the specified graphics cards until
        a working one is found.

        If none are specified, tries all graphics cards
        within BASEDIR until a working one is found.
        """
        if not graphics_cards:
            graphics_cards = listdir(BASEDIR)

        for graphics_card in graphics_cards:
            try:
                self.graphics_card = GraphicsCard(graphics_card)
            except DoesNotExist:
                error('Graphics card "{}" does not exist.'.format(
                    graphics_card))
            except DoesNotSupportAPI:
                error('Graphics card "{}" does not support API.'.format(
                    graphics_card))
            else:
                break
        else:
            raise NoSupportedGraphicsCards() from None

        self.config = dict(parse_config(load_config(config_file)))
        self.reset = reset
        self.tick = tick
        self._initial_brightness = self.graphics_card.percent
        self._last_timestamp = None

    @property
    def brightness(self):
        """Returns the current brightness."""
        return self.graphics_card.percent

    @brightness.setter
    def brightness(self, percent):
        """Sets the current brightness."""
        try:
            self.graphics_card.percent = percent
        except ValueError:
            error('Invalid brightness: {}.'.format(percent))
        else:
            log('Set brightness to {}%.'.format(percent))

    def _startup(self):
        """Starts up the daemon."""
        log('Starting up...')
        log('Tick is {} second(s).'.format(self.tick))
        log('Detected graphics card: {}.'.format(self.graphics_card.name))
        log('Initial brightness is {}%.'.format(self._initial_brightness))

        try:
            self._last_timestamp, self.brightness = get_latest(self.config)
        except NoLatestEntry:
            error('Latest entry could not be determined.')
            error('Falling back to 100%.')
            self.brightness = 100
        else:
            log('Loaded latest setting from {}.'.format(
                self._last_timestamp.strftime(TIME_FORMAT)))

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
            now = strip_time(datetime.now().time())

            if now != self._last_timestamp:
                with suppress(KeyError):
                    self.brightness = self.config[now]

                self._last_timestamp = now

            try:
                sleep(self.tick)
            except KeyboardInterrupt:
                break

        return self._shutdown()


if __name__ == '__main__':
    exit(backlightd())
