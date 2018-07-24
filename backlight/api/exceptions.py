"""API exceptions."""


__all__ = [
    'DoesNotExist',
    'DoesNotSupportAPI',
    'NoOutputFound',
    'NoSupportedGraphicsCards']


class DoesNotExist(Exception):
    """Indicates that the respective graphics card does not exist."""

    pass


class DoesNotSupportAPI(Exception):
    """Indicates that the respective graphics
    card does not implement this API.
    """

    pass


class NoOutputFound(Exception):
    """Indicates that no output could be determined."""

    pass


class NoSupportedGraphicsCards(Exception):
    """Indicates that the available graphics cards are not supported."""

    pass
