"""API exceptions."""


__all__ = [
    "DoesNotExist",
    "DoesNotSupportAPI",
    "NoOutputFound",
    "NoSupportedGraphicsCards",
    "NoLatestEntry",
]


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
