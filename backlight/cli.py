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
"""A command line interface program to read
and set the screen's backlight brightnesss.
"""
from argparse import ArgumentParser
from sys import stderr

from backlight.api import NoSupportedGraphicsCards, load, IntegerDifferential


__all__ = ['main']


def get_args():
    """Parses the command line arguments."""

    parser = ArgumentParser(description='A screen backlight CLI interface.')
    parser.add_argument('value', type=IntegerDifferential, nargs='?')
    parser.add_argument(
        '--max', action='store_true', help='returns the maximum raw value')
    parser.add_argument('--graphics-card', help='specifies the graphics card')
    parser.add_argument(
        '--raw', action='store_true', help='work with raw values')
    return parser.parse_args()


def set_brightness(graphics_card, value, raw):
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


def main():
    """Runs as CLI program."""

    args = get_args()

    try:
        graphics_card = load(args.graphics_card)
    except NoSupportedGraphicsCards:
        print('No supported graphics cards found.', file=stderr, flush=True)
        return 3

    if args.max:
        print(graphics_card.max)
        return 0

    if args.value is None:
        if args.raw:
            print(graphics_card.raw, flush=True)
        else:
            print(graphics_card.percent, flush=True)

        return 0

    try:
        set_brightness(graphics_card, args.value, args.raw)
    except ValueError:
        print(f'Invalid percentage: {args.value}.', file=stderr, flush=True)
        retval = 1
    except PermissionError:
        print('Cannot set brightness. Try running as root.', file=stderr,
              flush=True)
        retval = 4
    except OSError:
        print(f'Invalid brightness: {args.value}.', file=stderr, flush=True)
        retval = 1
    else:
        retval = 0

    return retval
