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
"""API exceptions."""


__all__ = [
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoOutputFound',
    'NoSupportedGraphicsCards',
    'NoLatestEntry']


class DoesNotExist(Exception):
    """Indicates that the respective graphics card does not exist."""


class DoesNotSupportAPI(Exception):
    """Indicates that the respective graphics
    card does not implement this API.
    """


class NoOutputFound(Exception):
    """Indicates that no output could be determined."""


class NoSupportedGraphicsCards(Exception):
    """Indicates that the available graphics cards are not supported."""


class NoLatestEntry(Exception):
    """Indicates that no latest entry could
    be determined from the configuration.
    """
