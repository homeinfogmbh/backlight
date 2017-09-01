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
    def docopt(_):
        """Docopt mockup to fail if invoked."""
        print('WARNING: "docopt" not installed.', file=stderr, flush=True)
        print('Daemon and CLI unavailable.', file=stderr, flush=True)
        exit(127)


__all__ = [
    'DEFAULT_CONFIG',
    'BASEDIR',
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoSupportedGraphicsCards',
    'NoLatestEntry',
    'strip_time',
    'load_config',
    'parse_config',
    'get_latest',
    'GraphicsCard',
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


def strip_time(timestamp):
    """Returns the time with hours and minutes only."""

    return time(hour=timestamp.hour, minute=timestamp.minute)


def get_backlight(graphics_cards):
    """Gets the backlight for the first supporting graphics card."""

    if not graphics_cards:
        graphics_cards = listdir(BASEDIR)

    for graphics_card in graphics_cards:
        with suppress(DoesNotExist, DoesNotSupportAPI):
            return GraphicsCard(graphics_card).backlight

    raise NoSupportedGraphicsCards() from None


def read_brightness(path):
    """Reads the raw brightness from the respective file."""

    with open(path, 'r') as file:
        return file.read().strip()


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


class GraphicsCard():
    """Graphics card API."""

    def __init__(self, name):
        """Sets the graphics card's name."""
        self.name = name

        if not exists(self.path):
            raise DoesNotExist()

    @property
    def path(self):
        """Returns the absolute path to the
        graphics card's device folder.
        """
        return join(BASEDIR, self.name)

    @property
    def backlight(self):
        """Returns the respective backlight handler."""
        return Backlight(self)


class Backlight():
    """Backlight handler for graphics cards."""

    def __init__(self, graphics_card):
        """Sets the respective graphics card."""
        self.graphics_card = graphics_card

        if not all(isfile(file) for file in self._files):
            raise DoesNotSupportAPI()

    @property
    def _max_file(self):
        """Returns the path of the maximum brightness file."""
        return join(self.graphics_card.path, 'max_brightness')

    @property
    def _setter_file(self):
        """Returns the path of the backlight file."""
        return join(self.graphics_card.path, 'brightness')

    @property
    def _getter_file(self):
        """Returns the file to read the current brightness from."""
        return join(self.graphics_card.path, 'actual_brightness')

    @property
    def _files(self):
        """Yields the graphics cards API's files."""
        yield self._max_file
        yield self._setter_file
        yield self._getter_file

    @property
    def max(self):
        """Returns the raw maximum brightness."""
        return int(read_brightness(self._max_file))

    @property
    def raw(self):
        """Returns the raw brightness."""
        return read_brightness(self._getter_file)

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
        self._backlight = get_backlight(graphics_cards)
        self.config = dict(parse_config(load_config(config_file)))
        self.reset = reset
        self.tick = tick
        self._initial_brightness = self._backlight.percent
        self._last_timestamp = None

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
        log('Detected graphics card: {}.'.format(
            self._backlight.graphics_card.name))
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

    def spawn(self):
        """Spawns the daemon."""
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


class CLI():
    """backlight

A screen backlight CLI interface.

Usage:
    backlight [<value>] [options]

Options:
    --graphics-card=<graphics_card>     Sets the desired graphics card.
    --raw                               Get / set raw brightness.
    --help                              Shows this page.
"""

    def __init__(self, graphics_cards):
        """Sets the graphics cards."""
        self._backlight = get_backlight(graphics_cards)

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
