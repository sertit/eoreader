# Custom stacks

Custom products can be created from any stack (and some data) provided by the user. These custom products will work
exactly like regular products, but with the user's metadata.

See [this notebook](https://eoreader.readthedocs.io/latest/notebooks/custom.html) for examples of how custom stacks work.

## Custom stack with minimum data

For both SAR and optical stacks, the two minimum keywords to provide are:

- `band_map`: a dictionary mapping the satellite band to the band number (starting **from** 1, in GDAL style)
- `sensor_type`: Either `SAR` or `OPTICAL` (a string or a `SensorType` enum)

```python

from eoreader.reader import Reader
from eoreader.bands.alias import *

custom_prod = Reader().open(
    "stack_path.tif",
    custom=True,
    sensor_type="OPTICAL",
    band_map={
        BLUE: 1,
        GREEN: 2,
        RED: 3,
        NIR: 4
    }
)
```

## Custom stack with full data

If you know them, it is best to provide **EOReader** with all the data you know about your stack:

- `name`: product name. If not provided, the filename will be used
- `datetime`: product acquisition datetime. If not provided, the datetime of the creation of the object will be used
- `constellation`: product constellation. If not provided, `CUSTOM` will be set. Either a string or a `Constellation` enum.
- `product_type`: product type. If not provided, `CUSTOM` will be set.
- `pixel_size`: product default pixel size. If not provided, the stack pixel size will be used.

For optical products, two additional keywords can be set to compute the hillshade band:

- `sun_azimuth`
- `sun_zenith`

```python

from eoreader.reader import Reader
from eoreader.bands.alias import *

custom_prod = Reader().open(
    "stack_path.tif",
    custom=True,
    name="20200310T030415_WV02_Ortho",
    datetime="20200310T030415",
    sensor_type="OPTICAL",
    constellation="WV02",
    product_type="Ortho",
    pixel_size=2.0,
    sun_azimuth=10.0,
    sun_zenith=20.0,
    band_map={
        BLUE: 1,
        GREEN: 2,
        RED: 3,
        NIR: 4
    }
)
```

## Disambiguate the custom stack

At the heart of EOReader lies the condensed name of a product, to which every produced file refers.
However, if insufficient data is provided when creating your custom stack, ambiguity can occur if several custom stacks are created in the same second.

To avoid this, if no product type or constellation is given, the condensed name will be set to the file's filename.

However, if this does not suit you, there are several workarounds:
- Provide a datetime and a product type or constellation
- Add an `id` that will be added at the end of your condensed name
- Provide your own custom condensed name directly via `condensed_name`

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> custom_prod = Reader().open(
        "stack_path.tif",
        custom=True,
        name="20200310T030415_WV02_Ortho",
        sensor_type="OPTICAL",
        condensed_name="my_wonderful_name",
        band_map={
            BLUE: 1,
            GREEN: 2,
            RED: 3,
            NIR: 4
        }
    )
>>> custom_prod.condensed_name
my_wonderful_name

>>> custom_prod = Reader().open(
        "stack_path.tif",
        custom=True,
        name="20200310T030415_WV02_Ortho",
        datetime="20200310T030415",
        sensor_type="OPTICAL",
        constellation="WV02",
        id="test",
        band_map={
            BLUE: 1,
            GREEN: 2,
            RED: 3,
            NIR: 4
        }
    )
>>> custom_prod.condensed_name
20200310T030415_WV02_CUSTOM_test
```

## Limitations

- ⚠️ Currently, stacks must be projected in **UTM** (and orthorectified)