# backlight
A screen backlight API, CLI and daemon.

## `backlight.api`
Provides a straightforward API to set the brightness of screen backlights
for devices available under `/sys/class/backlight`.

### Exceptions
The API provides some exceptions to handle errors that can occur while
handling the backlight.

#### `DoesNotExist`
Indicates that the provided graphics card does not exist under
`/sys/class/backlight`.

#### `DoesNotSupportAPI`
Indicates that the provided graphics card does not implement our API.

#### `NoSupportedGraphicsCards`
Indicates that no supported graphics cards could be found in either the
provided pool or, if none was supplied, the system.

### Interface
Provides an abtracting interface to the backlight API provided under
`/sys/class/backlight/<graphics_card>`.

#### `Backlight(graphics_card)`
Creates a new backlight instance using the respective graphics card.

If the provided graphics card does not exist, it raises `DoesNotExist`.

If the provided graphics card does not support this API, it raises
`DoesNotSupportAPI`.

#### `Backlight.load(graphics_cards=None)`
Loads the backlight using the first working graphics card specified in
`graphics_cards`.

If `graphics_cards` is `None`, it will use the first working graphics card
found on the system.

If no provided graphics cards could be found, it raises
`NoSupportedGraphicsCards`.

#### `Backlight.max`
Property to get the maximum raw backlight value.
The default minimum raw backlight value is always `0`.
This property is read-only.

#### `Backlight.raw`
Get and sets the raw backlight brightness of the used device as `str`.
The conditions and constraints of `Backlight.value` apply accordingly, except
that the integer values are represented by base-10 string representations.

#### `Backlight.value`
Gets and sets the raw backlight brightness of the used device, as `int`.
The valid values for this property are integers from `0` to `Backlight.max`
including both values and vary between different devices.

#### `Backlight.percent`
Gets and sets the raw backlight brightness in percent.
The valid values for this property range from `0` to `100` including both.
