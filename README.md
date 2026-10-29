[![pypi](https://img.shields.io/pypi/v/eoreader.svg)](https://pypi.python.org/pypi/eoreader)
[![Conda](https://img.shields.io/conda/vn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)
[![Apache](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sertit/eoreader/blob/master/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5082050.svg)](https://doi.org/10.5281/zenodo.5082050)
[![stars](https://img.shields.io/github/stars/sertit/eoreader?style=social)](https://github.com/sertit/eoreader)
[![Conda](https://img.shields.io/conda/dn/conda-forge/eoreader.svg)](https://anaconda.org/conda-forge/eoreader)

# ![eoreader_logo](https://eoreader.readthedocs.io/latest/_static/favicon.png) EOReader

**EOReader** is a remote-sensing open-source Python library reading [optical](https://eoreader.readthedocs.io/latest/optical.html)
and [SAR](https://eoreader.readthedocs.io/latest/sar.html) constellations, loading and stacking bands,
clouds, DEM and spectral indices in a sensor-agnostic way.

> [!IMPORTANT] 
> 💡 The goal of this library is to manage one satellite product at a time.  
> To handle more complicated sets of products (such as mosaics, pairs or time series), please consider using [`EOSets`](https://github.com/sertit/eosets).

## 🛰️ Managed constellations

### Optical
[![Sentinel-2 SAFE and Theia Sentinel-3 OLCI and SLSTR Venus Landsat 1 to 9 Harmonized Landsat-Sentinel PlanetScope, SkySat and RapidEye, Satellogic (Aleph-1), Pleiades and Pleiades-Neo SPOT-6/7 and 4/5 Vision-1 Vantor/Maxar (WorldViews, GeoEye) SuperView-1 GEOSAT-2](https://zupimages.net/up/26/04/xtdk.png)](https://eoreader.readthedocs.io/latest/optical.html)

### SAR
[![Sentinel-1 COSMO-Skymed 1st and 2nd Generation TerraSAR-X, TanDEM-X and PAZ SAR RADARSAT-2 and RADARSAT-Constellation ICEYE SAOCOM Capella](https://i.postimg.cc/GhPpwwL7/sar-sensors.png)](https://eoreader.readthedocs.io/latest/sar.html)

## 🔮 Features

EOReader implements **sensor-agnostic** features:

- [`load`](https://eoreader.readthedocs.io/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.load): Load many band types:
    - satellite bands ([optical](https://eoreader.readthedocs.io/latest/optical.html#satellite-bands) or [SAR](https://eoreader.readthedocs.io/latest/sar.html#sar-bands))
    - [index](https://eoreader.readthedocs.io/latest/optical.html#available-index)
    - [cloud bands](https://eoreader.readthedocs.io/latest/optical.html#cloud-bands)
    - [DEM bands](https://eoreader.readthedocs.io/latest/optical.html#dem-bands)
- [`stack`](https://eoreader.readthedocs.io/latest/api/eoreader.products.product.Product.html#eoreader.products.product.Product.stack): Stack all these types of bands

EOReader works mainly with:
- [`xarray.DataArray`](http://xarray.pydata.org/en/stable/generated/xarray.DataArray.html#xarray.DataArray) and [`xarray.Dataset`](http://xarray.pydata.org/en/stable/generated/xarray.Dataset.html#xarray.Dataset) for raster data
- [`geopandas.GeoDataFrames`](https://geopandas.org/docs/user_guide/data_structures.html#geodataframe) for vector data (extents, footprints...)

EOReader allows you to create internal STAC catalogs directly from raw data.

> [!NOTE] 
> 💡 EOReader handles data from the past!  
> Legacy formats are mostly supported and if not, they can be requested by creating an issue with the `legacy_format` label.  
> This is super useful if you need to create an internal STAC catalog with old data.

## 🛠 Installation

### Pip

You can install EOReader via pip:

```bash
pip install eoreader
```

EOReader mainly relies on `geopandas`, `xarray` and `rasterio` (through `rioxarray`).

Please look at the [rasterio page](https://rasterio.readthedocs.io/en/latest/installation.html) to learn more about that.

### Conda

You can install EOReader via conda:

```
conda config --env --set channel_priority strict
conda install -c conda-forge eoreader
```

## ⚡️ Quickstart

### Optical
EOReader allows you to load and stack spectral bands, spectral indices, DEM and cloud bands agnostically from every handled optical constellation:

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

EOReader aligns spectral bands from every handled sensor to make any call to a band generic:  
[![Optical Band Mapping](https://zupimages.net/up/25/44/i20v.png)](https://eoreader.readthedocs.io/latest/optical_band_mapping.html)

### SAR
In the same way, you can import and stack radar bands from any handled SAR constellation, with the same pattern.

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

## 📖 Documentation

The API documentation can be found [here](https://eoreader.readthedocs.io/latest/).

## 🔗 Examples

Available notebooks provided as examples:

- [Why EOReader?](https://eoreader.readthedocs.io/latest/notebooks/why_eoreader.html): the motivation behind the library

### Basics
- [Basic tutorial](https://eoreader.readthedocs.io/latest/notebooks/base.html): first steps: open a product, load and stack bands
- [Optical data](https://eoreader.readthedocs.io/latest/notebooks/optical.html): spectral bands, indices, and cloud bands from optical constellations
- [SAR data](https://eoreader.readthedocs.io/latest/notebooks/SAR.html): radar bands with SNAP orthorectification
- [VHR data](https://eoreader.readthedocs.io/latest/notebooks/VHR.html): very high resolution sensors (Pleiades, WorldView, ...)
- [Remove clouds](https://eoreader.readthedocs.io/latest/notebooks/remove_clouds.html): cloud masking from brightness temperature measurements

### Advanced
- [Sentinel-3 data](https://eoreader.readthedocs.io/latest/notebooks/sentinel-3.html): OLCI and SLSTR band specificities
- [Water detection on multiple products](https://eoreader.readthedocs.io/latest/notebooks/water_detection.html): water extraction across several constellations over the same area
- [Windowed Reading](https://eoreader.readthedocs.io/latest/notebooks/windowed_reading.html): read a subset of a product instead of full bands
- [DEM](https://eoreader.readthedocs.io/latest/notebooks/dem.html): DEM bands (DEM, SLOPE, HILLSHADE) and orthorectification
- [Exogenous data](https://eoreader.readthedocs.io/latest/notebooks/exogenous_data.html): collocate external data onto the product grid
- [Custom stacks](https://eoreader.readthedocs.io/latest/notebooks/custom.html): read back stacks previously written by EOReader
- [Methods to clean optical bands](https://eoreader.readthedocs.io/latest/notebooks/optical_cleaning_methods.html): cleaning methods and their time cost
- [AWS storage](https://eoreader.readthedocs.io/latest/notebooks/aws.html): read products stored on AWS S3
- [S3 Compatible Storage](https://eoreader.readthedocs.io/latest/notebooks/s3_compatible_storage.html): read products from MinIO or other S3-compatible stores

### Experimental
- [Dask](https://eoreader.readthedocs.io/latest/notebooks/dask.html): lazy computation with dask-backed arrays
- [STAC](https://eoreader.readthedocs.io/latest/notebooks/stac.html): create SpatioTemporal Asset Catalog items from products

## 📚 Context

EOReader was created by [SERTIT](https://sertit.unistra.fr/) to support
[Copernicus Emergency Management Service](https://emergency.copernicus.eu/)
rapid mapping. See [CONTEXT.md](https://github.com/sertit/eoreader/blob/main/CONTEXT.md) for the full story.

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
- Used to extract water for assessing agriculture impacts after the Kakhovka Dam Collapse (cross-post from [NASA Harvest](https://www.nasaharvest.org/news/navigating-kakhovka-dam-collapse-nasa-harvest-consortium-assesses-agriculture-impacts) and [Planet](https://www.planet.com/pulse/navigating-the-kakhovka-dam-collapse-nasa-harvest-consortium-assesses-agriculture-impacts-with-satellite-imagery/))

### Articles

- [Maxant, J. Braun, R. Caspard, M. Clandillon, S. ExtractEO, a Pipeline for Disaster Extent Mapping in the Context of Emergency Management. Remote Sens. 2022, 14, 5253. (Technical Note)](https://doi.org/10.3390/rs14205253)

### Blog

- [Introduction to EOReader](https://sertit.unistra.fr/en/news/introduction-to-eoreader/)
- [EOReader: Remote sensing open-source python library](https://sertit.unistra.fr/en/news/eoreader/)
- [The collapse of the Kakhovka dam seen from satellite imagery](https://sertit.unistra.fr/en/news/the-collapse-of-the-kakhovka-dam-seen-from-satellite-imagery/)

## 🚀 Contributing

EOReader welcomes contributions, human-written or carefully reviewed AI-assisted:

- **Humans**: [CONTRIBUTING.md](https://github.com/sertit/eoreader/blob/main/CONTRIBUTING.md): quick start, test suite, PR conventions
- **Coding agents**: [AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md): hard limits, task navigation, verification & self-review
- **Technical reference**: [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md): architecture, modules, build & test, pitfalls
- **AI-assisted contribution policy**: [AI_POLICY.md](https://github.com/sertit/eoreader/blob/main/AI_POLICY.md)
- Task templates with AI-risk warnings: [.github/templates/](https://github.com/sertit/eoreader/tree/main/.github/templates)

## 📝 License

**EOReader** is licensed under Apache License v2.0. See LICENSE file for details.

## 🖋️ Authors

**EOReader** has been created by [ICube-SERTIT](https://sertit.unistra.fr/).

## 🤝 Credits

**EOReader** is built on top of amazing libs, without which it couldn't have been coded:

- [`geopandas`](https://geopandas.org/)
- [`rasterio`](https://rasterio.readthedocs.io/en/latest/)
- [`xarray`](http://xarray.pydata.org/en/stable/)
- [`rioxarray`](https://vylor.github.io/rioxarray/stable/)
- [`awesome-spectral-indices` and `spyndex`](https://awesome-spectral-indices.github.io/awesome-spectral-indices/)
