"""A linux screen backlight API and daemon.

This module supports getting and setting of the backlight brightness
of graphics cards unter '/sys/class/backlight/<graphics_card>/',
provided they implement the files 'brightness', 'actual_brightness'
and 'max_brightness' in the respective folder.
"""
from contextlib import suppress
from datetime import datetime
from json import load
from os import listdir
from os.path import exists, isfile, join
from sys import exit, stderr
from time import sleep

try:
    from docopt import docopt
except ImportError:
    def docopt(_):
        """Docopt mockup to fail if invoked."""
        print('WARNING: "docopt" not installed.', file=stderr, flush=True)
        print('Daemon and CLI unavailable.', file=stderr, flush=True)
        exit(5)


__all__ = [
    'DEFAULT_CONFIG',
    'BASEDIR',
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoSupportedGraphicsCards',
    'NoLatestEntry',
    'stripped_datetime',
    'load_config',
    'parse_config',
    'get_latest',
    'Backlight',
    'Daemon',
    'CLI']


TIME_FORMAT = '%H:%M'
DEFAULT_CONFIG = '/etc/backlight.json'
BASEDIR = '/sys/class/backlight'


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
            timestamp = datetime.strptime(timestamp, TIME_FORMAT).time()
        except ValueError:
            error('Skipping invalid timestamp: {}.'.format(timestamp))
        else:
            try:
                brightness = int(brightness)
            except (TypeError, ValueError):
                error('Skipping invalid brightness: "{}" at {}.'.format(
                    brightness, timestamp.strftime(TIME_FORMAT)))
            else:
                if 0 <= brightness <= 100:
                    yield (timestamp, brightness)
                else:
                    error('Skipping invalid percentage: {} at {}.'.format(
                        brightness, timestamp.strftime(TIME_FORMAT)))


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


class Backlight():
    """Backlight handler for graphics cards."""

    def __init__(self, graphics_card):
        """Sets the respective graphics card."""
        self._graphics_card = graphics_card

        if not exists(self._path):
            raise DoesNotExist()

        if not all(isfile(file) for file in self._files):
            raise DoesNotSupportAPI()

    def __str__(self):
        """Returns the respective graphics card's name."""
        return self._graphics_card

    @classmethod
    def load(cls, graphics_cards=None):
        """Loads the backlight from the respective graphics cards.

        If no graphics cards have been defined, seek BASEDIR for
        available graphics card and return backlight for the first
        graphics card that implements the API.
        """
        if not graphics_cards:
            graphics_cards = listdir(BASEDIR)

        for graphics_card in graphics_cards:
            with suppress(DoesNotExist, DoesNotSupportAPI):
                return cls(str(graphics_card))

        raise NoSupportedGraphicsCards() from None

    @property
    def _path(self):
        """Returns the absolute path to the
        graphics card's device folder.
        """
        return join(BASEDIR, self._graphics_card)

    @property
    def _max_file(self):
        """Returns the path of the maximum brightness file."""
        return join(self._path, 'max_brightness')

    @property
    def _setter_file(self):
        """Returns the path of the backlight file."""
        return join(self._path, 'brightness')

    @property
    def _getter_file(self):
        """Returns the file to read the current brightness from."""
        return join(self._path, 'actual_brightness')

    @property
    def _files(self):
        """Yields the graphics cards API's files."""
        yield self._max_file
        yield self._setter_file
        yield self._getter_file

    @property
    def max(self):
        """Returns the raw maximum brightness."""
        with open(self._max_file, 'r') as file:
            return int(file.read().strip())

    @property
    def raw(self):
        """Returns the raw brightness."""
        with open(self._getter_file, 'r') as file:
            return file.read().strip()

    @raw.setter
    def raw(self, brightness):
        """Sets the raw brightness."""
        with open(self._setter_file, 'w') as file:
            return file.write('{}\n'.format(brightness))

    @property
    def value(self):
        """Returns the raw brightness as integer."""
        return int(self.raw)

    @value.setter
    def value(self, brightness):
        """Sets the raw brightness."""
        self.raw = str(brightness)

    @property
    def percent(self):
        """Returns the current brightness in percent."""
        return self.value * 100 // self.max

    @percent.setter
    def percent(self, percent):
        """Returns the current brightness in percent."""
        if 0 <= percent <= 100:
            self.value = self.max * percent // 100
        else:
            raise ValueError('Invalid percentage: {}.'.format(percent))


class Daemon():
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
        self._backlight = Backlight.load(graphics_cards)
        self.config = dict(parse_config(load_config(config_file)))
        self.reset = reset
        self.tick = tick
        self._initial_brightness = self._backlight.percent
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
        else:
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
            error('Invalid brightness: {}.'.format(percent))
        except PermissionError:
            error('Cannot set brightness. Is this service running as root?')
        else:
            log('Set brightness to {}%.'.format(percent))

    def _startup(self):
        """Starts up the daemon."""
        log('Starting up...')
        log('Tick is {} second(s).'.format(self.tick))
        log('Detected graphics card: {}.'.format(self._backlight))
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


class CLI():
    """backlight

A screen backlight CLI interface.

Usage:
    backlight [<value>] [options]

Options:
    --graphics-card=<graphics_card>   Sets the desired graphics card.
    --raw                             Work with raw values instead of percent.
    --help                            Shows this page.
"""

    def __init__(self, graphics_cards):
        """Sets the graphics cards."""
        self._backlight = Backlight.load(graphics_cards)

    @classmethod
    def run(cls):
        """Runs as CLI program."""
        options = docopt(cls.__doc__)

        try:
            cli = CLI([options['--graphics-card']])
        except NoSupportedGraphicsCards:
            error('No supported graphics cards found.')
            return 3
        else:
            value = options['<value>']

            if value:
                return cli.set_brightness(value, raw=options['--raw'])

            return cli.print_brightness(raw=options['--raw'])

    def print_brightness(self, raw=False):
        """Returns the current backlight brightness."""
        if raw:
            print(self._backlight.raw)
        else:
            print(self._backlight.percent)

        return 0

    def set_brightness(self, value, raw=False):
        """Seths the backlight brightness."""
        if raw:
            try:
                self._backlight.raw = value
            except PermissionError:
                error('Cannot set brightness. Try running as root.')
                return 4
            except OSError:
                error('Invalid brightness: {}.'.format(value))
                return 1
        else:
            try:
                value = int(value)
            except ValueError:
                error('Value must be an integer.')
                return 2
            else:
                try:
                    self._backlight.percent = value
                except ValueError:
                    error('Invalid percentage: {}.'.format(value))
                    return 1
                except PermissionError:
                    error('Cannot set brightness. Try running as root.')
                    return 4
