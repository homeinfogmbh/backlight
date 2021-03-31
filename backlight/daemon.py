"""A daemon to update the screen's backlight brightness
at given timestamps to the respective value.
"""
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from datetime import datetime
from json import load
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from time import sleep
from typing import Iterable

from backlight.api import load as load_backlight, GraphicsCard
from backlight.types import TimedBrightness
from backlight.exceptions import NoLatestEntry, NoSupportedGraphicsCards


__all__ = [
    'TIME_FORMAT',
    'DEFAULT_CONFIG',
    'NoLatestEntry',
    'stripped_datetime',
    'load_config',
    'parse_config',
    'get_latest',
    'main',
    'Daemon'
]


DEFAULT_CONFIG = Path('/etc/backlight.json')
LOG_FORMAT = '[%(levelname)s] %(name)s: %(message)s'
LOGGER = getLogger('backlightd')
TIME_FORMAT = '%H:%M'


def stripped_datetime(timestamp: datetime  = None) -> datetime:
    """Gets current date time, exact to minute."""

    timestamp = timestamp or datetime.now()
    return datetime(
        year=timestamp.year, month=timestamp.month, day=timestamp.day,
        hour=timestamp.hour, minute=timestamp.minute)


def load_config(path: Path) -> dict:
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


def parse_config(config: dict) -> Iterable[TimedBrightness]:
    """Parses the configuration dictionary."""

    for timestamp, brightness in config.items():
        try:
            timestamp = datetime.strptime(timestamp, TIME_FORMAT).time()
        except ValueError:
            LOGGER.error('Invalid timestamp "%s".', timestamp)
            continue

        timestamp = timestamp.strftime(TIME_FORMAT)

        try:
            brightness = int(brightness)
        except (TypeError, ValueError):
            LOGGER.error('Invalid brightness "%s".', brightness)
            LOGGER.debug('At "%s".', timestamp)
            continue

        if 0 <= brightness <= 100:
            yield TimedBrightness(timestamp, brightness)
        else:
            LOGGER.error('Invalid percentage "%s".', brightness)
            LOGGER.debug('At "%s".', timestamp)


def get_latest(config: dict) -> TimedBrightness:
    """Returns the last config entry from the provided configuration."""

    now = stripped_datetime().time()
    sorted_values = sorted(config.items())
    latest = None

    for timestamp, brightness in sorted_values:
        if timestamp <= now:
            latest = TimedBrightness(timestamp, brightness)
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


def get_args() -> Namespace:
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


def main():
    """Runs as a daemon."""

    args = get_args()
    basicConfig(level=DEBUG if args.debug else INFO, format=LOG_FORMAT)
    backlight = load_backlight(args.graphics_card)
    config = dict(parse_config(load_config(args.config_file)))

    try:
        daemon = Daemon(backlight, config, reset=args.reset, tick=args.tick)
    except NoSupportedGraphicsCards:
        LOGGER.error('No supported graphics cards found.')
        return 3

    if daemon.spawn():
        return 0

    return 1


class Daemon:
    """A screen backlight daemon."""

    def __init__(self, backlight: GraphicsCard, config: dict,
                 reset: bool = False, tick: int = 1):
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
