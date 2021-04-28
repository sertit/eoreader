# EOReader

This project is a multi-satellite **reader** allowing you to open
[optical](https://sertit.github.io/eoreader/eoreader#implemented-optical-satellites)
and [SAR](https://sertit.github.io/eoreader/eoreader#implemented-sar-satellites) data.

It also implements two additional features, non depending on the sensor:

- `eoreader.products.product.Product.load`: Load many band types:
    - satellite bands ([optical](https://sertit.github.io/eoreader/eoreader#band-mapping) or [SAR](https://sertit.github.io/eoreader/eoreader#sar-bands))
    - [index](https://sertit.github.io/eoreader/eoreader#available-index)
    - [cloud bands](https://sertit.github.io/eoreader/eoreader#cloud-bands)
    - [DEM bands](https://sertit.github.io/eoreader/eoreader#dem-bands)
- `eoreader.products.product.Product.stack`: Stack all these type of bands

It allows you to focus on the science instead of worrying how to access to the data, especially if you have to work with multiple sensors !

## Python Quickstart

The main features of EOReader are gathered hereunder:

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Your variables
>>> path = r"path/to/your/satellite/product"  # Optical in this example
>>> # WARNING: you can leave the output_path empty, but EOReader will create a temporary output directory
>>> # and you won't be able to retrieve what's has been written on disk
>>> output = r"path/to/your/output"

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()
>>> prod = eoreader.open(path, output_path=output)  # The Reader will recognize the satellite type from its name

>>> # Get the footprint of the product (usable data) and its extent (envelope of the tile)
>>> footprint = prod.footprint
>>> extent = prod.extent

>>> # Load some bands and index: they will all share the same metadata
>>> bands = prod.load([NDVI, GREEN, HILLSHADE, CLOUDS])  # Resolution not specified: use product resolution
>>> ndvi = bands[NDVI]
>>> green = bands[GREEN]
>>> hillshade = bands[HILLSHADE]
>>> clouds = bands[CLOUDS]
>>> # NOTE: every array that comes out `load` are collocated, which isn't the case if you load arrays separately
>>> # (important for DEM data as they may have different grids)

>>> # Create a stack with some other bands
>>> stack = prod.stack([NDVI, MNDWI, GREEN, SLOPE, CIRRUS])  # Resolution not specified: use product resolution

>>> # Read Metadata
>>> mtd, namespace = prod.read_mtd()
```

.. WARNING::
  - Sentinel-3 and SAR products need [`SNAP gpt`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to be geocoded.
  Ensure that you have the folder containing your `gpt.exe` in your `PATH`.

## Installation

`pip install eoreader`

.. WARNING ::
  EOReader depends mainly on `geopandas` and `rasterio`.
  (with GDAL installation issues on Windows, so please install them from wheels that you can
  find [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio)).
