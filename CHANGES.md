# Release History

## 0.9.5 (2021-12-14)

- FIX: Do not force import `methodtools` (not existing lib in conda)
- FIX: Using `GRD` resolution given by the constructors as default values for `SLC` products. Do not look it up in
  metadata as SLC resolution is **NOT** the GRD resolution !

## 0.9.4 (2021-12-13)

- FIX: Caching properties and functions only for object instances
- FIX: Fixing metadata reading for `COSMO-SkyMed 1st Generation` with `Wide Region` and complex product type (handling
  of multiple swaths)
- FIX: Updates of SNAP GPT graphs for complex SAR data
- FIX: Interpolate nodata inside SAR images (badly handled by SNAP -> fill the gaps that shouldn't exist)
- INTERNAL: Creation of a class `CosmoProduct` handling generic methods for both `COSMO-SkyMed` generations

## 0.9.3 (2021-12-09)

- FIX: Fixing the search for `.TIL` files for `Maxar` products (with on disk files)
- FIX: Fixing the search for metadata files for `Landsat` products (with on disk files)
- FIX: Fixing the search for metadata files for `TerraSAR-X`, `TanDEM-X` and `PAZ SAR` products (with on disk files)
- FIX: Fixing SNAP files for `TerraSAR-X`, `TanDEM-X` and `PAZ SAR` products
- FIX: Fixing when reading CRS code for `DIMAP` products

## 0.9.2 (2021-12-07)

- FIX: Fixing flag type for `Sentinel-3` data
- FIX: Do not multiply the flags values by the radiance adjustment factor for `Sentinel-3 SLSTR`!
- FIX: Fixing flag exception threshold for `Sentinel-3 SLSTR`
- FIX: Fixing preprocessed band filenames for `Sentinel-3 SLSTR`

## 0.9.1 (2021-12-07)

- FIX: `Reader().valid_mtd` now correctly accepts strings instead of only `Platform` objects
- FIX: Better handling of `Sentinel-2` product type
- FIX: Save bands' new attributes in `str` (to pickle them)
- FIX: Add a `clear()` function to clear products cache

## 0.9.0 (2021-12-06)

- **ENH: Adding the support of the ICEYE sensor**
- **ENH: Adding the support of the COSMO-SkyMed 2nd Generation sensor**
- **ENH: Adding some attributes to bands and stack: `sensor`, `sensor_id`, `product_type`, `acquisition_date`
  , `condensed_name`** [#7](https://github.com/sertit/eoreader/issues/7)
- **ENH: Replace name by filename and read directly the true name of the product in the
  metadata** [#15](https://github.com/sertit/eoreader/issues/15)
- FIX: `Sentinel-1` metadata file with archived products (discarding RFI folder in its search).
- FIX: Add `Quickbird`, `GeoEye` and `WorldView` sensors in `reader` regexes.
- FIX: Add scipy in `requirements.txt` and `setup.py`
- DOC: Fix references to `pcigeomatics` that doesn't exist anymore (RADARSAT-2 and Constellation)
- REQ: Update `dask` to fix a security issue (only in requirements as `dask` is not mandatory)

## 0.8.1 (2021-10-26)

- FIX: Do not force `chunk` in `utils.read` if dask is not installed

## 0.8.0 (2021-10-25)

- **BREAKING CHANGE: `crs`, `footprint`, `extent`, `wgs84_extent` are now properties !**
- **BREAKING CHANGE: Removing raw `gdaldem` CLI from EOReader (the `HILLSHADE` and `SLOPE` bands are now slightly
  different !)** [#10](https://github.com/sertit/eoreader/issues/10)
- **BREAKING CHANGE: `HILLSHADE` is given in `float32` instead of `uint8`**
- **BREAKING CHANGE: `SLOPE` is given in degrees instead of percents**
- **ENH: Adding the support of the PAZ SAR sensor**
- **ENH: Adding the support of the Sentinel-2 processed with
  the [processing baseline 4.0](https://sentinels.copernicus.eu/web/sentinel/-/copernicus-sentinel-2-major-products-upgrade-upcoming)** [#11](https://github.com/sertit/eoreader/issues/11)
- **ENH: Removing SNAP from Sentinel-3 pre-process -> Freeing optical data from SNAP
  dependency !** [#12](https://github.com/sertit/eoreader/issues/12)
- **ENH: Enabling the use of other S3-SLSTR suffixes than `an` (stripe A at nadir position)**
- **ENH: Thermal bands of Sentinel-3 SLSTR can now be used**
- **ENH: All bands of Sentinel-3 SLSTR/OLCI can now be used (`S7`, `F1`, `F2` for SLSTR, `Oaxx` for
  OLCI)** [#14](https://github.com/sertit/eoreader/issues/14)
- **ENH: `YELLOW` band is mapped to `Oa07` band of Sentinel-3 OLCI**
- **ENH: Zipped Sentinel-3 products can now be processed**
- **ENH: Allow the use of `kwargs` in `load`, mainly for `rasters.read` (and allowing ie. radiance adjustment in
  S3-SLSTR)**
- OPTIM: `crs`, `footprint`, `extent`, `default_transform`, `wgs84_extent` are cached (
  using `@cached_property`) [#13](https://github.com/sertit/eoreader/issues/13)
- OPTIM: `get_mean_sun_angles` and `default_transform` are now cached (
  using `@cache`) [#13](https://github.com/sertit/eoreader/issues/13)
- OPTIM: `get_datetime`: Look for the date only if `datetime` attribute is
  None [#13](https://github.com/sertit/eoreader/issues/13)
- OPTIM: Better management of `fspath` for cloud-stored products (download the files only once)
- OPTIM: Stop downloading/extracting files if not necessary
- FIX: Bands are correctly ordered in stacks
- FIX: Only load a band once, even if asked several time in the bands
- FIX: Use band size for cleaning optical pixel (instead of user resolution/size)
- FIX: Always take the absolute value of the resolution when converting it to strings (for filenames)
- FIX: Take the default resolution if nothing is given when converting it to strings (for filenames)
- FIX: Always use `utils.read/write` instead of `rasters.read/write` (for Dask management)
- FIX: Fixing a bug in `utils.write`
- FIX: Add .xml files from `eoreader/data` in the MANIFEST.in
- FIX: Add forgotten `@abstractmethod` where needed
- FIX: Better management of `_tmp_process`
- FIX: Fixing minor bug when trying to read metadata with a POSIX path
- FIX: Fixing the `**kwargs` omission in `utils.read`
- FIX: Better management of `_temp_process` directory
- FIX: Landsats and TSX: Can use other filenames now
- DEPR: `FAR_NIR` band is removed
- REQ: Using `h5netcdf` instead of `netCDF4`
- DOC: Add a Context paragraph in the README
- DOC: Add a Conda x SNAP question in the FAQ
- DOC: Creation of a Sentinel-3 notebook
- DOC: Updates of notebooks
- DOC: Numerous updates

## 0.7.1 (2021-09-29)

- FIX: Fixing a bug when opening archived Sentinel-1 (wrong metadata file found)
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
