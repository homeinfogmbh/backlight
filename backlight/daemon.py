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
"""A daemon to update the screen's backlight brightness
at given timestamps to the respective value.
"""
from contextlib import suppress
from datetime import datetime
from json import load
from time import sleep

from backlight.api import NoSupportedGraphicsCards, load_backlight
from backlight.cli import docopt, error, log


__all__ = [
    'TIME_FORMAT',
    'DEFAULT_CONFIG',
    'NoLatestEntry',
    'stripped_datetime',
    'load_config',
    'parse_config',
    'get_latest',
    'Daemon']


TIME_FORMAT = '%H:%M'
DEFAULT_CONFIG = '/etc/backlight.json'


class NoLatestEntry(Exception):
    """Indicates that no latest entry could
    be determined from the configuration.
    """

    pass


def stripped_datetime(date_time=None):
    """Gets current date time, exact to minute."""

    date_time = date_time or datetime.now()
    return datetime(
        year=date_time.year, month=date_time.month, day=date_time.day,
        hour=date_time.hour, minute=date_time.minute)


def load_config(path):
    """Loads the configuration"""

    try:
        with open(path, 'r') as config_file:
            return load(config_file)
    except PermissionError:
        error(f'Cannot read config file: {path}.')
    except FileNotFoundError:
        error(f'Config file does not exist: {path}.')
    except ValueError:
        error(f'Config file has invalid content: {path}.')

    return {}


def parse_config(config):
    """Parses the configuration dictionary."""

    for timestamp, brightness in config.items():
        try:
            timestamp = datetime.strptime(timestamp, TIME_FORMAT).time()
        except ValueError:
            error(f'Invalid timestamp "{timestamp}".')
            continue
        else:
            timestamp = timestamp.strftime(TIME_FORMAT)

        try:
            brightness = int(brightness)
        except (TypeError, ValueError):
            error(f'Invalid brightness "{brightness}" at {timestamp}.')
        else:
            if 0 <= brightness <= 100:
                yield (timestamp, brightness)
            else:
                error(f'Invalid percentage: {brightness} at {timestamp}.')


def get_latest(config):
    """Returns the last config entry from the provided configuration."""

    now = stripped_datetime().time()
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


class Daemon:
    """backlightd

A screen backlight daemon.

Usage:
    backlightd [<graphics_card>...] [options]

Options:
    --config=<config_file>, -c  Sets the JSON configuration file.
    --tick=<seconds>, -t        Sets the daemon's interval [default: 1].
    --reset, -r                 Reset the brightness before terminating.
    --help                      Shows this page.
"""

    def __init__(self, graphics_cards, config_file, reset=False, tick=1):
        """Tries the specified graphics cards until
        a working one is found.

        If none are specified, tries all graphics cards
        within BASEDIR until a working one is found.
        """
        self._backlight = load_backlight(graphics_cards)
        self.config = dict(parse_config(load_config(config_file)))
        self.reset = reset
        self.tick = tick
        self._initial_brightness = self.brightness
        self._last = None

    @classmethod
    def run(cls):
        """Runs as a daemon."""
        options = docopt(cls.__doc__)
        graphics_cards = options['<graphics_card>']
        config_file = options['--config'] or DEFAULT_CONFIG
        tick = int(options['--tick'])
        reset = options['--reset']

        try:
            daemon = Daemon(
                graphics_cards, config_file, reset=reset, tick=tick)
        except NoSupportedGraphicsCards:
            error('No supported graphics cards found.')
            return 3

        if daemon.spawn():
            return 0

        return 1

    @property
    def brightness(self):
        """Returns the current brightness."""
        return self._backlight.percent

    @brightness.setter
    def brightness(self, percent):
        """Sets the current brightness."""
        try:
            self._backlight.percent = percent
        except ValueError:
            error(f'Invalid brightness: {percent}.')
        except PermissionError:
            error('Cannot set brightness. Is this service running as root?')
        else:
            log(f'Set brightness to {percent}%.')

    def _startup(self):
        """Starts up the daemon."""
        log('Starting up...')
        log(f'Tick is {self.tick} second(s).')
        log(f'Detected graphics card: {self._backlight}.')
        log(f'Initial brightness is {self._initial_brightness}%.')

        try:
            timestamp, self.brightness = get_latest(self.config)
        except NoLatestEntry:
            error('Latest entry could not be determined.')
            error('Falling back to 100%.')
            self.brightness = 100
        else:
            timestamp = timestamp.strftime(TIME_FORMAT)
            log(f'Loaded latest setting from {timestamp}.')

    def _shutdown(self):
        """Performs shutdown tasks."""
        if self.reset:
            log('Resetting brightness...')
            self.brightness = self._initial_brightness

        log('Terminating...')
        return True

    def spawn(self):
        """Spawns the daemon."""
        self._startup()

        while True:
            now = stripped_datetime()

            if self._last is None or now > self._last:
                with suppress(KeyError):
                    self.brightness = self.config[now.time()]

                self._last = now

            try:
                sleep(self.tick)
            except KeyboardInterrupt:
                break

        return self._shutdown()
