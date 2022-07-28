[![pypi](https://img.shields.io/pypi/v/eoreader.svg)](https://pypi.python.org/pypi/eoreader)
[![Conda](https://img.shields.io/conda/vn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)
[![Tests](https://github.com/sertit/eoreader/actions/workflows/test.yml/badge.svg)](https://github.com/sertit/eoreader/actions/workflows/test.yml)
[![Gitter](https://badges.gitter.im/eoreader/community.svg)](https://gitter.im/eoreader/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Apache](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sertit/eoreader/blob/master/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6605956.svg)](https://doi.org/10.5281/zenodo.6605956)
[![stars](https://img.shields.io/github/stars/sertit/eoreader?style=social)](https://github.com/sertit/eoreader)
[![Conda](https://img.shields.io/conda/dn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/eoreader.svg?style=social&label=EOReader)](https://twitter.com/eoreader)

# ![eoreader_logo](https://eoreader.readthedocs.io/en/latest/_static/favicon.png) EOReader

**EOReader** is a remote-sensing opensource python library reading [optical](https://eoreader.readthedocs.io/en/latest/optical.html)
and [SAR](https://eoreader.readthedocs.io/en/latest/sar.html) constellations, loading and stacking bands,
clouds, DEM and spectral indices in a sensor-agnostic way.

| **Optical**                                                                                                                                                                                                                                        | **SAR**|
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| ---|
| `Sentinel-2` and `Sentinel-2 Theia`<br>`Sentinel-3 OLCI` and `SLSTR`<br>`Landsat` 1 to 9<br>`PlanetScope` and `SkySat`<br>`Pleiades` and `Pleiades-Neo`<br>`SPOT-6/7`<br>`SPOT-4/5`<br>`Vision-1`<br>`Maxar` (WorldViews, GeoEye)<br>`SuperView-1` | `Sentinel-1`<br>`COSMO-Skymed` 1st and 2nd Generation<br>`TerraSAR-X`, `TanDEM-X` and `PAZ SAR`<br>`RADARSAT-2` and `RADARSAT-Constellation`<br>`ICEYE`<br>`SAOCOM`|

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

### Optical

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands import *

>>> # Sentinel-2 path
>>> s2_path = "S2B_MSIL1C_20181126T022319_N0207_R103_T51PWM_20181126T050025.SAFE"

>>> # Create the reader object and open satellite data
>>> reader = Reader()

>>> # The reader will recognize the constellation from its product structure
>>> s2_prod = reader.open(s2_path)

>>> # Load some bands and index
>>> bands = s2_prod.load([NDVI, GREEN, CLOUDS])

>>> # Create a stack with some bands
>>> stack = s2_prod.stack([RED, GREEN, BLUE], stack_path="s2_rgb_stack.tif")
```

### SAR

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands import *

>>> # Sentinel-1 GRD path
>>> s1_path = "S1B_EW_GRDM_1SDH_20200422T080459_20200422T080559_021254_028559_784D.zip"

>>>  # Create the reader object and open satellite data
>>> reader = Reader()

>>> # The reader will recognize the constellation from its product structure
>>> s1_prod = reader.open(s1_path)

>>> # Load some bands and index
>>> bands = s1_prod.load([VV, VV_DSPK])

>>> # Create a stack with some bands
>>> stack = s1_prod.stack([VV, VV_DSPK], stack_path="s1_vv_stack.tif")
```

> ⚠️**SNAP and SAR**
>
> SAR products need [`ESA SNAP`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph)
> free software to be orthorectified and calibrated.
> Ensure that you have the folder containing your `gpt` executable in your `PATH`.

## Documentation
The API documentation can be found [here](https://eoreader.readthedocs.io/en/latest/).

## Examples

Available notebooks provided as examples:

- [Why EOReader?](https://eoreader.readthedocs.io/en/latest/notebooks/why_eoreader.html)
- [Basic tutorial](https://eoreader.readthedocs.io/en/latest/notebooks/base.html)
- [Optical data](https://eoreader.readthedocs.io/en/latest/notebooks/optical.html)
- [SAR data](https://eoreader.readthedocs.io/en/latest/notebooks/SAR.html)
- [VHR data](https://eoreader.readthedocs.io/en/latest/notebooks/VHR.html)
- [Sentinel-3 data](https://eoreader.readthedocs.io/en/latest/notebooks/sentinel-3.html)
- [Water detection on multiple products](https://eoreader.readthedocs.io/en/latest/notebooks/water_detection.html)
- [DEM](https://eoreader.readthedocs.io/en/latest/notebooks/dem.html)
- [Custom stacks](https://eoreader.readthedocs.io/en/latest/notebooks/custom.html)
- [Methods to clean optical bands](https://eoreader.readthedocs.io/en/latest/notebooks/optical_cleaning_methods.html)
- [S3 Compatible Storage](https://eoreader.readthedocs.io/en/latest/notebooks/s3_compatible_storage.html)
- [Dask](https://eoreader.readthedocs.io/en/latest/notebooks/dask.html)
- [STAC](https://eoreader.readthedocs.io/en/latest/notebooks/stac.html)

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

```
conda config --env --set channel_priority strict
conda install -c conda-forge eoreader
```

## Context

SERTIT is part of the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/)
rapid mapping and risk and recovery teams.

In these activations, we need to deliver information (such as flood or fire delineations, landslides mapping, etc.)
based on various constellations (more than 10 optical and 5 SAR). As every minute counts in production,
it seemed crucial to harmonize the ground on which are built our production tools, in order to make them
as sensor-agnostic as possible.

Thus, thanks to **EOReader**, these tools are made independent to the constellation:
- the algorithm (and its developer) can focus on its core tasks (such as extraction)
without taking into account the constellation characteristics
(how to load a band, which band correspond to which band number, which band to use for this index...)
- the addition of a new constellation is done effortlessly (if existing in **EOReader**) and without any modification of the algorithm
- the maintenance is simplified and the code is way more readable (no more ifs regarding the sensor type!)
- the testing is also simplified as the sensor-related parts are tested in this library

However, keep in mind that the support of all the constellations used in CEMS is done in a best effort mode, especially for commercial data.
Indeed, we may not have faced every product type, sensor mode or order configuration, so some details may be missing.
If this happens to you, do not hesitate to make a PR or write an issue about that !

## Talks

- GeoPython 2022 [ [PDF](https://seafile.unistra.fr/f/be2b461af970465b903e/) ] [ [YouTube](https://www.youtube.com/watch?v=mKxOiRULOJA&t=14303s) ]

## Press Release

- [ESA Success Story](https://earth.esa.int/eogateway/news/new-open-source-python-library-improves-rapid-mapping-services)

## Talks

- GeoPython 2022 [ [PDF](https://seafile.unistra.fr/f/be2b461af970465b903e/) ] [ [YouTube](https://www.youtube.com/watch?v=mKxOiRULOJA&t=14303s) ]

## License

**EOReader** is licensed under Apache License v2.0. See LICENSE file for details.

## Authors

**EOReader** has been created by [ICube-SERTIT](https://sertit.unistra.fr/).
Follow us on [twitter](https://twitter.com/eoreader)

## Credits

**EOReader** is built on top of amazing libs, without which it couldn't have been coded:

- [`geopandas`](https://geopandas.org/)
- [`rasterio`](https://rasterio.readthedocs.io/en/latest/)
- [`xarray`](http://xarray.pydata.org/en/stable/)
- [`rioxarray`](https://corteva.github.io/rioxarray/stable/)
