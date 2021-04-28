# ![eoreader_logo](https://github.com/sertit/eoreader/blob/master/docs/eoreader_small.png) EOReader

**EOReader** is a **multi-satellite reader** allowing you to open
[optical](https://sertit.github.io/eoreader/eoreader#implemented-optical-satellites)
and [SAR](https://sertit.github.io/eoreader/eoreader#implemented-sar-satellites) data.

||**Optical** | **SAR**|
|--- | --- | ---|
|Sensors|+ Sentinel-2 & Theia<br>+ Sentinel-3 OLCI & SLSTR<br>+ Landsats 1 - 8| + Sentinel-1<br>+ COSMO-Skymed<br>+ TerraSAR-X<br>+ RADARSAT-2|

It also implements additional **sensor-agnostic** features:

- `eoreader.products.product.Product.load`: Load many band types:
    - satellite bands ([optical](https://sertit.github.io/eoreader/eoreader#band-mapping) or [SAR](https://sertit.github.io/eoreader/eoreader#sar-bands))
    - [index](https://sertit.github.io/eoreader/eoreader#available-index)
    - [cloud bands](https://sertit.github.io/eoreader/eoreader#cloud-bands)
    - [DEM bands](https://sertit.github.io/eoreader/eoreader#dem-bands)
- `eoreader.products.product.Product.stack`: Stack all these type of bands

EOReader works with [`xarrays.DataArray`](http://xarray.pydata.org/en/stable/generated/xarray.DataArray.html#xarray.DataArray)
and [`geopandas.GeoDataFrames`](https://geopandas.org/docs/user_guide/data_structures.html#geodataframe)


## Python Quickstart

The main features of EOReader are gathered hereunder:

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Your variables
>>> path = r"path/to/your/satellite/product"  # Optical in this example

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()
>>> prod = eoreader.open(path)  # The Reader will recognize the satellite type from its name

>>> # Get the footprint of the product (usable data) and its extent (envelope of the tile)
>>> footprint = prod.footprint
>>> extent = prod.extent

>>> # Load some bands and index: they will all share the same metadata
>>> bands = prod.load([NDVI, GREEN, HILLSHADE, CLOUDS]

>>> # Create a stack with some other bands
>>> stack = prod.stack([NDVI, MNDWI, GREEN, SLOPE, CIRRUS])

>>> # Read Metadata
>>> mtd, namespace = prod.read_mtd()
```

Sentinel-3 and SAR products need [`SNAP gpt`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to be geocoded.
Ensure that you have the folder containing your `gpt.exe` in your `PATH`.


## Examples

Available notebooks provided as examples:

- [Basic tutorial](/eoreader/examples/base.html)

## Installation

`pip install eoreader`

EOReader depends mainly on `geopandas` and `rasterio`.
(with GDAL installation issues on Windows, so please install them from wheels that you can
find [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio)).
