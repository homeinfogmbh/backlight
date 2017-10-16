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
from sys import stderr, exit as exit_

try:
    from docopt import docopt
except ImportError:
    def docopt(_):
        """Docopt mockup to fail if invoked."""
        print('WARNING: "docopt" not installed.', file=stderr, flush=True)
        print('Daemon and CLI unavailable.', file=stderr, flush=True)
        exit_(5)

from backlight.api import NoSupportedGraphicsCards, Backlight

__all__ = ['error', 'log', 'CLI']


def error(*msgs):
    """Logs error messages."""

    print(*msgs, file=stderr, flush=True)


def log(*msgs):
    """Logs informational messages."""

    print(*msgs, flush=True)


class CLI:
    """backlight

A screen backlight CLI interface.

Usage:
    backlight [<value>] [options]

Options:
    --graphics-card=<graphics_card>   Sets the desired graphics card.
    --raw                             Work with raw values instead of percent.
    --max                             Returns the maximum raw backlight value.
    --help                            Shows this page.
"""

    def __init__(self, graphics_cards):
        """Sets the graphics cards."""
        self._backlight = Backlight.load(graphics_cards)

    @classmethod
    def run(cls):
        """Runs as CLI program."""
        options = docopt(cls.__doc__)
        graphics_card = options['--graphics-card']
        graphics_cards = [graphics_card] if graphics_card else None

        try:
            cli = cls(graphics_cards)
        except NoSupportedGraphicsCards:
            error('No supported graphics cards found.')
            return 3
        else:
            value = options['<value>']

            if value:
                return cli.set_brightness(value, raw=options['--raw'])

            return cli.print_brightness(
                raw=options['--raw'], maximum=options['--max'])

    def print_brightness(self, raw=False, maximum=False):
        """Returns the current backlight brightness."""
        if maximum:
            print(self._backlight.max)
        else:
            print(self._backlight.raw if raw else self._backlight.percent)

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
                error('Percentage must be an integer.')
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
