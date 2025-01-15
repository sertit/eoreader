# Custom stacks

Custom products can be created from any stack (and some data) provided by the user. These custom products will work
exactly as usual products, but with the user's metadata.

See [this notebook](https://eoreader.readthedocs.io/latest/notebooks/custom.html) for examples on how custom stacks
are working.

## Custom stack with minimum data

For both SAR and optical stacks, the two minimum keywords to provide are:

- `band_map`: a dictionary mapping the satellite band to the band number (starting to 1, in GDAL style)
- `sensor_type`: Either `SAR` or `OPTICAL` (a string or a SensorType Enum)

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

If you know them, it is best to give **EOReader** all the data you know about your stack:

- `name`: product name. If not provided, the filename will be used
- `datetime`: product acquisition datetime. If not provided, the datetime of the creation of the object will
  be used
- `constellation`: product constellation. If not provided, `CUSTOM` will be set. Either a string of a `Constellation` enum.
- `product_type`: product type. If not provided, `CUSTOM` will be set.
- `pixel_size`: product default pixel size. If not provided, the stack pixel size will be used.

For optical products, two additional keyword can be set to compute the hillshade band:

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

## Limitations

- ⚠ For now, stacks must be projected in **UTM** (and orthorectified)