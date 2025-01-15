# Main features

These features can be seen in the [basic tutorial](https://eoreader.readthedocs.io/latest/notebooks/base.html).

## Open

The reader singleton is your unique entry.
It will create for you the product object corresponding to your satellite data.

You can load products from the cloud, see 
[this tutorial](https://eoreader.readthedocs.io/latest/notebooks/s3_compatible_storage.html).
S3 and S3 Compatible Storage are working and maybe Google and Azure if `rasterio` supports it, 
but they have not been tested.

```python
import os
from reader import Reader

# Path to your satellite data, i.e. Sentinel-2
# You can directly work with archived S2 data
path = r'S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.zip'

# Path to your output directory (if not set, it will work in a temp directory)
output = os.path.abspath('.')

# Create the reader singleton
reader = Reader()
prod = reader.open(path, output_path=output, remove_tmp=True)
# remove_tmp allows you to automatically delete processing files 
# such as cleaned or orthorectified bands when the product is deleted
# False by default to speed up the computation if you want to use the same product in several part of your code

# NOTE: you can set the output directory after the creation, that allows you to use the product condensed name
# It will automatically create the output directory if needed
prod.output = os.path.join(output, prod.condensed_name)
```

The goal of this library is to manage only one satellite product at a time. 
To handle more complicated sets of products (such as mosaics, pairs or time series), please consider using [`EOSets`](https://github.com/sertit/eosets).

### Recognized paths

**EOReader** always uses the directory containing the product files.
Hereunder are the paths meant to be given to the reader.

#### Optical

| Sensor group                                   | Folder to link                                                                                                          |
|------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `Sentinel-2 and 3`                             | Main directory, `.SAFE`, `.SEN3` or `.zip`,<br>i.e. `S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE` |
| `Sentinel-2 Theia`                             | Main directory containing the `.tif` images,<br>i.e. `SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2`                 |
| `Landsats`                                     | Main directory extracted or archived if Collection 2 (`.tar`),<br>i.e. `LC08_L1TP_200030_20201220_20210310_02_T1.tar`   |
| `Harmonized Landsat-Sentinel`                  | Main directory containing the `.tif` images,<br>i.e. `HLS.S30.T42RUS.2022241T060629.v2.0`                               |
| `PlanetScope`, `SkySat` and `RapidEye`         | Directory containing the `manifest.json` file,<br>i.e. `20210406_015904_37_2407`                                        |
| `DIMAP`<br>(Pleiades, SPOTs,<br>Vision-1, ...) | Directory containing the `.JP2` files,<br>i.e. `IMG_PHR1B_PMS_001`                                                      |
| `Maxar`<br>(WorldViews,<br>GeoEye...)          | Directory containing the `.TIL` file,<br>i.e. `013187549010_01_P001_PSH`                                                |
| `SuperView-1`                                  | Directory containing the `.shp` file,<br>i.e. `0032100150001_01`                                                        |  
| `GEOSAT-2`                                     | Directory containing the `.dim` file,<br>i.e. `DE2_PM4_L1C_000000_20161107T013821_20161107T013826_DE2_12927_DE02`       |

#### SAR

| Sensor group                             | Folder to link                                                                                                                         |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `Sentinel-1`<br>`RADARSAT-Constellation` | SAFE directory containing the `manifest.safe` file,<br>i.e. `S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.SAFE` |
| `COSMO-Skymed`<br>1st and 2nd Gen        | Directory containing the `.h5` image,<br>i.e. `1011117-766193`                                                                         |
| `RADARSAT-2`                             | Main directory containing the `.tif` image,<br>i.e. `RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip`                   |
| `TerraSAR-X`<br>`TanDEM-X`<br>`PAZ SAR`  | Directory containing the `IMAGEDATA` directory,<br>i.e. `TDX1_SAR__MGD_SE___SM_S_SRA_20201016T231611_20201016T231616`                  |
| `ICEYE`                                  | Directory containing the `.tif` file,<br>i.e. `SC_124020`                                                                              |
| `SAOCOM`                                 | Directory containing the `.xemt` **AND** the `.zip` files,<br>i.e. `11245-EOL1CSARSAO1A198523`                                         |
| `CAPELLA`                                | Directory containing the `.tif` file,<br>i.e. `CAPELLA_C05_SP_SLC_HH_20220320114010_20220320114013`                                    |

## Load

{meth}`~eoreader.products.product.Product.load` is the function for accessing product-related bands.
It can load satellite bands, index, DEM bands and cloud bands according to this workflow:

```{image} https://zupimages.net/up/22/12/9mz0.png
:class: full-width
:alt: load_workflow
```

Bands can be called with their name, ID or mapped name. 
For example, for Sentinel-3 OLCI you can use `7`, `Oa07` or `YELLOW`. For Landsat-8, you can use `BLUE` or `2`.

```{note}
For now, EOReader **always** loads bands with projected CRS (in UTM). 

We know that this policy may be an issue for:

- Sentinel-3 data that are very wide and may have inaccurate georeferencing.
- DIMAP data provided in WGS84 that need reprojection (and therefore time-consuming processes)

If needed, we could change in the future this to allow custom CRS. 
If so, do not hesitate to add comments in [this issue](https://github.com/sertit/eoreader/issues/5) on GitHub !
```

```python
import os
from eoreader.reader import Reader
from eoreader.bands import *
from eoreader.env_vars import DEM_PATH

path = r"S2B_MSIL1C_20210517T103619_N7990_R008_T30QVE_20210929T075738.SAFE"
output = os.path.abspath("./output")
# WARNING: you can leave the output_path empty, but EOReader will create a temporary output directory,
# and you won't be able to retrieve what's has been written on disk
prod = Reader().open(path, output_path=output)

# Specify a DEM to load DEM bands
os.environ[DEM_PATH] = r"my_dem.tif"

# Get the wanted bands and check if the product can produce them
band_list = [GREEN, NDVI, TIR_1, SHADOWS, HILLSHADE]
ok_bands = to_str([band for band in band_list if prod.has_band(band)])
# [GREEN, NDVI, HILLSHADE]
# Sentinel-2 cannot produce satellite band TIR_1 and cloud band SHADOWS

# Load bands
# if pixel_size is not specified -> load at default pixel_size (10.0 m for S2 data)
bands = prod.load(ok_bands, pixel_size=20.)
# NOTE: every array that comes out `load` are collocated, which isn't the case if you load arrays separately
# (important for DEM data as they may have different grids)
```

```{note}
Index and bands are opened as [`xarrays`](http://xarray.pydata.org/en/stable/)
with [`rioxarray`](https://corteva.github.io/rioxarray/stable/), in `float` with the nodata set to `np.nan`.
The nodata written back on disk is by convention:

- `-9999` for optical bands (saved in `float32`)
- `65535` for optical bands (saved in `uint16`)
- `0` for SAR bands (saved in `float32`), to be compliant with SNAP default nodata
- `255` for masks (saved in `uint8`)

For optical bands, only the pixels outside of the detector are set to nodata by default 
but this can be changed according to the user's needs (see below).
```

Some additional arguments can be passed to this function, please see {meth}`~eoreader.keywords` for the list.
- Methods to clean optical bands are best described [here](https://eoreader.readthedocs.io/latest/notebooks/optical_cleaning_methods.html),
- Sentinel-3 additional keywords use is highlighted in the [corresponding notebook](https://eoreader.readthedocs.io/latest/notebooks/sentinel-3.html).
- Windows can be passed to the `load` and `stack` functions ([notebook](https://eoreader.readthedocs.io/latest/notebooks/windowed_reading.html)).

💡 The bands will be opened with a chunk of `[1, TILE_SIZE, TILE_SIZE]` with `TILE_SIZE` coming from the 
[`EOREADER_TILE_SIZE` environment variable](https://eoreader.readthedocs.io/latest/api/eoreader.env_vars.TILE_SIZE.html#eoreader.env_vars.TILE_SIZE). 
The `TILE_SIZE` default value is 2048.


## Stack

{meth}`~eoreader.products.product.Product.stack()` is the function stacking all possible bands.
It is based on the load function and then just stacks the bands and write it on disk if needed.

The bands are ordered as asked in the stack.
However, they cannot be duplicated (the stack cannot contain 2 `RED` bands for instance)!
If the same band is asked several time, its order will be the one of the last demand.

```python
# Create a stack with the previous OK bands
stack = prod.stack(
  ok_bands,
  pixel_size=300.,
  stack_path=os.path.join(prod.output, "stack.tif")
)
```

Bands can be called with their name, ID or mapped name. 
For example, for Sentinel-3 OLCI you can use `7`, `Oa07` or `YELLOW`. For Landsat-8, you can use `BLUE` or `2`.

Some additional arguments can be passed to this function, please see {meth}`~eoreader.keywords` for the list.
- Methods to clean optical bands are best
  described [here](https://eoreader.readthedocs.io/latest/notebooks/optical_cleaning_methods.html),
- Sentinel-3 additional keywords use is highlighted in the [corresponding notebook](https://eoreader.readthedocs.io/latest/notebooks/sentinel-3.html).
- Windows can be passed to the `load` and `stack` functions ([notebook](https://eoreader.readthedocs.io/latest/notebooks/windowed_reading.html)).

## Read Metadata
EOReader gives you the access to the metadata of your product as a `lxml.etree._Element` followed by the namespace you may need to read them 

```python

# Access the raw metadata as an lxml.etree._Element and its namespaces as a dict:
mtd, nmsp = prod.read_mtd()

# You can access a field like that: 
datastrip_id = mtd.findtext(".//DATASTRIP_ID")
# 'S2B_OPER_MSI_L1C_DS_VGSR_20210929T075738_S20210517T104617_N79.90'

# Pay attention, for some products you will need a namespace, i.e. for planet data:
# name = mtd.findtext(f".//{nsmap['eop']}identifier")
```


```{note}
Landsat Collection 1 have no metadata with XML format, so the XML is simulated from the text file.
```

```{note}
Sentinel-3 constellations have no metadata file but have global attributes repeated in every NetCDF files.
This is what you will have when calling this function:

- `absolute_orbit_number`
- `comment`
- `contact`
- `creation_time`
- `history`
- `institution`
- `netCDF_version`
- `product_name`
- `references`
- `resolution`
- `source`
- `start_offset`
- `start_time`
- `stop_time`
- `title`
- `ac_subsampling_factor` (`OLCI` only)
- `al_subsampling_factor` (`OLCI` only)
- `track_offset` (`SLSTR` only)
```

## Plot
If a quicklook exists, the user can plot the product.
Always existing for VHR and SAR data, more rarely for other optical constellations.
See [Optical](https://eoreader.readthedocs.io/latest/notebooks/optical.html) and [SAR](https://eoreader.readthedocs.io/latest/notebooks/SAR.html) tutorials for examples.

```python
# Plot product
prod.plot()
```


## Other features

### CRS
Get the product CRS, always in UTM
```python
# Product CRS (always in UTM)
prod.crs()
# CRS.from_epsg(32630)
```

### Extent and footprint

Get the product extent and footprint, always in UTM as a `gpd.GeoDataFrame`

```python
# Full extent of the bands as a geopandas GeoDataFrame
prod.extent()
#                                            geometry
#0   POLYGON((309780.000 4390200.000, 309780.000 4...

# Footprint: extent of the useful pixels (minus nodata) as a geopandas GeoDataFrame
prod.footprint()
#                                            geometry
#0 POLYGON Z((199980.000 4390200.000 0.000, 1999...
```

Please note the difference between `footprint` and `extent`:

|Without nodata | With nodata|
|--- | ---|
| ![without_nodata](https://zupimages.net/up/21/14/69i6.gif) | ![with_nodata](https://zupimages.net/up/21/14/vg6w.gif) |

### Solar angles

Get optical product azimuth (between [0, 360] degrees) and
[zenith solar angles](https://en.wikipedia.org/wiki/Solar_zenith_angle), useful for computing the Hillshade for example.

```python
# Get azimuth and zenith solar angles
prod.get_mean_sun_angles()
# (81.0906721240477, 17.5902388851456)
```

### Cloud Cover

Get optical product cloud cover as specified in the metadata

```python
# Get cloud cover
prod.get_cloud_cover()
# 0.155752635193646
```

### Orbit direction

Get product optical direction (useful especially for SAR data), as a {meth}`~eoreader.product.OrbitDirection` (`ASCENDING` or `DESCENDING`).
Always specified in the metadata for SAR constellations, set to `DESCENDING` by default for optical data if not existing.

```python
# Get orbit direction
prod.get_orbit_direction()
# <OrbitDirection.DESCENDING: 'DESCENDING'>
```

## STAC

**EOReader** can help you create [SpatioTemporal Asset Catalog (STAC)](https://stacspec.org/) items from every supported products, included custom ones.
Those items are ready to be added in any STAC catalogue or collection. 
See [STAC Notebook](https://eoreader.readthedocs.io/latest/notebooks/stac.html) to learn more about this feature.

```python
# Get STAC object
prod.stac

# Create STAC item
prod.stac.create_item()
# <Item id = 20210517T103619_S2_T30QVE_L1C_075738>
```

Some functions have different names between EOReader and STAC vocabulary. 
For legacy purpose, this has not been changed. Hereunder is the mapping:
- `prod.stac.bbox` is equivalent to `prod.extent` but in `WGS84` (`EPSG:4326`)
- `prod.stac.proj.bbox` is equivalent to `prod.extent`
- `prod.stac.geometry` is equivalent to `prod.footprint` but in `WGS84` (`EPSG:4326`)
- `prod.stac.proj.geometry` is equivalent to `prod.footprint`
