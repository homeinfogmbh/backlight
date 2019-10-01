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
"""Custom data structures."""


__all__ = ['IntegerDifferential']


class IntegerDifferential(int):
    """An optionally signed integer."""

    def __new__(cls, value):
        if isinstance(value, str):
            value = value.strip()
            increase = value.startswith('+')
            decrease = value.startswith('-')
        else:
            increase = None
            decrease = None

        instance = super().__new__(cls, value)
        instance.increase = increase
        instance.decrease = decrease
        return instance
