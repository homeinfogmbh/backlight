"""A command line interface program to read
and set the screen's backlight brightnesss.
"""
from argparse import ArgumentParser, Namespace
from logging import INFO, basicConfig, getLogger
from pathlib import Path

from backlight.api import load, GraphicsCard
from backlight.exceptions import NoSupportedGraphicsCards
from backlight.types import IntegerDifferential


__all__ = ['main']


BACKUP_FILE = Path('/etc/backlight')
LOG_FORMAT = '[%(levelname)s] %(name)s: %(message)s'
LOGGER = getLogger('brightness')


def _set_value(graphics_card: GraphicsCard, value: IntegerDifferential, *,
               raw: bool = False) -> None:
    """Sets the brightness."""

    if raw:
        if value.increase:
            value = min(graphics_card.max, graphics_card.raw + value)
        elif value.decrease:
            value = max(0, graphics_card.raw - value)

        graphics_card.raw = value
    else:
        if value.increase:
            value = min(100, graphics_card.percent + value)
        elif value.decrease:
            value = max(0, graphics_card.percent - value)

        graphics_card.percent = value


def set_value(graphics_card: GraphicsCard, value: IntegerDifferential, *,
              raw: bool = False) -> int:
    """Sets the brightness and handles errors."""

    try:
        _set_value(graphics_card, value, raw=raw)
    except ValueError:
        LOGGER.error('Invalid percentage: %s.', value)
        return 1
    except PermissionError:
        LOGGER.error('Cannot set brightness. Try running as root.')
        return 2
    except OSError:
        LOGGER.error('Invalid brightness: %s.', value)
        return 3

    return 0


def load_value(graphics_card: GraphicsCard, backup_file: Path) -> int:
    """Loads from a backup file."""

    try:
        with backup_file.open('r') as file:
            value = IntegerDifferential(file.read().strip())
    except (FileNotFoundError, PermissionError) as error:
        LOGGER.error(str(error))
        return 1
    except ValueError:
        LOGGER.error('Backup file contains garbage: %s', backup_file)
        return 2

    return set_value(graphics_card, value, raw=True)


def save_value(graphics_card: GraphicsCard, backup_file: Path) -> int:
    """Saves backlight to file."""

    try:
        with backup_file.open('w') as file:
            file.write(str(graphics_card.raw))
    except (FileNotFoundError, PermissionError) as error:
        LOGGER.error(str(error))
        return 1

    return 0


def get_args() -> Namespace:
    """Parses the command line arguments."""

    parser = ArgumentParser(description='A screen backlight CLI interface.')
    parser.add_argument('value', type=IntegerDifferential, nargs='?')
    parser.add_argument(
        '-l', '--load', action='store_true', help='load brightness from file')
    parser.add_argument(
        '-s', '--save', action='store_true', help='save brightness to file')
    parser.add_argument(
        '-f', '--file', type=Path, default=BACKUP_FILE, metavar='filename',
        help='brightness backup file')
    parser.add_argument(
        '--max', action='store_true', help='returns the maximum raw value')
    parser.add_argument('--graphics-card', help='specifies the graphics card')
    parser.add_argument(
        '--raw', action='store_true', help='work with raw values')
    parser.add_argument(
        '--omit-actual', action='store_true',
        help='do not use actual_brightness')
    return parser.parse_args()


def main() -> int:
    """Runs as CLI program."""

    args = get_args()
    basicConfig(level=INFO, format=LOG_FORMAT)

    try:
        graphics_card = load(args.graphics_card, omit_actual=args.omit_actual)
    except NoSupportedGraphicsCards:
        LOGGER.error('No supported graphics cards found.')
        return 3

    if args.max:
        print(graphics_card.max)
        return 0

    if args.value is None:
        if args.load:
            return load_value(graphics_card, args.file)

        if args.save:
            return save_value(graphics_card, args.file)

        if args.raw:
            print(graphics_card.raw, flush=True)
        else:
            print(graphics_card.percent, flush=True)

        return 0

    return set_value(graphics_card, args.value, raw=args.raw)
