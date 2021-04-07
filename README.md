# EOReader

This project allows you to read and open satellite data.

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Your variables
>>> path = r"path/to/your/satellite/product"  # Optical in this example
>>> # WARNING: you can leave the output_path empty, but EOReader will create a temporary output directory 
>>> # and you won't be able to retrieve what's has been written on disk
>>> output = r"path/to/your/output"

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()  # This is a singleton
>>> prod = eoreader.open(path, output_path=output)  # The Reader will recognize the satellite type from its name

>>> # Get the footprint of the product (usable data) and its extent (envelope of the tile)
>>> footprint = prod.footprint
>>> extent = prod.extent

>>> # Load some bands and index: they will all share the same metadata
>>> bands, meta = prod.load([NDVI, GREEN, HILLSHADE, CLOUDS])  # Resolution not specified: use product resolution
>>> ndvi = bands[NDVI]
>>> green = bands[GREEN]
>>> hillshade = bands[HILLSHADE]
>>> clouds = bands[CLOUDS]
>>> # NOTE: every array that comes out `load` are collocated, which isn't the case if you load arrays separately 
>>> # (important for DEM data as they may have different grids)

>>> # Create a stack with some other bands
>>> stack, stk_meta = prod.stack([NDVI, MNDWI, GREEN, SLOPE, CIRRUS])  # Resolution not specified: use product resolution

>>> # Read Metadata
>>> mtd, namespace = prod.read_mtd()
```
 
Index and bands are opened as `numpy.ma.masked_array` 
(see [here](https://numpy.org/doc/stable/reference/maskedarray.generic.html) to learn more about it) and converted to float.
Their mask corresponds to the nodata of your product, that is set to 0 by convention.
Clouds masks are loaded in `uint8` and their nodata is set to 255.

**WARNING**: 

- This software relies on satellite's name to open them, so please do not modify them !
- Sentinel-3 and SAR products need [`SNAP gpt`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to work.  
Ensure that you have the folder containing your `gpt.exe` in your `PATH`.
