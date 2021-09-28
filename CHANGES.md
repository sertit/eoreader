# Release History

## X.Y.Z (YYYY-MM-DD)

## 0.8.0 (2021-MM-DD)

- ENH: Removing raw `gdal` CLI from EOReader (the `HILLSHADE` and `SLOPE` bands are now slightly different !) #10
- ENH: `HILLSHADE` is given in `float32` instead of `uint8`
- FIX: `SLOPE` is given in degrees instead of percents
- DOC: Updating CSS and readme

## 0.7.0 (2021-09-23)

- **ENH: Implementing RADARSAT-Constellation products (as `RCM`)**
- **ENH: Implementing Maxar products (such as `GE01, WV02, WV03, WV04`, but others should be supported too)**
- **ENH: Implementing TanDEM-X products (as `TDX`)**
- **ENH: Adding `RH`, `RV`, `RH_DSPK` and `RV_DSPK` SAR bands**
- **ENH: Adding the `YELLOW` optical band (for `WorldView-2`, `WorldView-3` and `Sentinel-3 OLCI`)**
- **ENH: Adding [WorldView index](https://resources.maxar.com/optical-imagery/multispectral-reference-guide) (without
  the ones using SWIR)**
- **ENH: Loading by size -> round resolution to the closest meter (or decimeter for resolution < 1.0m)**
- **ENH: Super class for VHR data**
- FIX: Fixing reading PlanetScope archived products (error in read band)
- FIX: Fix band name with complex resolutions
- FIX: Fixing minor bug in RADARSAT-2 data when looking for product type
- FIX: Fixing SAR band search in BEAM-DIMAP files
- FIX: Fixing python version in environment.yml
- FIX: Discard unused MIR and FNIR bands
- FIX: Check for existence of given path when reading any product
- FIX: Workaround for a bug involving some downloaded but badly formatted archives for Sentinel-2
- FIX: Allow NARROW_NIR for and DIMAP data (== NIR)
- FIX: Better management of writeable band folder
- DOC: Fix documentation of the NDWI index
- DOC: Update graph for optical band mapping
- CI: Adding a test loading invalid band name
- CI: Setting CI log level to DEBUG
- CI: Accelerating the CI processes

## 0.6.4 (2021-09-15)

- FIX: Sentinel-3 band mapping (`Coastal Aerosol` <-> `03`, `BLUE` <-> `04`)
- DOC: Adding an interactive graph for optical band mapping

## 0.6.3 (2021-09-10)

- **ENH: Load works with string bands (`prod.load('BLUE')`)**
- FIX: Fixing missing `_remove_tmp_process` for products needing extraction
- FIX: Remove multi converting for Sentinel-3

## 0.6.2 (2021-09-10)

- FIX: Better handling of archives for products that needs extraction
- FIX: TerraSAR-X products need to be extracted to be processed by SNAP !

## 0.6.1 (2021-09-10)

- FIX: Fixing critical bug for Sentinel-3 (mapping between clean bands and SNAP bands)

## 0.6.0 (2021-09-02)

- **ENH: Ensuring EOReader supports Dask**
- FIX: Fixing and adding BAIS2 index in alias
- FIX: Fixing GLI index
- FIX: Fixing a bug when writing reprojected DIMAP band
- FIX: Fixing a bug with SCS Cosmo-SkyMed data
- DOC: Adding a DASK notebook
- DOC: Updating notebooks

## 0.5.0 (2021-08-24)

- **ENH: Adding the [BAIS2](https://www.researchgate.net/publication/323964124_BAIS2_Burned_Area_Index_for_Sentinel-2)
  index**
- **ENH: Read metadata/namespaces only once and store it as a private member. Keep accessing it through the `read_mtd`
  function (#9)**
  **WARNING**: Breaking change for Landsat: `read_mtd()` loses the argument `force_pd=True` as it always returns an
  Etree
- **ENH: Reads Sentinel-3 global attributes as metadata:**
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
- **ENH: Refining Despeckle Graph (#6) to use a more usual filter (`Refined Lee`)**
- **ENH: Allowing the user to open the datatake metadata for Sentinel-2 products**
- FIX: Decoupling classic metadata reading from the name as EOReader accepts now modified product names (#9)
- FIX: Better handling of cloud-stored DEM (raising an exception for non-ortho DIMAP data as GDAL and rasterio does not
  handle that case)
- FIX: `environment.yml` to respect the stricter use of `file:` syntax.
  See [here](https://stackoverflow.com/questions/68571543/using-a-pip-requirements-file-in-a-conda-yml-file-throws-attributeerror-fileno)
  for more information.
- FIX: Fixing bug when opening an archive product with `name` mode and nested dictionary (when looking for a filename
  instead of the directory name)
- CI: Fixing `test_dems_https` and resetting DEM afterwards
- CI: Fixing DEM and ds2 database management
- DOC: Adding a FAQ page and enhancing the Main Features page (#3)
- DOC: Read Metadata has its own paragraph in Main Features

## 0.4.8 (2021-07-23)

- **ENH: Allowing `stack` to take single band in input instead of a list**
- FIX: Fixing a regression loading optical bands which have been previously cleaned (Landsat, Theia, possibly
  PlanetScope)
- FIX: `load` and `stack` always returns `float32` arrays
- CI: Testing if loading 2 times a band gives the same result

## 0.4.7.post0 (2021-07-23)

- Fixing a regression loading Landsat bands which have been previously cleaned

## 0.4.7 (2021-07-23)

- **ENH: Adding a `default_transform` function returning data from default band (without warping it)**
  -> *mapping `calculate_default_transform` from `rasterio`*
- **ENH: Adding a `clean_tmp` function allowing the user to clean the product's temporary output by hand**
- **ENH: Simplifying DEM warping code**
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

- **ENH: Optimizing loading cloud bands for DIMAP Products**
- `stack` accepts `**kwargs` in order to pass options to `rioxarray.to_raster()`
- FIX: Fixing not found masks with S3+zip Sentinel-2 products
- FIX: Fixing some type hints
- CI: Fixing network directories with pathlib

## 0.4.2 (2021-07-01)

- **ENH: Enabling the use of products stored in the cloud
  (S3, S3 compatible storage, Google, Azure...) through [`cloudpathlib`](https://cloudpathlib.drivendata.org/)**
- **ENH: Using correct band names in long_name**
- CI: Use pre-computed cleaned band if existing
- DOC: Adding examples for using S3 data, especially for S3 compatible storage

## 0.4.1.post0 (2021-06-21)

- FIX: cloud mask values were inverted in Sentinel-2 cloud masks
- FIX: Landsat collection 2 cloud masks are now OK

## 0.4.1 (2021-06-21)

- FIX: Improving stacks saved as uint16:
    - Only satellite bands and index are scaled (*10.000)
    - DEM bands are just rounded
    - Cloud bands (booleans) are saved as is
- FIX: Fixing a rasterization bug affecting S2 and DIMAP masks, happening when the vectors have another size than the
  image
- FIX: Adding a warning on bad georeferencing when using GS and GT Landsat products
- CI: Minor updates in documentation and code

## 0.4.0 (2021-06-10)

### Features

- **ENH: Adding THR data support:**
    - **PlanetScope**
    - **Pleiades**
    - **SPOT 6-7**
- **ENH: Better handling of SNAP DEMs (using External DEM and other available SNAP DEMs)**

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
