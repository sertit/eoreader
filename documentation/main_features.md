# Main features

## Read

The reader singleton is your unique entry.
It will create for you the product object corresponding to your satellite data.

.. WARNING::
    Be sure that your satellite data folder has the required name to be recognized !
    Only COSMO-Skymed data relies on the SAR band name and can have any folder name.

```python
>>> import os
>>> from eoreader.reader import Reader

>>> # Path to your satellite data, ie. S2
>>> path = r'S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.zip'  # You can work with the archive for S2 data

>>> # Path to your output directory (if not set, it will work in a temp directory)
>>> output = os.path.abspath('.')

>>> # Create the reader singleton
>>> eoreader = Reader()
>>> # The Reader will recognize the satellite type from its name so keep the original one !
>>> prod = eoreader.open(path, output_path=output)

>>> # NOTE: you can set the output directory after the creation, that allows you to use the product condensed name
>>> prod.output = os.path.join(output, prod.condensed_name)  # It will automatically create it if needed
```

From there you have access to a lot of information on your product:

```python
>>> # Product CRS (always in UTM)
>>> prod.crs
CRS.from_epsg(32630)

>>> # Full extent of the bands as a geopandas GeoDataFrame (always in UTM)
>>> prod.extent()
                                            geometry
0   POLYGON((309780.000 4390200.000, 309780.000 4...

>>> # Footprint: extent of the useful pixels (minus nodata) as a geopandas GeoDataFrame (always in UTM)
>>> prod.footprint()
   index                                           geometry
0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

>>> # Default resolution (20m for S2)
>>> prod.resolution
20.

>>> # Acquisition date and datetime
>>> prod.date
datetime.date(2020, 8, 24)
>>> prod.datetime
datetime.datetime(2020, 8, 24, 11, 6, 31)

>>> # Access the raw metadata as an lxml.etree._Element:
>>> prod.read_mtd()
```

See the difference between footprint and extent hereunder:

|Without nodata | With nodata|
|--- | ---|
| ![without_nodata](https://zupimages.net/up/21/14/69i6.gif) | ![with_nodata](https://zupimages.net/up/21/14/vg6w.gif) |

## Load

`eoreader.products.product.Product.load` is the function for accessing to product-related bands.
It can load satellite bands, index, DEM bands and cloud bands according to this workflow:
![load_workflow](https://zupimages.net/up/21/14/vtnc.png)

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.zip"
>>> prod = Reader().open(path)

>>> # Get the wanted bands and check if the product can produce them
>>> band_list = [GREEN, NDVI, TIR_1, SHADOWS, HILLSHADE]
>>> ok_bands = [band for band in band_list if prod.has_band(band)]
[GREEN, NDVI, HILLSHADE]
>>> # Sentinel-2 cannot produce satellite band TIR_1 and cloud band SHADOWS

>>> # Load bands
>>> bands, meta = prod.load(ok_bands)
>>> bands
{
<function NDVI at 0x00000227FBB929D8>: masked_array(
  data=[[[-0.02004455029964447, ..., 0.11663568764925003]]],
  mask=[[[False, ..., False]]],
  fill_value=0.0,
  dtype=float32),
  <OpticalBandNames.GREEN: 'GREEN'>: masked_array(
  data=[[[0.061400000005960464, ..., 0.15799999237060547]]],
  mask=[[[False, ..., False]]],
  fill_value=0.0,
  dtype=float32),
  <DemBandNames.HILLSHADE: 'HILLSHADE' >: masked_array(
  data=[[[0.0, ..., 0.0]]],
  mask=[[[False, ..., False]]],
  fill_value=0.0,
  dtype=float32)
}
>>> meta
{
    'driver': 'GTiff',
    'dtype': <class 'numpy.float32'>,
    'nodata': 0,
    'width': 5490,
    'height': 5490,
    'count': 1,
    'crs': CRS.from_epsg(32630),
    'transform': Affine(20.0, 0.0, 199980.0,0.0, -20.0, 4500000.0)
}
>>> # 20. meters is the default resolution
>>> # All bands will have the same metadata
```

.. WARNING::
    For now there is a discrepancy between clouds bands and metadata
    (**only if loaded with other bands**) as their type is `uint8` and their nodata is `255`.
    This will be fixed when EOReader will use `xarrays` instead of `dicts`.
    The current workaround is to load cloud bands separately.

## Stack

`eoreader.products.product.Product.stack` is the function stacking all possible bands.
It is based on the load function and then just stacks the bands and write it on disk if needed.

```python
>>> # Create a stack with the previous OK bands
>>> stack, stk_meta = prod.stack(ok_bands, resolution=300., stack_path=os.path.join(prod.output, "stack.tif")
```
