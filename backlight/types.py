"""Custom data structures."""

from typing import NamedTuple


__all__ = ["Backlight", "IntegerDifferential", "PercentageMap", "TimedBrightness"]


class Backlight(NamedTuple):
    """Represents backlight settings."""

    percent: int
    method: str


class IntegerDifferential(int):
    """An optionally signed integer."""

    def __new__(cls, value):
        if isinstance(value, str):
            value = value.strip()
            increase = value.startswith("+")
            decrease = value.startswith("-")
        else:
            increase = None
            decrease = None

        instance = super().__new__(cls, value)
        instance.increase = increase
        instance.decrease = decrease
        return instance


class PercentageMap(dict):
    """Range of brightness raw and percentage values."""

    __slots__ = ()

    def __init__(self, raw, percent=range(0, 101)):
        """Sets raw and percentage ranges."""
        super().__init__()
        raw_span = max(raw) - min(raw)
        percent_span = max(percent) - min(percent)
        percent_step = percent_span / raw_span
        percentage = min(percent)

        for raw_value in raw:
            next_percentage = percentage + percent_step
            self[raw_value] = range(round(percentage), round(next_percentage))
            percentage = next_percentage

    def from_percent(self, percentage):
        """Returns the raw value for the given percentage."""
        for raw, percent in self.items():
            if percentage in percent:
                return raw

        raise ValueError(percentage)


class TimedBrightness(NamedTuple):
    """Brightness at a specific time setting."""

    timestamp: str
    brightness: int
