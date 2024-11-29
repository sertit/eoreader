[![pypi](https://img.shields.io/pypi/v/eoreader.svg)](https://pypi.python.org/pypi/eoreader)
[![Conda](https://img.shields.io/conda/vn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)
[![Tests](https://github.com/sertit/eoreader/actions/workflows/test.yml/badge.svg)](https://github.com/sertit/eoreader/actions/workflows/test.yml)
[![Gitter](https://badges.gitter.im/eoreader/community.svg)](https://gitter.im/eoreader/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Apache](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sertit/eoreader/blob/master/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5082050.svg)](https://doi.org/10.5281/zenodo.5082050)
[![stars](https://img.shields.io/github/stars/sertit/eoreader?style=social)](https://github.com/sertit/eoreader)
[![Conda](https://img.shields.io/conda/dn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)

# ![eoreader_logo](https://eoreader.readthedocs.io/en/latest/_static/favicon.png) EOReader

**EOReader** is a remote-sensing opensource python library reading [optical](https://eoreader.readthedocs.io/en/latest/optical.html)
and [SAR](https://eoreader.readthedocs.io/en/latest/sar.html) constellations, loading and stacking bands,
clouds, DEM and spectral indices in a sensor-agnostic way.

> [!IMPORTANT] 
> 💡 The goal of this library is to manage one satellite product at a time.  
> To handle more complicated sets of products (such as mosaics, pairs or time series), please consider using [`EOSets`](https://github.com/sertit/eosets).

## 🛰️ Managed constellations

### Optical
[![Sentinel-2 SAFE and Theia Sentinel-3 OLCI and SLSTR Landsat 1 to 9 Harmonized Landsat-Sentinel PlanetScope, SkySat and RapidEye Pleiades and Pleiades-Neo SPOT-6/7 and 4/5 Vision-1 Maxar (WorldViews, GeoEye) SuperView-1 GEOSAT-2](https://zupimages.net/up/23/22/j3mz.png)](https://eoreader.readthedocs.io/en/latest/optical.html)

### SAR
[![Sentinel-1 COSMO-Skymed 1st and 2nd Generation TerraSAR-X, TanDEM-X and PAZ SAR RADARSAT-2 and RADARSAT-Constellation ICEYE SAOCOM Capella](https://zupimages.net/up/23/22/7b6k.png)](https://eoreader.readthedocs.io/en/latest/sar.html)

## 🔮 Features

EOReader implements **sensor-agnostic** features:

- [`load`](https://eoreader.readthedocs.io/en/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.load): Load many band types:
    - satellite bands ([optical](https://eoreader.readthedocs.io/en/latest/optical.html#satellite-bands) or [SAR](https://eoreader.readthedocs.io/en/latest/sar.html#sar-bands))
    - [index](https://eoreader.readthedocs.io/en/latest/optical.html#available-index)
    - [cloud bands](https://eoreader.readthedocs.io/en/latest/optical.html#cloud-bands)
    - [DEM bands](https://eoreader.readthedocs.io/en/latest/optical.html#dem-bands)
- [`stack`](https://eoreader.readthedocs.io/en/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.stack): Stack all these type of bands

EOReader works mainly with:
- [`xarrays.DataArray`](http://xarray.pydata.org/en/stable/generated/xarray.DataArray.html#xarray.DataArray) and [`xarrays.Dataset`](http://xarray.pydata.org/en/stable/generated/xarray.Dataset.html#xarray.Dataset) for raster data
- [`geopandas.GeoDataFrames`](https://geopandas.org/docs/user_guide/data_structures.html#geodataframe) for vector data (extents, footprints...)

## ⚡️ Quickstart

### Optical
EOReader allows you ta load and stack spectral bands, spetrcal indices, DEM and cloud bands agnostically from every handled optical constellation:

```python
from eoreader.reader import Reader
from eoreader.bands import RED, GREEN, BLUE, NDVI, CLOUDS

# Sentinel-2 path
s2_path = "S2B_MSIL1C_20181126T022319_N0207_R103_T51PWM_20181126T050025.SAFE"

# Create the reader object and open satellite data
reader = Reader()

# The reader will recognize the constellation from its product structure
s2_prod = reader.open(s2_path)

# Load some bands and index
bands = s2_prod.load([NDVI, GREEN, CLOUDS])

# Create a stack with some bands
stack = s2_prod.stack([RED, GREEN, BLUE], stack_path="s2_rgb_stack.tif")
```

EOReader aligns spectral bands from every handled sensor in order to make any call to a band generic:  
[![Optical Band Mapping](https://zupimages.net/up/23/40/0zgb.png)](https://eoreader.readthedocs.io/en/latest/optical_band_mapping.html)

### SAR
In the same way, you can import and stack radar band from any handled SAR constellation, with the same pattern.

```python
from eoreader.reader import Reader
from eoreader.bands import VV, VH, VV_DSPK, VH_DSPK

# Sentinel-1 GRD path
s1_path = "S1B_EW_GRDM_1SDH_20200422T080459_20200422T080559_021254_028559_784D.zip"

# Create the reader object and open satellite data
reader = Reader()

# The reader will recognize the constellation from its product structure
s1_prod = reader.open(s1_path)

# Load some bands and index
bands = s1_prod.load([VV, VH])

# Create a stack with some bands
stack = s1_prod.stack([VV_DSPK, VH_DSPK], stack_path="s1_stack.tif")
```

> [!WARNING] 
> ⚠️**SNAP and SAR**
>
> SAR products need [`ESA SNAP`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph)
> free software to be orthorectified and calibrated.
> Ensure that you have the folder containing your `gpt` executable in your `PATH`.
> If you are using SNAP 8.0, be sure to have your software up-to-date (SNAP version >= 8.0).

## 📖 Documentation

The API documentation can be found [here](https://eoreader.readthedocs.io/en/latest/).

## 🔗 Examples

Available notebooks provided as examples:

- [Why EOReader?](https://eoreader.readthedocs.io/en/latest/notebooks/why_eoreader.html)

### Basics 
- [Basic tutorial](https://eoreader.readthedocs.io/en/latest/notebooks/base.html)
- [Optical data](https://eoreader.readthedocs.io/en/latest/notebooks/optical.html)
- [SAR data](https://eoreader.readthedocs.io/en/latest/notebooks/SAR.html)
- [VHR data](https://eoreader.readthedocs.io/en/latest/notebooks/VHR.html)
- [Remove clouds](https://eoreader.readthedocs.io/en/latest/notebooks/remove_clouds.html)


### Advanced 
- [Sentinel-3 data](https://eoreader.readthedocs.io/en/latest/notebooks/sentinel-3.html)
- [Water detection on multiple products](https://eoreader.readthedocs.io/en/latest/notebooks/water_detection.html)
- [Windowed Reading](https://eoreader.readthedocs.io/en/latest/notebooks/windowed_reading.html)
- [DEM](https://eoreader.readthedocs.io/en/latest/notebooks/dem.html)
- [Custom stacks](https://eoreader.readthedocs.io/en/latest/notebooks/custom.html)
- [Methods to clean optical bands](https://eoreader.readthedocs.io/en/latest/notebooks/optical_cleaning_methods.html)
- [AWS storage](https://eoreader.readthedocs.io/en/latest/notebooks/aws.html)
- [S3 Compatible Storage](https://eoreader.readthedocs.io/en/latest/notebooks/s3_compatible_storage.html)

### Experimental
- [Dask](https://eoreader.readthedocs.io/en/latest/notebooks/dask.html)
- [STAC](https://eoreader.readthedocs.io/en/latest/notebooks/stac.html)

## 🛠 Installation

### Pip

You can install EOReader via pip:

`pip install eoreader`

EOReader mainly relies on `geopandas`, `xarray` and `rasterio` (through `rioxarray`).

Please look at the [rasterio page](https://rasterio.readthedocs.io/en/latest/installation.html) to learn more about that.

### Conda

You can install EOReader via conda:

```
conda config --env --set channel_priority strict
conda install -c conda-forge eoreader
```

## 📚 Context

As one of the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/) Rapid Mapping and Risk and Recovery Mapping operators, 
[SERTIT](https://sertit.unistra.fr/) needs to deliver geoinformation (such as flood or fire delineation, landslides mapping, etc.) based on multiple EO constellations.

In rapid mapping, it is always important to have access to various sensor types, resolutions, and satellites. Indeed, SAR sensors are able to detect through clouds and during nighttime 
(which is particularly useful during flood and storm events), while optical sensors benefit from of multi spectral bands to better analyze and classify the crisis information.

As every minute counts in the production of geoinformation in an emergency mode, it seemed crucial to harmonize the ground on which are built our production tools, in order to make them as
sensor-agnostic as possible.

This is why SERTIT decided to decouple the sensor handling from the extraction algorithms: the latter should be able to ingest semantic bands 
(i.e. `RED` or `VV`) without worrying about how to load the specific sensor band or in what unit it is.  
The assumption was made that all the spectral bands from optical sensors could be mapped between each other, in addition to the natural mapping between SAR bands.

Thus, thanks to **EOReader**, these tools are made independent to the constellation:  
✅ the algorithm (and its developer) can focus on its core tasks (such as extraction) without taking into account the sensor characteristics 
(how to load a band, which band correspond to which band number, …)  
✅ new sensor addition is effortless (if existing in **EOReader**) and requires no algorithm modification  
✅ maintenance is simplified and the code quality is significantly improved  
✅ testing is also simplified as the sensor-related parts are tested in EOReader library  

However, keep in mind that the support of all the constellations used in CEMS is done in the best effort mode, especially for commercial data.
Indeed, we may not have faced every product type, sensor mode or order configuration, so some details may be missing.
If this happens to you, do not hesitate to make a PR or write an issue about that !

## 🎤 Communication
### Talks

- [GeoPython 2022](https://submit.geopython.net/geopython-2022/talk/FQPN3Q/) [ [PDF](https://seafile.unistra.fr/f/be2b461af970465b903e/) ] [ [YouTube](https://www.youtube.com/watch?v=mKxOiRULOJA&t=14303s) ]
- Mentioned in **[Live+]SIG 2022 by ESRI France** (in French):
  `Enrichir ArcgisPro grâce à des processus personnalisés d'observation de la Terre`
  [ [PDF](https://seafile.unistra.fr/f/9502a14f142041468837/) ]
- Mentioned in GeoPython 2023 - `FLORIA, a custom python pipeline for urban flood extraction from SAR multi-sensors, supported by U-Net convolutional network.`
- Mentioned in EGU 2023 - [`Cutting-edge developments in rapid mapping`](https://doi.org/10.5194/egusphere-egu23-14143) 
- [FOSS4G 2023](https://talks.osgeo.org/foss4g-2023/talk/XJH7JE/) [ [PDF](https://seafile.unistra.fr/f/f727dc62cdfe471f9b33/) ] [ [YouTube](https://www.youtube.com/watch?v=3ZfPQrTypmQ) ]

### Press Release

- [ESA Success Story](https://earth.esa.int/eogateway/news/new-open-source-python-library-improves-rapid-mapping-services)
- Used to extract water for assessing agriculture impacts after the Kakhovka Dam Collapse (cross-post from [NASA Harvest](https://nasaharvest.org/index.php/news/navigating-kakhovka-dam-collapse-nasa-harvest-consortium-assesses-agriculture-impacts) and [Planet](https://www.planet.com/pulse/navigating-the-kakhovka-dam-collapse-nasa-harvest-consortium-assesses-agriculture-impacts-with-satellite-imagery/))

### Articles

- [Maxant, J. Braun, R. Caspard, M. Clandillon, S. ExtractEO, a Pipeline for Disaster Extent Mapping in the Context of Emergency Management. Remote Sens. 2022, 14, 5253. (Technical Note)](https://doi.org/10.3390/rs14205253)

### Blog

- [Introduction to EOReader](https://sertit.unistra.fr/en/news/introduction-to-eoreader/)
- [EOReader: Remote sensing open-source python library](https://sertit.unistra.fr/en/news/eoreader/)
- [The collapse of the Kakhovka dam seen from satellite imagery](https://sertit.unistra.fr/en/news/the-collapse-of-the-kakhovka-dam-seen-from-satellite-imagery/)

## 📝 License

**EOReader** is licensed under Apache License v2.0. See LICENSE file for details.

## 🖋️ Authors

**EOReader** has been created by [ICube-SERTIT](https://sertit.unistra.fr/).

## 🤝 Credits

**EOReader** is built on top of amazing libs, without which it couldn't have been coded:

- [`geopandas`](https://geopandas.org/)
- [`rasterio`](https://rasterio.readthedocs.io/en/latest/)
- [`xarray`](http://xarray.pydata.org/en/stable/)
- [`rioxarray`](https://corteva.github.io/rioxarray/stable/)
- [`awesome-spectral-indices` and `spyndex`](https://awesome-ee-spectral-indices.readthedocs.io/en/latest/index.html)
