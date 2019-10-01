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
from argparse import ArgumentParser
from contextlib import suppress
from datetime import datetime
from json import load
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from time import sleep

from backlight.api import NoSupportedGraphicsCards, load as load_backlight
from backlight.api.exceptions import NoLatestEntry


__all__ = [
    'TIME_FORMAT',
    'DEFAULT_CONFIG',
    'NoLatestEntry',
    'stripped_datetime',
    'load_config',
    'parse_config',
    'get_latest',
    'Daemon'
]


DEFAULT_CONFIG = Path('/etc/backlight.json')
LOG_FORMAT = '[%(levelname)s] %(name)s: %(message)s'
LOGGER = getLogger('backlightd')
TIME_FORMAT = '%H:%M'


def stripped_datetime(date_time=None):
    """Gets current date time, exact to minute."""

    date_time = date_time or datetime.now()
    return datetime(
        year=date_time.year, month=date_time.month, day=date_time.day,
        hour=date_time.hour, minute=date_time.minute)


def load_config(path):
    """Loads the configuration"""

    try:
        with path.open('r') as config_file:
            return load(config_file)
    except PermissionError:
        LOGGER.error('Cannot read config file: %s.', path)
    except FileNotFoundError:
        LOGGER.error('Config file does not exist: %s.', path)
    except ValueError:
        LOGGER.error('Config file has invalid content: %s.', path)

    return {}


def parse_config(config):
    """Parses the configuration dictionary."""

    for timestamp, brightness in config.items():
        try:
            timestamp = datetime.strptime(timestamp, TIME_FORMAT).time()
        except ValueError:
            LOGGER.error('Invalid timestamp "%s".', timestamp)
            continue
        else:
            timestamp = timestamp.strftime(TIME_FORMAT)

        try:
            brightness = int(brightness)
        except (TypeError, ValueError):
            LOGGER.error('Invalid brightness "%s".', brightness)
            LOGGER.debug('At "%s".', timestamp)
        else:
            if 0 <= brightness <= 100:
                yield (timestamp, brightness)
            else:
                LOGGER.error('Invalid percentage "%s".', brightness)
                LOGGER.debug('At "%s".', timestamp)


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


def get_args():
    """Parses the command line arguments."""

    parser = ArgumentParser(description='A screen backlight daemon.')
    parser.add_argument('graphics_card', nargs='?')
    parser.add_argument(
        '-c', '--config', metavar='config_file', type=Path,
        default=DEFAULT_CONFIG, help='sets the JSON configuration file')
    parser.add_argument(
        '-t', '--tick', metavar='seconds', type=float, default=1,
        help="sets the daemon's interval")
    parser.add_argument(
        '-r', '--reset', action='store_true',
        help='reset the brightness before terminating')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='turn on verbose logging')
    return parser.parse_args()


class Daemon:
    """A screen backlight daemon."""

    def __init__(self, backlight, config, reset=False, tick=1):
        """Tries the specified graphics cards until
        a working one is found.

        If none are specified, tries all graphics cards
        within BASEDIR until a working one is found.
        """
        self._backlight = backlight
        self.config = config
        self.reset = reset
        self.tick = tick
        self._initial_brightness = self.brightness
        self._last = None

    @classmethod
    def run(cls):
        """Runs as a daemon."""
        args = get_args()
        basicConfig(level=DEBUG if args.debug else INFO, format=LOG_FORMAT)
        backlight = load_backlight(args.graphics_card)
        config = dict(parse_config(load_config(args.config_file)))

        try:
            daemon = cls(backlight, config, reset=args.reset, tick=args.tick)
        except NoSupportedGraphicsCards:
            LOGGER.error('No supported graphics cards found.')
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
            LOGGER.error('Invalid brightness: %s.', percent)
        except PermissionError:
            LOGGER.error('Cannot set brightness.')
            LOGGER.info('Is this service running as root?')
        else:
            LOGGER.info('Set brightness to %s%%.', percent)

    def _startup(self):
        """Starts up the daemon."""
        LOGGER.info('Starting up...')
        LOGGER.info('Tick is %s second(s).', self.tick)
        LOGGER.info('Detected graphics card: %s.', self._backlight)
        LOGGER.info('Initial brightness is %s%%.', self._initial_brightness)

        try:
            timestamp, self.brightness = get_latest(self.config)
        except NoLatestEntry:
            LOGGER.error('Latest entry could not be determined.')
            LOGGER.error('Falling back to 100%.')
            self.brightness = 100
        else:
            timestamp = timestamp.strftime(TIME_FORMAT)
            LOGGER.info('Loaded latest setting from %s.', timestamp)

    def _shutdown(self):
        """Performs shutdown tasks."""
        if self.reset:
            LOGGER.info('Resetting brightness...')
            self.brightness = self._initial_brightness

        LOGGER.info('Terminating...')
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
