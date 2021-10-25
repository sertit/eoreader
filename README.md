[![pypi](https://img.shields.io/pypi/v/eoreader.svg)](https://pypi.python.org/pypi/eoreader)
[![Conda](https://img.shields.io/conda/vn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)
[![Tests](https://github.com/sertit/eoreader/actions/workflows/test.yml/badge.svg)](https://github.com/sertit/eoreader/actions/workflows/test.yml)
[![Gitter](https://badges.gitter.im/eoreader/community.svg)](https://gitter.im/eoreader/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Apache](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sertit/eoreader/blob/master/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5082051.svg)](https://doi.org/10.5281/zenodo.5082051)

# ![eoreader_logo](https://eoreader.readthedocs.io/en/latest/_static/favicon.png) EOReader

**EOReader** is a remote-sensing opensource python library reading [optical](https://eoreader.readthedocs.io/en/latest/optical.html)
and [SAR](https://eoreader.readthedocs.io/en/latest/sar.html) sensors, loading and stacking bands,
clouds, DEM and index in a sensor-agnostic way.

|**Optical sensors** | **SAR sensors**|
| --- | ---|
|Sentinel-2 and Sentinel-2 Theia<br>Sentinel-3 OLCI and Sentinel-3 SLSTR<br>Landsat 1 to 8 (MSS, TM, ETM and OLCI)<br>PlanetScope<br>Pleiades<br>SPOT 6-7<br>WorldView-2 to 4, GeoEye-1 (and other Maxar sensors)| Sentinel-1<br>COSMO-Skymed<br>TerraSAR-X, TanDEM-X & PAZ<br>RADARSAT-2<br>RADARSAT-Constellation|

It also implements additional **sensor-agnostic** features:

- [`load`](https://eoreader.readthedocs.io/en/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.load): Load many band types:
    - satellite bands ([optical](https://eoreader.readthedocs.io/en/latest/optical.html#satellite-bands) or [SAR](https://eoreader.readthedocs.io/en/latest/sar.html#sar-bands))
    - [index](https://eoreader.readthedocs.io/en/latest/optical.html#available-index)
    - [cloud bands](https://eoreader.readthedocs.io/en/latest/optical.html#cloud-bands)
    - [DEM bands](https://eoreader.readthedocs.io/en/latest/optical.html#dem-bands)
- [`stack`](https://eoreader.readthedocs.io/en/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.stack): Stack all these type of bands

EOReader works with [`xarrays.DataArray`](http://xarray.pydata.org/en/stable/generated/xarray.DataArray.html#xarray.DataArray)
and [`geopandas.GeoDataFrames`](https://geopandas.org/docs/user_guide/data_structures.html#geodataframe)


## Python Quickstart

The main features of EOReader are gathered hereunder.
For optical data:

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Landsat-5 MSS path, can be found in CI/DATA
>>> l5_path = "LM05_L1TP_200029_19841014_20200902_02_T2.tar"

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()
>>> l5_prod = eoreader.open(l5_path)  # The Reader will recognize the satellite type from its structure

>>> # Specify a DEM to load DEM bands
>>> import os
>>> from eoreader.env_vars import DEM_PATH
>>> os.environ[DEM_PATH] = "my_dem.tif"

>>> # Load some bands and index: they will all share the same metadata
>>> bands = l5_prod.load([NDVI, GREEN, HILLSHADE, CLOUDS])

>>> # Create a stack with some other bands
>>> stack = l5_prod.stack([NDWI, RED, SLOPE])

>>> # Read Metadata
>>> mtd, namespace = l5_prod.read_mtd()
```

For SAR data:

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Sentinel-1 GRD path, not provided in package
>>> s1_path = "S1B_EW_GRDM_1SDH_20200422T080459_20200422T080559_021254_028559_784D.zip"

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()
>>> s1_prod = eoreader.open(s1_path)  # The Reader will recognize the satellite type from its name

>>>  # Specify a DEM to load DEM bands
>>> import os
>>> from eoreader.env_vars import DEM_PATH
>>> os.environ[DEM_PATH] = "my_dem.tif"

>>> # Load some bands and index: they will all share the same metadata
>>> bands = s1_prod.load([VV, VV_DSPK, DEM])

>>> # Create a stack with some other bands
>>> stack = s1_prod.stack([VV, VV_DSPK, SLOPE])

>>> # Read Metadata
>>> mtd, namespace = s1_prod.read_mtd()
```

SAR products need [`SNAP gpt`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to be orthorectified and calibrated.
Ensure that you have the folder containing your `gpt` executable in your `PATH`.

## Documentation
The API documentation can be found [here](https://eoreader.readthedocs.io/en/latest/).

## Examples

Available notebooks provided as examples:

- [Basic tutorial](https://eoreader.readthedocs.io/en/latest/notebooks/base.html)
- [SAR data](https://eoreader.readthedocs.io/en/latest/notebooks/SAR.html)
- [VHR data](https://eoreader.readthedocs.io/en/latest/notebooks/VHR.html)
- [Sentinel-3 data](https://eoreader.readthedocs.io/en/latest/notebooks/sentinel-3.html)
- [Water detection](https://eoreader.readthedocs.io/en/latest/notebooks/water_detection.html)
- [S3 Compatible Storage](https://eoreader.readthedocs.io/en/latest/notebooks/s3_compatible_storage.html)
- [Dask](https://eoreader.readthedocs.io/en/latest/notebooks/dask.html)

## Installation

### Pip

You can install EOReader via pip:

`pip install eoreader`

EOReader mainly relies on `geopandas` and `rasterio` (through `rioxarray`).

On Windows and with pip, you may face installation issues due to GDAL.
The well known workaround of installing from [Gohlke's wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio)
also applies here.
Please look at the [rasterio page](https://rasterio.readthedocs.io/en/latest/installation.html)
to learn more about that.

### Conda

You can install EOReader via conda:

`conda config --env --set channel_priority strict`

`conda install -c conda-forge eoreader`

## Context

SERTIT is part of the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/)
rapid mapping and risk and recovery teams.

In these activations, we need to deliver information (such as flood or fire delineations, landslides mapping, etc.)
based on various sensors (more than 10 optical and 5 SAR). As every minute counts in production,
it seemed crucial to harmonize the ground on which are built our production tools, in order to make them
as sensor-agnostic as possible.

Thus, thanks to **EOReader**, these tools are made independent to the sensor:
- the algorithm (and its developer) can focus on its core tasks (such as extraction)
without taking into account the sensor characteristics
(how to load a band, which band correspond to which band number, which band to use for this index...)
- the addition of a new sensor is done effortlessly (if existing in **EOReader**) and without any modification of the algorithm
- the maintenance is simplified and the code is way more readable (no more ifs regarding the sensor type!)
- the testing is also simplified as the sensor-related parts are tested in this library

## License

**EOReader** is licensed under Apache License v2.0. See LICENSE file for details.

## Authors

**EOReader** has been created by [ICube-SERTIT](https://sertit.unistra.fr/).

## Credits

**EOReader** is built on top of amazing libs, without which it couldn't have been coded:

- [`geopandas`](https://geopandas.org/)
- [`rasterio`](https://rasterio.readthedocs.io/en/latest/)
- [`xarray`](http://xarray.pydata.org/en/stable/)
- [`rioxarray`](https://corteva.github.io/rioxarray/stable/)
