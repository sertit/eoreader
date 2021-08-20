# Release History

## X.Y.Z (YYYY-MM-DD)

## 0.4.9 (2021-0X-XX)

- DOC: Adding a FAQ page (#3)
- FIX: Better handling of cloud-stored DEM (raising an exception for non-ortho DIMAP data as GDAL and rasterio does not handle that case)
- FIX: `environment.yml` to respect the stricter use of `file:` syntax.
  See [here](https://stackoverflow.com/questions/68571543/using-a-pip-requirements-file-in-a-conda-yml-file-throws-attributeerror-fileno)
  for more information.
- CI: Fixing `test_dems_https` and resetting DEM afterwards
- CI: Fixing DEM and ds2 database management
- DOC: Adding a FAQ page and enhancing the Main Features page (#3)

## 0.4.8 (2021-07-23)

- ENH: Allowing `stack` to take single band in input instead of a list
- FIX: Fixing a regression loading optical bands which have been previously cleaned (Landsat, Theia, possibly
  PlanetScope)
- FIX: `load` and `stack` always returns `float32` arrays
- CI: Testing if loading 2 times a band gives the same result

## 0.4.7.post0 (2021-07-23)

- Fixing a regression loading Landsat bands which have been previously cleaned

## 0.4.7 (2021-07-23)

- ENH: Adding a `default_transform` function returning data from default band (without warping it) -> *
  mapping `calculate_default_transform` from `rasterio`*
- ENH: Adding a `clean_tmp` function allowing the user to clean the product's temporary output by hand
- ENH: Simplifying DEM warping code
- FIX: `DIMAP` products return always projected (in UTM) default bands (`get_default_band_path`
  uses `_get_default_utm_band`)
- FIX: Theia Footprint returns a `GeoDataFrame` instead of a `GeoSeries`
- FIX: Better management of the `size` keyword with `load` and `stack` functions
- FIX: Landsat retrieval of multipart cleaned bands (like `SWIR_1`)
- FIX: Some typehints fixes
- FIX: Sentinel-3 open sun angles with NetCDF files stored in the cloud
- FIX: Silently pass the writing of clean bands if we cannot (like if permission error)
- CI: Do not reinstall everything if not needed (only PyYAML)
- CI: renaming `build` stage into `lint`
- CI: simplifying geometry comparison
- CI: Testing the `size` keyword for every sensor

## 0.4.6 (2021-07-19)

- FIX: Fixing no data for Sentinel-3 cloud bands
- FIX: In alias: `DeprecationWarning: using non-Enums in containment checks will raise TypeError in Python 3.8`
- CI: Set default S3 client to point to unistra's bucket
- CI: Tox SNAP relay S3_DB_URL_ROOT

## 0.4.5 (2021-07-13)

- Adding condensed name in the search when loading S3-SLSTR clouds
- FIX: Fixing no data for Sentinel-3 bands processed by SNAP
- FIX: Fix bug when stack path's directory doesn't exist

## 0.4.4 (2021-07-13)

- Do not verbose empty lists when loading optical bands
- Sentinel-3: Bands processed by SNAP are written with the condensed name as suffix

## 0.4.3.post1 (2021-07-08)

- BUG: Fixing another bug for DEM_PATH using S3 Paths
- Add a DOI

## 0.4.3.post0 (2021-07-08)

- BUG: Fixing DEM_PATH using S3 Paths

## 0.4.3 (2021-07-05)

- [DIMAP Products] Optimizing loading cloud bands
- `stack` accepts `**kwargs` in order to pass options to `rioxarray.to_raster()`
- Fixing not found masks with S3+zip Sentinel-2 products
- [CI] BUG: Fixing network directories with pathlib
- Fixing some type hints

## 0.4.2 (2021-07-01)

- Feature: Enabling the use of products stored in the cloud
  (S3, S3 compatible storage, Google, Azure...) through [`cloudpathlib`](https://cloudpathlib.drivendata.org/)
- Enhancement: Using correct band names in long_name
- CI: Use pre-computed cleaned band if existing
- Doc: Adding examples for using S3 data, especially for S3 compatible storage

## 0.4.1.post0 (2021-06-21)

- Bug fix: cloud mask values were inverted in Sentinel-2 cloud masks
- Bug fix: Landsat collection 2 cloud masks are now OK

## 0.4.1 (2021-06-21)

- Improving stacks saved as uint16:
    - Only satellite bands and index are scaled (*10.000)
    - DEM bands are just rounded
    - Cloud bands (booleans) are saved as is
- Fixing a rasterization bug affecting S2 and DIMAP masks, happening when the vectors have another size than the image
- Adding a warning on bad georeferencing when using GS and GT Landsat products
- Minor updates in documentation and code

## 0.4.0 (2021-06-10)

### Features

- Adding **THR** data support:
    - **PlanetScope**
    - **Pleiades**
    - **SPOT 6-7**
- [SAR] Better handling of SNAP DEMs (using External DEM and other available SNAP DEMs)

### Fix

- More robust way of looking for `data` directory
- Bug fix in `stack` that causes some bands to be inexplicably empty sometimes
- Bug fix in `alias.isindex`
- Forcing extent to UTM

### Optimizations

- Write clean bands on disk to avoid redoing invalid pixel computation and allow the user to remove them on deletion
- `prod.has_bands` / `prod.get_existing_bands` do not orthorectify/despeckle SAR bands anymore

### CI

- Adding a bimonthly test for SNAP processes

### Documentation

- Adding two new notebooks (SAR and VHR data)
- Completing the documentation

## 0.3.4 (2021-05-28)

- **Feature**: Introduced support for DEM files from web urls (starting with http(s)://)
- **Bug resolution**: Landsat Zenith angle computation (mixing elevation and zenith angle)
- **API change**: `read_mtd()` returns a dict for the namespace map in order to manage multi namespace XMLs
- **Signature change (invisible)**: Adding the band name in `_read_band()` to allow loading stacked bands
- **CI**: Adding weekly tests (`tox` on Python 3.7, 3.8, 3.9 on Linux and Windows)
- **Doc**: Updating documentation, setting DEM path as an environment variable

## 0.3.3 (2021-05-21)

- Migrating documentation to sphinx and readthedocs
- Refactoring documentation and ReadMe
- Bug correction when loading invalid masks for S2 sensor (fiona.errors.UnsupportedGeometryTypeError)

## 0.3.2.post2 (2021-05-04)

- Bug when reading cloud mask on Linux
- Log update in `product._check_dem_path()`
- README & documentation updates

## 0.3.2.post1 (2021-05-04)

- Do not use psutil in requirements and setup.py
- Typo in setup.py

## 0.3.2 (2021-05-04)

- In case of DEM bands, checks if the DEM is set and exists and raise an exception if not
- Setting minimum versions in setup.py and in requirements.txt
- ReadMe improvement
- Updating docs

## 0.3.1-post2 (2021-05-03)

- Bug in NDVI formula, typo when passing to xarray

## 0.3.1-post1 (2021-04-30)

- Correcting a broken link in setup.py
- Setting a minimum version of sertit
- Footprint:
    - Fixing a bug in the default function
    - Optimization for S2 and S2-Theia sensors
    - Fixing L7 footprint which was too complex due to nodata stripes
- CI:
    - Testing footprints and extent
    - Resolving non update of gitlab documentation
    - Changing the resolution of CI processes (to a multiple of the real resolution to speed up the computation)

## 0.3.1 (2021-04-29)

- Multiple optimizations when reading and processing the bands
- Bug resolutions:
    - S2-Theia masks
    - SAR DSPK bands always recomputed
    - SAR nodata set to 0 as SNAP expects it
    - Bad mask nodata setting when computing invalid pixels
    - Interverted default resolution between L4/5 MSS and TM sensors
- Removing useless logs when missing DEM but no computed DEM bands
- Adding copyright headers to every python files
- Fixing and adding examples

## 0.3.0 (2021-04-28)

- Going Open Source
