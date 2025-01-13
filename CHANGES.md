# Release History

## 0.21.8 (2024-01-13)

- ENH: Add a new type (`BandsType`) for list of BandType
- ENH: Add a new environment variable `EOREADER_NOF_BANDS_IN_CHUNKS` to control the number of the bands in chunks when using `dask`. ([#178](https://github.com/sertit/eoreader/discussions/178))
- ENH: Allow `'auto'` in `EOREADER_TILE_SIZE`, to set `chunks="auto"` when reading data. ([#178](https://github.com/sertit/eoreader/discussions/178))
- FIX: Fix stack `save_as_int` to use updated int values - by @TabeaW
- FIX: Fixed PAZ Product Regex to properly indentify PAZ ST products as `PAZProduct` - by @guillemc23
- FIX: Fixed PNEO Product Regex to properly indentify PNEO products as `PneoProduct` - by @guillemc23
- FIX: Fixed preprocessing graph paths in order to support relative paths in more complex environments or contexts - by @guillemc23
- FIX: Remove useless `_norm_diff` function `indices.py`
- FIX: Add a fallback in case `map-overlay.kml` is not readable for `Sentinel-1` data ([#180](https://github.com/sertit/eoreader/discussions/180),[#182](https://github.com/sertit/eoreader/issues/182))
- FIX: Remove warning about Dask's lock and client
- FIX: Don't throw an error in case of missing cloud coverage, only a warning and set the cloud coverage to 0 [#159](https://github.com/sertit/eoreader/issues/159)
- FIX: Use the sun elevation angle rather than the sun zenith angle for STAC [#158](https://github.com/sertit/eoreader/issues/158)
- FIX: Create comparison operators for `BandNames`, removing the `xarray RuntimeWarning` about `sort order is undefined for incomparable objects`.
- FIX: Add some missing `@cache` around time-consuming functions
- FIX: Set correctly the SAR product type, with adding two types (`ORTHO` and `GEOCODED`)
- FIX: Fix the computation of parametric spectral indices [#193](https://github.com/sertit/eoreader/issues/193)
- FIX: Fix retrieval of quicklook path for SAOCOM when already computed
- FIX: Write data using `windowed=True` for very big rasters (> 50 Go) to avoid core dumps
- FIX: Fix management of numpy temporary files saved on disk
- OPTIM: Cache the access to any archived file list, as this operation is expensive when done with large archives stored on the cloud (and thus better done only once).
- CI: Remove useless verbosity in CI
- CI: GDAL performance tuning by tweaking `rasterio`'s env
- INTERNAL: Switch from `setup.py` to `pyproject.toml` [#109](https://github.com/sertit/eoreader/issues/109)
- INTERNAL: Use `ruff` instead of `black` + `flake8` + `isort`
- DOC: Update `conf.py` (remove useless hunks and set Sphinx 7 as base)
- DOC: Added the [PAZ product guide](https://earth.esa.int/eogateway/documents/20142/37627/PAZ-Image-Products-Guide.pdf) to the PAZ Product documentation instead of the TerraSAR-X one - by @guillemc23
- DEPS: Pin `sertit>=1.44.1`

## 0.21.7 (2024-11-08)

- FIX: Handle `ICEYE` products with missing quicklook
- FIX: Fix `Sentinel-1` name with weird PDFs names (i.e. ending with `.SAFE-report...`)
- FIX: Remove multi-swath workaround for `Cosmo` products if SNAP > 11.0
- FIX: By default, try to assign a constellation (in a pure dummy way) to any `Product` created
- FIX: Add ways of knowing if a constellation is a real one or not (i.e. `CUSTOM` or template such as `Maxar`)
- FIX: Create `TDX` and `PAZ` (completely inherited) classes to disambiguate their constellations

## 0.21.6 (2024-10-17)

- FIX: Fix (really) window's name coming from a vector with an underscore after it
- FIX: Fix clean band path for Sentinel-3 SLSTR products
- FIX: Remove an ignored exception when deleting a Product (`ValueError: Unknown '__class__' name in 'covariance.compute' hyperparameters`)

## 0.21.5 (2024-10-17)

- FIX: Fix window's name coming from a vector with an underscore after it
- FIX: Allow to load numpy pickles stored in S3 buckets
- FIX: Add MS and PAN resolution in Landsat Products

## 0.21.4 (2024-10-08)

- DEPS: Don't force using geopandas 1.0.0, 0.14.4 should be enough.

## 0.21.3 (2024-10-08)

- ENH: Allow the process of Sentinel-1 COGs (provided by the Copernicus DataSpace) for SNAP >= 10  ([#172](https://github.com/sertit/eoreader/issues/172))
- ENH: Add a `BandType` alias for any types that could be a band: a string, a `BandNames` or any of its children: Spectral, SAR, DEM or Cloud band names 
- FIX: Anticipate Sentinel C and D platforms in Reader's regexes
- FIX: Resolve the inversion of resolution and pixel size between `stripmap` and `sliding_spotlight` types for `Capella` products
- FIX: Get better window name (if available) when writing bands on disk (in tmp folder) 
- FIX: Reject buggy Maxar products (with version 28.4) as the workaround would be too heavy to implement. ([#106](https://github.com/sertit/eoreader/issues/106))
- FIX: Fix Despeckle graph with SNAP10 ([#177](https://github.com/sertit/eoreader/issues/177))
- OPTIM: Save rasterized masks of DIMAP V2 products on disk to avoid recomputing them (`features.rasterize` could be a heavy computation that shouldn't be done twice)
- COMPAT: EOReader works correctly with SNAP 10 ([#165](https://github.com/sertit/eoreader/issues/165))
- PUBLISH: Use PyPI's Trusted Publisher Management mechanism

## 0.21.2 (2024-07-30)

- ENH: `to_str` and `to_band`: add a `as_list` argument defaulting to `True`. When set as False, return a str from `to_str` and a band from `to_band` ([#138](https://github.com/sertit/eoreader/issues/138)). Thanks @jsetty!
- FIX: `Sentinel-2` product with `StopIteration` error ([#142](https://github.com/sertit/eoreader/issues/142))
- FIX: Fix error in looking for bands in `Sentinel-2 L1C` archived products ([#168](https://github.com/sertit/eoreader/issues/168))
- FIX: Fix issue with geocoding with unzipped `Sentinel-3 OLCI` product ([#137](https://github.com/sertit/eoreader/issues/137))
- FIX: In `SPOT` products, METADATA.DIM and IMAGERY.TIF must be at the root of the product ([#145](https://github.com/sertit/eoreader/issues/145))
- FIX: Fix `Maxar` product with `QB02` satellite ID ([#140](https://github.com/sertit/eoreader/issues/140))
- FIX: Fix `ICEYE` product when extent file (*.kml) not found ([#135](https://github.com/sertit/eoreader/pull/135))
- FIX: Handle `RCM` and `RS2` products that doesn't bundle their extent in a KML file ([#155](https://github.com/sertit/eoreader/issues/155))
- FIX: Handle wrongly recognized `Planet` products because of the recursive nested mtd in the Reader ([#169](https://github.com/sertit/eoreader/issues/169))
- FIX: Fix an unknown `Planet` bug that just appeared (`'...Path' has no len()`)
- FIX: Force the loading of `DimapV1` bands in `float32`
- FIX: Handle the case where `fiona` isn't installed anymore (with `geopandas 1.0`)
- FIX: Don't make `pystac` a mandatory requirement
- OPTIM: Search correctly nested metadata in the Reader (without accidentally using a recursive glob)
- CI: Fix S3 endpoint management with `sertit>=1.37`
- CI: Remove for now end-to-end tests with Python 3.11 and 3.10. 
- INSTALL: Remove `pystac[validation]` (as it is an optional dependency) from setup.py, and create a `stac` extra feature.

## 0.21.1 (2024-04-03)

- ENH: Add a `is_stacked` parameters for EOReader's `Product` to document either its bands are delivered stacked or file by file.
- FIX: Correct `SWIR_CIRRUS` spectral band's enum value (to `SWIR_CIRRUS` instead of `CIRRUS`), avoiding shadowing cloud band `CIRRUS` ([#131](https://github.com/sertit/eoreader/issues/131))
- FIX: Raise proper exception (`UnhandledArchiveError`) for archived data that needs to be extracted before use. A warning wasn't enough.
- FIX: Remove unused `pixel_spacing` for SAR Products
- FIX: Fix workaround for corrupted `Sentinel-2` mask.

## 0.21.0.post0 (2024-01-08)

- FIX: Don't force install `planetary-computer` or `stac-asset` to use EOReader
- DOC: Remove Twitter from README

## 0.21.0 (2024-01-08)

- **BREAKING CHANGES: Rename `utils.stack_dict` to `utils.stack` since we are stacking datasets and not dict anymore.**
- **BREAKING CHANGES: Band ID for Sentinel-3 OLCI are now int instead of band names (i.e. `7` instead of `Oa07`. The names don't change).**
- **ENH: Allow to use bands IDs, names and common name added to mapped names when trying to load a spectral band. ([#111](https://github.com/sertit/eoreader/issues/111))**
- **ENH: Manage Sentinel-2 as formatted on the cloud (Element84 or Sinergise's way). ([#104](https://github.com/sertit/eoreader/issues/104))**
- **ENH: Handle Python 3.12. ([#113](https://github.com/sertit/eoreader/issues/113))**
- **ENH: Guard against S1 COG format, not yet handled by SNAP.**
- **ENH: Calibration step for `Capella` products now exists in ESA SNAP. Add it in pre-processing.**
- **ENH: Handling of Sentinel-1 [ASF](https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/#readme-file) and [MPC](https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc) RTC products. ([#112](https://github.com/sertit/eoreader/issues/112), [#118](https://github.com/sertit/eoreader/issues/118))**
- **ENH: Handling of Sentinel-1 SM products.**
- **ENH: Better handling of calibration step in SNAP for SAR data.**
- FIX: Fix jpg, png... quicklooks management when plotting
- FIX: Fix an `xarray` issue when trying to compute percentiles when stacking bands
- DEPS: Remove as many mention as possible to `cloudpathlib`
- DEPS: Update minimum versions of some libraries
- DOC: Add example about the output management (in `base` notebook, [#117](https://github.com/sertit/eoreader/issues/117))
- DOC: Update copyright to 2024
- GITHUB: Update bug template
- CI: Enabling pre-commit.ci and dependabot bots
- CI: Update pre-commit hooks
- CI: Revamping `test_satellites`
- CI: Some refactoring and speed-ups

## 0.20.4 (2023-09-26)

- FIX: Don't collocate a raster on itself
- FIX: Better management of default pixel size for multi-resolution products (such as PAN band in Landsat)
- FIX: Fixing the PAN GSD for Landsat-OLI products
- FIX: Update some code to match `sertit>=1.29.0`

## 0.20.3 (2023-07-31)

### Bug Fixes

- FIX: Use `auto` as default dask chunk (instead of `2048`)
- FIX: Minor fix in RasterioError handling when reading bands 
- FIX: Fix Landsat L2 surface reflectance and temperature computation ([#99](https://github.com/sertit/eoreader/issues/99))
- FIX: Fixing TIR temperature conversion for Landsat-7
- FIX: Test thermal bands in CI
- FIX: Upgraded to EO STAC extension v1.1.0 ([#83](https://github.com/sertit/eoreader/issues/83))

## 0.20.2 (2023-06-22)

### Bug Fixes

- FIX: Use already computed bands stored in `tmp` for Planet products 

## 0.20.1 (2023-06-20)

### Bug Fixes

- FIX: Allow band aliases (such as `"CA"` instead of `"COASTAL_AEROSOL"`) in string in band mapping when creating Custom Stacks

### Other

- COMPAT: Add the alias `GREEN_1` for GREEN I band of PlanetScope data, in order to stay in the same pattern as `VRE_x`, `SWIR_x`... `GREEN1` will be deprecated in another release.

## 0.20.0 (2023-05-31)

### Breaking Changes

- **BREAKING CHANGES: Switching from `resolution` to `pixel_size` to avoid confusion about the definitions (especially for SAR data)** ([#82](https://github.com/sertit/eoreader/issues/82))
- **BREAKING CHANGES: `load` function now returns a `xarray.Dataset`** ([#88](https://github.com/sertit/eoreader/issues/88))

### Bug Fixes

- FIX: Collocate bands before trying to create spectral indices: resolve the case where their size mismatches (i.e. in case of window or change of native pixel size)
- FIX: Landsat band masking when specifying a custom resolution and a custom window
- FIX: Round the default pixel_size of custom stacks
- FIX: Convert some fields of STAC items from non JSON serializable dtypes to correct ones
- FIX: Fix erroneous property set to `_get_raw_crs` for Maxar products

### Other

- ENH: Don't load data into memory when computing indices, ensuring tasks are delayed a bit longer ([#58](https://github.com/sertit/eoreader/issues/58))
- DOCS: Add documentation about default CRS ([#87](https://github.com/sertit/eoreader/issues/87))
- DEPS: Dropping support of Python 3.8 ([#81](https://github.com/sertit/eoreader/issues/81))
- DEPS: Pin sertit to 1.27.0
- INTERNAL: Better management of logs for deprecation warnings
- INTERNAL: Refactoring `simplify_footprint` in `sertit` library
- CI: Test that STAC items are serializable when added to a catalog

## 0.19.4 (2023-04-12)

### Bug Fixes

- FIX: Removing calibration step from SNAP pre-processing graph for multi-swath `Cosmo-SkyMed 1st GEN` products (to avoid ending up with empty images after pre-process)
- FIX: Fixing the paths to Sentinel-2 quicklooks: using PVI instead of TCI file if no .jpg preview file is found ([#84](https://github.com/sertit/eoreader/issues/84)
  , [#85](https://github.com/sertit/eoreader/issues/85), thanks a lot @floriandeboissieu)

### Other

- STAC: Updates in STAC management
- INTERNAL: Use `geopandas.estimate_utm_crs()` when possible

## 0.19.3 (2023-03-24)

### Bug Fixes

- OPTIM: Don't recompute stacks if already existing on disk
- FIX: Fixing `Custom Stacks` when specifying `datetime=None` on creation
- FIX: Fix regression for multi-swath DGM CSK data (huge region) ([#78](https://github.com/sertit/eoreader/issues/78))
- FIX: Fix calibration issues with CSK HR data (using fallback GPT graph by default)

### Other

- OPTIM: Always use chunks when reading rasters ([#58](https://github.com/sertit/eoreader/issues/58))
- OPTIM: Speed up VRT virtual warping
- OPTIM: Better management of dask's usage
- CI: Fix projection STAC extension's new version number (1.1.0)

## 0.19.2 (2023-02-23)

### Bug Fixes

- FIX: Fixing stack when saved as integer for some special cases
- FIX: Clipping negative reflectances to 0 ([#79](https://github.com/sertit/eoreader/issues/79))
- FIX: Fixing nodata management for Theia product
- FIX: Fixing handling of SCS multi-swath `Cosmo-SkyMed` products ([#78](https://github.com/sertit/eoreader/issues/78))
- FIX: Writing spectral indices on disk to align with other bands ([#80](https://github.com/sertit/eoreader/issues/80))
- FIX: By default, calibration is not applied to slant range `CSG` data, avoiding producing an empty raster ([#48](https://github.com/sertit/eoreader/issues/48))

### Other

- OPTIM: Using warped VRT instead of reprojecting DEM/VHR stacks to UTM ([#58](https://github.com/sertit/eoreader/issues/58))
- TYP: Fixing typos in typing
- INTERNAL: Moving `EOREADER_NAME` and `DATETIME_FMT` into `__init__.py`
- INTERNAL: Moving stacking function into `utils`
- INTERNAL: Removing unused `cache_property` decorator
- INTERNAL: Factorizing `_load` function
- CI: Using `assert_raster_almost_equal_magnitude` in CI to better check according to bands' content (sertit 1.24.0)
- DEPS: Officially handling Python 3.11 (adding weekly tests on Python 3.11) ([#71](https://github.com/sertit/eoreader/issues/71))
- DOC: Updating `Custom` notebook
- DOC: Updating jupyter cache to match new way of handling outputs in readthedocs

## 0.19.1 (2023-01-12)

### Bug Fixes

- FIX: Fixing a bug for DIMAP V2 products with GML masks opening without CRS: assigning first the raw CRS before converting to the product's CRS
- FIX: Fixing index creation when exotic bands not handled by ASI have been loaded in the same time (i.e. stacking `NDWI` with `Oa21` band)

### Other

- CLEAN: Removing useless GCP functions regarding Sentinel-3 data
- DOC: Adding a `Remove Clouds` notebook
- LIB: Pinning `sertit` to 1.22.0
- CI: Don't run tests when only `__init__` or `__meta__` is updated
- CI: Some factorizing in `gitlab-ci`

## 0.19.0 (2023-01-03)

### Enhancements

- **ENH: Adding the support of Capella constellation** ([#74](https://github.com/sertit/eoreader/issues/74))
- **ENH: Allow the user to load bands with a window (pixels and geo)** ([#25](https://github.com/sertit/eoreader/issues/25))
  , [notebook](https://eoreader.readthedocs.io/en/latest/notebooks/windowed_reading.html))

### Bug Fixes

- FIX: Fix extent computation for `CSG` products with Shapely 2.0
- FIX: Shapely 2.0 deprecation warnings

### Other

- DEPR: Add deprecation warning for EOReader spectral indices (used for legacy in 0.18.0) that are aliases of ASI names ([#72](https://github.com/sertit/eoreader/issues/72)):
    - `AFRI_1_6`: `AFRI1600`,
    - `AFRI_2_1`: `AFRI2100`,
    - `BSI`: `BI`,
    - `NDGRI`: `NGRDI`,
    - `NDRE1`: `NDREI`,
    - `RGI`: `RGRI`,
    - `WV_BI`: `NHFD`,
    - `WI`: `WI2015`,
    - `RDI`: `DSI`,
    - `DSWI`: `DSWI5`,
    - `GRI`: `DSWI4`,
    - `WV_SI`: `NDSIWV`,
    - `PANI`: `BITM`
- DOC: Changing copyright from 2022 to 2023

## 0.18.1 (2022-12-08)

### Bug Fixes

- FIX: Fix regression for missing EOReader aliases for `spyndex` spectral indices
- FIX: Fix bug in footprint computation of DIMAP V1 data

### Other

- DOC: Add latest DOI link
- LIB: Pass to `sertit==1.21.0` to handle windowed data in read natively

## 0.18.0 (2022-12-06)

### Breaking Changes

- **BREAKING CHANGES: Refactoring spectral indices management** ([#47](https://github.com/sertit/eoreader/issues/47))
    - Using [spyndex](https://github.com/awesome-spectral-indices/spyndex) library, allowing to use all spectral indices
      listed [here](https://github.com/awesome-spectral-indices/awesome-spectral-indices/blob/main/output/spectral-indices-table.csv)
    - SAR products may now compute indices if possible (see [this list](https://awesome-ee-spectral-indices.readthedocs.io/en/latest/list.html#radar))
    - Old EOReader indices are still available for legacy purposes, with some changes:
        - For Sentinel-2 data, the band `NIR` and `NARROW_NIR` may be interchanged for some index (
          see [this discussion](https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/27))
        - OSAVI formula has changed to stick with the original paper definition (see [issue](https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/12))
        - `NDRE2/3` formula are fixed, now using `VRE_2/3` and `NDRE1` corresponds to `NDREI` and uses `VRE_1`
        - `CI1` is renamed `CI32` and `CI2` is renamed `CI21` for readability purposes
        - `NDWI21` can be written `NDWI2100` for homogeneity purposes
        - `RDI` (or `DSI`) uses now `SWIR_1` instead of `SWIR_2` (see [this](https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/18) issue)
        - `PANI` equivalent is now `BITM` and is normalised ! (divided by 3)
        - `SBI` is normalized (divided by 2) to fit with `BIXS` definition
        - ⚠ *You may need to install the last `spyndex` directly from GitHub latest version to have all available indices*
- **BREAKING CHANGES: Using `pyresample` to geocode Sentinel-3 data** ([#55](https://github.com/sertit/eoreader/issues/55))
    - Cleaner: better conversion from swath to grid
    - Faster: Up to 4 times faster
    - Allows code refactoring between OLCI and SLSTR
- **BREAKING CHANGES: For SAR product types that are not available in the Data Access Portfolio, default resolution is now the pixel spacing instead of the rg x az resolution**
    - Changes mainly Sentinel-1 default resolutions (except from IW mode)

### Enhancements

- **ENH: Adding the support of Harmonized Landsat-Sentinel constellation** ([#49](https://github.com/sertit/eoreader/issues/49))
- **ENH: Adding the support of GEOSAT-2 constellation** ([#59](https://github.com/sertit/eoreader/issues/59))

### Bug Fixes

- FIX: Fixing `CustomProduct` initialization when fields are set to None (instead of not declaring them)
- FIX: SNAP cannot handle float predictors other than 1! Set it to 1 when saving ortho SAR images to disk, in order for SNAP to be able to despeckle
  them. See [SNAP issue](https://forum.step.esa.int/t/exception-found-when-reading-compressed-tif/654/7). ([#62](https://github.com/sertit/eoreader/issues/62))
- FIX: Fixing mix in `Sentinel-2` mapping for `B8` (`NIR`, 10m resolution, large spectral bandwidth) and `B8A` (`NARROW_NIR`, 20m resolution, narrow spectral bandwidth)

### Other

- DOC: Add FAQ entry concerning SAR constellations extent KML files failing to be read (TLDR: needs `ogr2ogr` in your
  PATH)
- DOC: Add Technical Note published in Remote Sensing MDPI in Readme
- DOC: Update optical band mapping graphs (fix regression to 0.15.0 supported constellation)
- DOC: Add information about DEM management in SAR notebook ([#61](https://github.com/sertit/eoreader/issues/61))
- DOC: Updating indices paragraphs
- CI: Using actions/checkout@v3
- CI: Updating versions of pre-commit hooks
- LIBS: Updating `requirements.txt` and `setup.py` to add `pyresample` and `zarr`

## 0.17.0 (2022-10-12)

### Enhancements

- **ENH: Adding the support of RapidEye constellation**
- **ENH: Handling Planet data with multiple subdatasets** ([#45](https://github.com/sertit/eoreader/issues/45))
- **ENH: Adding the support of Landsat Level-2 products** ([#49](https://github.com/sertit/eoreader/issues/49))
- **ENH: Adding the support of Pleides Neo SEN and PRJ products** *(needs GDAL 3.5+ or rasterio 1.3.0+)*
- **ENH: Adding the function `bands.is_thermal_band`**
- **ENH: Adding the ability for optical custom stacks to load indices**
- **ENH: Adding [BAIM (MODIS Burned Area Index)](https://www.researchgate.net/publication/248428333_Burnt_Area_Index_BAIM_for_burned_area_discrimination_at_regional_scale_using_MODIS_datafire)
  spectral index**
- **ENH: Better management of raw units of the bands of optical products**
- **ENH: Copying files from `tmp_process` when changing product's output**

### Bug Fixes

- FIX: Stacks saved as integers on disk keep their original dtype (float32) in Python
- FIX: Stacks with bands loaded "as is" are correctly saved as integers on disk ([#52](https://github.com/sertit/eoreader/issues/52))
- FIX: Using stack CRS (if projected) for `DIMAP` products instead of recomputing from lat/lon, solving potential discrepancies between stack and product CRS
- FIX: Workaround for JP2 bug when updating an existing raster (maybe related to [this bug](https://github.com/rasterio/rasterio/issues/2528))
- FIX: Better management of SkySat datetime conversion from JSON to XML (deterministic way)
- FIX: Fixing computation of invalid pixels for `Sentinel-2` and `DIMAP` products (do not remove straylight mask)
- FIX: Fixing reprojection resolution of VHR data
- FIX: Computing Brightness Temperature of `Landsat` TIR bands instead of leaving them as is
- FIX: Better management of Landsat Instrument values
- FIX: Better radiometry attribute (adding `brightness temperature` and `reflectance and brightness temperature` values)
- FIX: Changing `Brilliance Temperature` to the correct `Brightness Temperature`
- FIX: Fixing pandas FutureWarning `The frame.append method is deprecated and will be removed from pandas in a future version.`
- FIX: Fixing DeprecationWarning `invalid escape sequence \.`
- FIX: Manage correctly Planet dubious pixels [(especially for 8 bands products)](https://community.planet.com/planet-s-community-forum-3/planetscope-8-bands-and-udm-mask-245?postid=427#post427)

### Optimizations

- OPTIM: Reduce memory usage when updating all the bands attributes
- OPTIM: Reduce memory usage when stacking as integers

### Other

- DOC: Add the need of using SNAP 8.0 up-to-date or SNAP 9.0 ([#42](https://github.com/sertit/eoreader/issues/42))
- DOC: Add the STAC session in API documentation
- DOC: Add warnings for shifts when orthorectifying DIMAP SEN products (using RPCs) ([#53](https://github.com/sertit/eoreader/issues/53))
- DOC: Add limitations to custom stacks
- DEPS: Dropping support of Python 3.7 ([#18](https://github.com/sertit/eoreader/issues/18))
- DEPS: Update minimum version of libs *(geopandas 0.11.0+, rasterio 1.3.0+...)*

## 0.16.1 (2022-08-03)

### Bug Fixes

- FIX: Add the missing conversion to reflectance for `Sentinel-3 OLCI`
- FIX: Better condition for the conversion to reflectance for `Sentinel-2 THEIA`
- FIX: Add logs for `SkySat` data that cannot been converted to reflectance and fix the `radiometry` field of its band xarrays
- FIX: Add the correct nodata (when overridden by the user) to stacks saved as uint16

### Optimizations

- OPTIM: Reduce memory usage during stacking

### Other

- CI: Test reflectance values

## 0.16.0 (2022-08-01)

### Enhancements

- **ENH: Adding the support of SuperView-1 constellation ([#21](https://github.com/sertit/eoreader/issues/21))**
- **ENH: Adding the support of SPOT-4/5 constellations ([#39](https://github.com/sertit/eoreader/issues/39))**
- **ENH: Allow the possibility to pass a constellation (or a constellation list) to `Reader().open()` to speed up the opening of a product**
- **ENH: Add a quicklook search for `Sentinel-3` products**

### Bug Fixes

- FIX: Fix quicklook media type with `JP2` files
- FIX: Fix `Sentinel-3 SLSTR` `F1` bands based on F grid
- FIX: Correct the UTM projection for `Sentinel-3` data
- FIX: Fix handling of zipped `Sentinel-2 L2Ap`
- FIX: Fix zipped `Sentinel-2` with other XML files in GRANULE subdirectories

### Other

- Renaming `master` branch to `main`

## 0.15.1 (2022-06-02)

### Optimizations

- OPTIM: Try to create `Vision-1` footprint from the preview file instead of from the stack.
- OPTIM: Create footprints for stacked products (i.e. `Maxar`, `SkySat`, `Custom`...) without mask by opening only the first band of the stack
- OPTIM: Create footprints for `Maxar` Products with a resolution 10 times lower.
- OPTIM: Footprints have now maximum 50 vertices in order to avoid pixelized footprints

### Bug Fixes

- FIX: Fixing condensed name to avoid duplicates:
    - adding the `job_id` for `VHR` products
    - adding the polarization channels for `SAR` products
- FIX: Remove import of pystac in `stac_utils`
- FIX: Fix bug for `Vision-1` data looking for non-existing RPC files in case of `ORTP` product type
- FIX: Fix quicklook regex for `Vision-1` data
- FIX: Fix regex for raw bands for extracted `Sentinel-3 OLCI` products
- FIX: Fix `PlanetScope` identifying regex to handle products with a satellite_id containing a letter
- FIX: Force metadata regex for `Maxar` products to look for a file with pattern `{name}.XML` to avoid other misplaced XML to be found in place of the true XML.
- FIX: Fix regression for `Landsat-7` footprint
- FIX: Manage the case with `cloud_cover = -999.0` for `Maxar` products (returns `None`)

### Other

- CI: Add new optical products to be tested for end-to-end tests

## 0.15.0 (2022-05-30)

### Breaking Changes

- **BREAKING CHANGES: `Optical` becomes `Spectral` when more appropriate**
- **BREAKING CHANGES: `Platform` and `Sensor` become `Constellation` when more appropriate, to fit STAC vocabulary** ([#29](https://github.com/sertit/eoreader/issues/29)):
    - `Platform` enum becomes `Constellation`
    - `prod.platform` becomes `prod.constellation`
    - `prod.sat_id` becomes `prod.constellation_id`
- **BREAKING CHANGES: File `alias` is removed, replaced by `*_bands` files and proper imports in `bands.__init__`**
- **BREAKING CHANGES: Product attribute `band_names` becomes `bands` in order to be STAC compliant ([#29](https://github.com/sertit/eoreader/issues/29))**
- **BREAKING CHANGES: Better use of `NIR` and `NARROW_NIR` in the `indices` file (according to the gsd of `Sentinel-2` bands composing the indices)**
- **BREAKING CHANGES: Correcting Landsat product types to better manage processing levels and instrument. Landsat-8/9 condensed name may change!**

### Enhancements

- **ENH: Adding the support of `SkySat` (Collect) products** ([#20](https://github.com/sertit/eoreader/issues/20))
- **ENH: Bands in mapping are now objects, instead of just IDs** ([#29](https://github.com/sertit/eoreader/issues/29)). This allows us to:
    - Add band metadata (such as center wavelength, bandwidth...)
    - Map spectral bands between STAC spec and EOReader format ([#29](https://github.com/sertit/eoreader/issues/29))
    - Add a better `__repr__` functions
- **ENH: Handling 8 bands `PlanetScope` data** ([#20](https://github.com/sertit/eoreader/issues/20))
- **ENH: Adding the `GREEN1` mapped band, corresponding to PlanetScope `GREEN I` and `Sentinel-3 OLCI` `Oa05` band**
- **ENH: Handle some slightly broken `Sentinel-2` products:**
    - when the metadata files are corrupted or when the detfoo vectors are empty ([#34](https://github.com/sertit/eoreader/issues/34))
    - with missing MSK prefix for QI_DATA files (i.e. `DETFOO` instead of `MSK_DETFOO`)
- **ENH: Handle exception for corrupted bands (in `Sentinel-2` and `utils.read`) ([#34](https://github.com/sertit/eoreader/issues/34))**
- **ENH: Add a STAC object that can be used to retrieve STAC Items from every Product (`prod.stac.create_item()`) ([#29](https://github.com/sertit/eoreader/issues/29))**
- **ENH: Add a `get_mean_viewing_angles` for Optical Products to fill STAC View Extension ([#29](https://github.com/sertit/eoreader/issues/29))**
- **ENH: Extending `get_raw_band_paths` to every product ([#31](https://github.com/sertit/eoreader/issues/31))**
- **ENH: Adding a `is_ortho` attribute corresponding to when the product is already orthorectified/geocoded, in order to avoid computing heavy processes without wanting it (i.e. footprint...)**
- **ENH: Adding the instrument name of every constellation, under `prod.instrument`**
- **ENH: Handling `COSMO` product with only the `h5` file in it (if missing XML metadata file)** ([#36](https://github.com/sertit/eoreader/issues/36))

### Optimizations

- OPTIM: Retrieve name from filename if possible
- OPTIM: Retrieve extent from metadata when possible (for VHR data)

### Bug Fixes

- FIX: Fixing the band mapping of `WorldView-2/3 Multi` (8 bands)
- FIX: Retrieval (if possible) of Sentinel-1 [unique ID](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar/naming-conventions) (was missing from the product name, as it is not in
  the product preview)
- FIX: Fixing PAZ/TDX MTD regex
- FIX: Optical products: Only set cloud cover and radiometry attributes if spectral bands are asked

### Other

- INTERNAL: File `spot_6` and `spot_7` are removed, replaced by a unique `spot` file. This shouldn't affect the user.
- INTERNAL: Refactoring Landsat-XX products into `LandsatProduct`, this should be invisible for user.
- INTERNAL: Some refactoring in `VHR` files
- WARNINGS: Filter warnings from `__init__`
- CI: Do not process two times the zipped Sentinel-1 in end-to-end tests and manage when the runner kills SNAP
- DOC: Adding a STAC notebook
- DOC: Various updates

## 0.14.0 (2022-04-14)

### Breaking Changes

- **BREAKING CHANGES: `footprint`, `extent`, `wgs84_extent` and `crs` properties are converted back to methods in order to prevent side effects of expensive computation when displaying the object when
  debugging (rollback before version 0.8.0)**
- **BREAKING CHANGES: `get_all_index` becomes `get_all_indices`**
- **BREAKING CHANGES: `acquisition_datetime` becomes `datetime` and `default_resolution`becomes `resolution` for `CustomProduct` in accepted keywords, and the metadata fields have been renamed
  according to the `CustomFields` enum**

### Enhancements

- **ENH: Adding spectral indices:**
    - Shadow Index (`SI`)
    - Global Vegetation Moisture Index (`GVMI`)
    - Soil Brightness Index (`SBI`), Soil Cuirass Index (`SCI`)
    - Panchromatic mocking Index (`PANI`)
    - Green-to-Red ratio Index (`GRI`)
    - Soil Adjusted Vegetation Index (`SAVI`)
    - Optimized Soil Adjusted Vegetation Index (`OSAVI`)
    - Visible Atmospherically Resistant Index (Green) (`VARI`)
    - Enhanced Vegetation Index (`EVI`)
    - Chlorophyll Index RedEdge VRE_3/VRE_2 (`CI1`)
    - Chlorophyll Index RedEdge VRE_2/VRE_1 (`CI2`)
    - Normalized Difference Moisture Index (with SWIR_21) (`NDMI21`)
- **ENH: Making SAR attribute `snap_filename` public**
- **ENH: Handling `ICEYE` pure SLC products**
- **ENH: Allowing the user to choose if they want the GRD or SLC image for `ICEYE` products**
- **ENH: Add the possibility to directly load the cloud cover for optical data (and add it in the band attributes) ([#28](https://github.com/sertit/eoreader/issues/28))**
- **ENH: Add the possibility to retrieve the quicklook path (if existing) and add the `plot` function allowing the user to plot the quicklook (if
  existing) ([#28](https://github.com/sertit/eoreader/issues/28))**
- **ENH: Add the possibility to retrieve the orbit direction (and add it in the band attributes) ([#28](https://github.com/sertit/eoreader/issues/28))**

### Bug Fixes

- FIX: Fixing the inversion between `8` and `8A` bands for `Sentinel-2` and `Sentinel-2 Theia` products
- FIX: Loading every optical band in reflectance (fixed for `Sentinel-2 THEIA`, `Maxar`, `Planet` and `Vision-1` data) ([#30](https://github.com/sertit/eoreader/issues/30))
- FIX: Fixing `ReferenceError: weakly-referenced object no longer exists` when deleting an object
- FIX: Do not set sea values to nodata when orthorectifying SAR data with SNAP
- FIX: Handle `Sentinel-2` data with PB < 02.07 as `L2Ap` products
- FIX: Fixing nodata and offset for `Sentinel-2` data with PB > 04.00
- FIX: Handle new `ICEYE` metadata name's nomenclature
- FIX: Fixing harmless regex error when searching for B1 path for `Landsat` products
- FIX: Fixing platform for `Sentinel-2 Theia`

### Other

- DOC: Creating a real `base` notebook and renaming the old one to `optical`
- DOC: Better type hints (replacing `XDS_TYPE` by `xr.DataArray`)
- CI: Using `sertit.ci.reduce_verbosity` instead of recreating the function

## 0.13.1 (2022-03-08)

### Bug Fixes

- FIX: Handling `Sentinel-2 L2Ap` data
- FIX: Do not use `--no-binary fiona,rasterio` directly in `requirements.txt` (breaks on Windows)
- FIX: Fixing stacking with string bands
- FIX: Better `__repr__` function
- FIX: Read README as UTF-8 in setup.py

### Other

- CI: Adding a tag for choosing the runners
- DOC: Fixing cartopy/GEOS conflicts making the documentation build to fail

## 0.13.0 (2022-03-02)

### Enhancements

- **ENH: Adding the support of `Landsat-9` sensor**
- **ENH: Support Sentinel-2 with missing datatake metadata file(sometimes happens with data downloaded from AWS buckets and converted to .SAFE)**

### Bug Fixes

- FIX: Using default SAR resolution from
  official [Copernicus Data Access Portfolio (2014-2022)](https://spacedata.copernicus.eu/documents/20126/0/DAP+Release+phase2+V2_8.pdf/82297817-2b96-d3de-c397-776292336434?t=1633508426589) (
  Sentinel-2 default
  resolution goes to 10.0 m !)
- FIX: Use `--no-binary fiona,rasterio` directly in `requirements.txt`
- FIX: Removing useless `outputComplex` line in GPT graphs that is breaking SNAP on Linux
- FIX: Removing the workarounds caused by some bugs of `cloudpathlib` and enabling retrieval of nested SAR products (TSX, TDX, PAZ, RCM) from S3 compatible storage.
- FIX: Do not process nodata for a band already existing
- FIX: Fixing an error when reading `TIR` bands with Landsat-7
- FIX: Fixing an error when additive/multiplicative coefficients are set to `NULL` for Landsat data
- FIX: Returning sun angles always as float (some `Sentinel-3` angles were returned as `np.array`)

### Other

- CI: Do not try to process SAR end to end if GPT cannot be found
- CI: Publishing wheel from GitHub instead of Gitlab
- REPO: Setting GitHub as the main repository and using new Gitlab runners

## 0.12.0 (2022-02-09)

### Enhancements

- **ENH: Adding the support of `Pleiades-Neo`, `Vision-1` and `SAOCOM` sensors**
- **ENH: Adding a keyword to allow passing a specific DEM path in `load`/`stack` (for VHR orthorectification and `DEM` bands)**
- **ENH: Adding the name of the DEM in DEM band (i.e. allow to compute the `HILLSHADE` with a DEM and the `SLOPE` with a DTM)**

### Bug Fixes

- FIX: `Sentinel-2` Processing Baseline 04.00: `NARROW_NIR` bands are now loaded correctly
- FIX: `Maxar` products (with `Multi` band ID) are now correctly handled
- FIX: Using `COPDEM-30` (`GLO-30`) by default for SNAP as it appears that the retrieval has been fixed.
- FIX: Fixing the default name for cleaned bands for `Sentinel-3 SLSTR` data (was set on `CLEAN` instead of `NODATA`)
- FIX: Fixing default band for Custom stacks
- FIX: Fixing `get_existing_band_paths` behavior for Custom stacks
- FIX: Remove other never covered lines of code (archived `RCM` products, complex `ICEYE` products, others...)
- FIX: Re-enabling loading str bands (regression)
- FIX: Proper check for empty fields when parsing metadata
- FIX: VHR `_get_dem_path` raises `ValueError` instead of `TypeError`
- FIX: Pre-process SAR bands before despeckling if not existing (was OK in most of the cases, but broke in some cases, especially with CI folder activated and S3 compatible storage)
- FIX: Remove warning `invalid escape sequence \.`, `\w`, `\D` and `\s`
- FIX: Do not set `long_name` for `RAW_CLOUDS` arrays
- FIX: Providing a URL DEM on Windows throws a `OSError` instead of a bare `Exception`

### Optimizations

- OPTIM: Do not pre-process existing Sentinel-3 geocoded bands
- OPTIM: Do not look for valid metadata further than a given nested level in product's directory (for extracted products)

### Other

- CI: Using another (faster) runner
- CI: Add on disk and end-to-end tests
- CI: Do not write tmp files when running on disk tests
- CI: Coverage:
    - Get coverage as HTML
    - Remove useless lines from coverage
    - Combine coverage of S3 and on disk tests
- DOC: Adding a DEM notebook

## 0.11.2 (2022-01-19)

### Bug Fixes

- FIX: Fixing archived SAR processing
- FIX: Needs extraction for `RS2-SLC` data as SNAP does not handle the product
- FIX: Fixing the default name for cleaned bands for optical data (was set on `CLEAN` instead of `NODATA`)

## 0.11.1 (2022-01-17)

### Bug Fixes

- FIX: Fixing complex and orthorectified products for `SAR` data
- FIX: Fixing `RADARSAT-2` `SLC` product type

### Optimizations

- OPTIM: Only preprocessing wanted SAR bands (instead of all existing)
- OPTIM: Do not interpolate nan values by default when writing SAR bands to disk (using a keyword instead)

### Other

- DOC: Updating the SAR notebook and documentation

## 0.11.0 (2022-01-13)

### Breaking Changes

- **BREAKING CHANGES: Renamed `is_band` to `is_sat_band` to better reflect that this function only checks optical and SAR bands**
- **BREAKING CHANGES: Invalid pixels are not processed by default anymore! Only the nodata is set (to go a bit faster)**

### Enhancements

- **ENH: Allowing the user to choose the pixel processing for optical bands: raw band, only nodata or total cleaning of defective pixels** ([#16](https://github.com/sertit/eoreader/issues/16))
- **ENH: Adding a CustomProduct, allowing the user to load any stack as an EOReader Product !**
- **ENH: Check if a band exists before trying to load it**

### Bug Fixes

- FIX: Better handling of `__all__` in `__init__.py` files
- FIX: Ensure that extents and footprints are in UTM
- FIX: Removing docs from wheel
- FIX: Fixing `TIR` bands reading for Landsat data

### Optimizations

- OPTIM: Optimizing `manage_invalid_pixels` for `Sentinel-2` data (processing baseline >= 04.00)

### Other

- DOC: Update README, documentation and notebooks
- DOC: Water Extraction notebook has been refined to show how to manage multiple products
- DOC: Update the installation paragraph in README
- DOC: Adding a `For Contributors` section in the documentation (contributing, release history and GitHub repository)
- DOC: Remove doc testing in GitHub (as the docs are built with readthedocs)
- INTERNAL: Better management of project metadata (version...) in a dedicated file

## 0.10.1 (2022-01-04)

### Bug Fixes

- FIX: Resolve a bug when `methodtools` is not present (for conda package)

## 0.10.0 (2022-01-04)

### Enhancements

- **ENH: Adding `has_bands` to products, ingesting lists as a shortcut for testing the availability of multiple bands**
- **ENH: Simplifying imports**. Now you can replace:
    - `from eoreader.bands.alias import RED, NDVI` by `from eoreader.bands import RED, NDVI`,
    - `from eoreader.products.optical.optical_product import OpticalProduct` by `from eoreader.products import OpticalProduct`,
    - `from eoreader.products.optical.s3_slstr_product import SlstrRadAdjustTuple` by `from eoreader.products import SlstrRadAdjustTuple`, ...

### Optimizations

- OPTIM: Writing cloud bands on disk to speed up multiple calls to `load` or `stack` functions ([#17](https://github.com/sertit/eoreader/issues/17))

### Bug Fixes

- FIX: Correctly naming cloud xarrays
- FIX: Add missing `SLEA` (Spot Extended Area) product type to `ICEYE` data
- FIX: Sentinel-2 clouds (with processing baseline >= 4.0) are now given with a rasterio shape (`count`, `height`, `width`)

### Other

- CI: Remove `pages` stage and run only the tests when a Python file has changed
- DOC: Updating notebooks
- DOC: Updating copyright to 2022

## 0.9.5 (2021-12-14)

### Bug Fixes

- FIX: Do not force import `methodtools` (not existing lib in conda)
- FIX: Using `GRD` resolution given by the constructors as default values for `SLC` products. Do not look it up in metadata as SLC resolution is **NOT** the GRD resolution !

## 0.9.4 (2021-12-13)

### Bug Fixes

- FIX: Caching properties and functions only for object instances
- FIX: Fixing metadata reading for `COSMO-SkyMed 1st Generation` with `Wide Region` and complex product type (handling of multiple swaths)
- FIX: Updates of SNAP GPT graphs for complex SAR data
- FIX: Interpolate nodata inside SAR images (badly handled by SNAP -> fill the gaps that shouldn't exist)

### Other

- INTERNAL: Creation of a class `CosmoProduct` handling generic methods for both `COSMO-SkyMed` generations

## 0.9.3 (2021-12-09)

### Bug Fixes

- FIX: Fixing the search for `.TIL` files for `Maxar` products (with on disk files)
- FIX: Fixing the search for metadata files for `Landsat` products (with on disk files)
- FIX: Fixing the search for metadata files for `TerraSAR-X`, `TanDEM-X` and `PAZ SAR` products (with on disk files)
- FIX: Fixing SNAP files for `TerraSAR-X`, `TanDEM-X` and `PAZ SAR` products
- FIX: Fixing when reading CRS code for `DIMAP` products

## 0.9.2 (2021-12-07)

### Bug Fixes

- FIX: Fixing flag type for `Sentinel-3` data
- FIX: Do not multiply the flags values by the radiance adjustment factor for `Sentinel-3 SLSTR`!
- FIX: Fixing flag exception threshold for `Sentinel-3 SLSTR`
- FIX: Fixing preprocessed band filenames for `Sentinel-3 SLSTR`

## 0.9.1 (2021-12-07)

### Bug Fixes

- FIX: `Reader().valid_mtd` now correctly accepts strings instead of only `Platform` objects
- FIX: Better handling of `Sentinel-2` product type
- FIX: Save bands' new attributes in `str` (to pickle them)
- FIX: Add a `clear()` function to clear products cache

## 0.9.0 (2021-12-06)

### Enhancements

- **ENH: Adding the support of the ICEYE sensor**
- **ENH: Adding the support of the COSMO-SkyMed 2nd Generation sensor**
- **ENH: Adding some attributes to bands and stack: `sensor`, `sensor_id`, `product_type`, `acquisition_date`
  , `condensed_name`** [#7](https://github.com/sertit/eoreader/issues/7)
- **ENH: Replace name by filename and read directly the true name of the product in the metadata** ([#15](https://github.com/sertit/eoreader/issues/15))

### Bug Fixes

- FIX: `Sentinel-1` metadata file with archived products (discarding RFI folder in its search).
- FIX: Add `Quickbird`, `GeoEye` and `WorldView` sensors in `reader` regexes.
- FIX: Add scipy in `requirements.txt` and `setup.py`

### Other

- DOC: Fix references to `pcigeomatics` that doesn't exist anymore (RADARSAT-2 and Constellation)
- REQ: Update `dask` to fix a security issue (only in requirements as `dask` is not mandatory)

## 0.8.1 (2021-10-26)

### Bug Fixes

- FIX: Do not force `chunk` in `utils.read` if dask is not installed

## 0.8.0 (2021-10-25)

### Breaking Changes

- **BREAKING CHANGE: `crs`, `footprint`, `extent`, `wgs84_extent` are now properties !**
- **BREAKING CHANGE: Removing raw `gdaldem` CLI from EOReader (the `HILLSHADE` and `SLOPE` bands are now slightly different !)** ([#10](https://github.com/sertit/eoreader/issues/10))
- **BREAKING CHANGE: `HILLSHADE` is given in `float32` instead of `uint8`**
- **BREAKING CHANGE: `SLOPE` is given in degrees instead of percents**

### Enhancements

- **ENH: Adding the support of the PAZ SAR sensor**
- **ENH: Adding the support of the Sentinel-2 processed with
  the [processing baseline 4.0](https://sentinels.copernicus.eu/web/sentinel/-/copernicus-sentinel-2-major-products-upgrade-upcoming)** ([#11](https://github.com/sertit/eoreader/issues/11))
- **ENH: Removing SNAP from Sentinel-3 pre-process -> Freeing optical data from SNAP dependency !** ([#12](https://github.com/sertit/eoreader/issues/12))
- **ENH: Enabling the use of other S3-SLSTR suffixes than `an` (stripe A at nadir position)**
- **ENH: Thermal bands of Sentinel-3 SLSTR can now be used**
- **ENH: All bands of Sentinel-3 SLSTR/OLCI can now be used (`S7`, `F1`, `F2` for SLSTR, `Oaxx` for OLCI)** ([#14](https://github.com/sertit/eoreader/issues/14))
- **ENH: `YELLOW` band is mapped to `Oa07` band of Sentinel-3 OLCI**
- **ENH: Zipped Sentinel-3 products can now be processed**
- **ENH: Allow the use of `kwargs` in `load`, mainly for `rasters.read` (and allowing i.e. radiance adjustment in S3-SLSTR)**

### Optimizations

- OPTIM: `crs`, `footprint`, `extent`, `default_transform`, `wgs84_extent` are cached (
  using `@cached_property`) ([#13](https://github.com/sertit/eoreader/issues/13))
- OPTIM: `get_mean_sun_angles` and `default_transform` are now cached (
  using `@cache`) ([#13](https://github.com/sertit/eoreader/issues/13))
- OPTIM: `get_datetime`: Look for the date only if `datetime` attribute is None ([#13](https://github.com/sertit/eoreader/issues/13))
- OPTIM: Better management of `fspath` for cloud-stored products (download the files only once)
- OPTIM: Stop downloading/extracting files if not necessary

### Bug Fixes

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

### Other

- DEPR: `FAR_NIR` band is removed
- REQ: Using `h5netcdf` instead of `netCDF4`
- DOC: Add a Context paragraph in the README
- DOC: Add a Conda x SNAP question in the FAQ
- DOC: Creation of a Sentinel-3 notebook
- DOC: Updates of notebooks
- DOC: Numerous updates

## 0.7.1 (2021-09-29)

### Bug Fixes

- FIX: Fixing a bug when opening archived Sentinel-1 (wrong metadata file found)
- DOC: Updating CSS and readme

## 0.7.0 (2021-09-23)

### Enhancements

- **ENH: Implementing RADARSAT-Constellation products (as `RCM`)**
- **ENH: Implementing Maxar products (such as `GE01, WV02, WV03, WV04`, but others should be supported too)**
- **ENH: Implementing TanDEM-X products (as `TDX`)**
- **ENH: Adding `RH`, `RV`, `RH_DSPK` and `RV_DSPK` SAR bands**
- **ENH: Adding the `YELLOW` optical band (for `WorldView-2`, `WorldView-3` and `Sentinel-3 OLCI`)**
- **ENH: Adding [WorldView index](https://resources.maxar.com/optical-imagery/multispectral-reference-guide) (without the ones using SWIR)**
- **ENH: Loading by size -> round resolution to the closest meter (or decimeter for resolution < 1.0m)**
- **ENH: Super class for VHR data**

### Bug Fixes

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

### Other

- DOC: Fix documentation of the NDWI index
- DOC: Update graph for optical band mapping
- CI: Adding a test loading invalid band name
- CI: Setting CI log level to DEBUG
- CI: Accelerating the CI processes

## 0.6.4 (2021-09-15)

### Bug Fixes

- FIX: Sentinel-3 band mapping (`Coastal Aerosol` <-> `03`, `BLUE` <-> `04`)

### Other

- DOC: Adding an interactive graph for optical band mapping

## 0.6.3 (2021-09-10)

### Bug Fixes

- FIX: Load works with string bands (`prod.load('BLUE')`)
- FIX: Fixing missing `_remove_tmp_process` for products needing extraction
- FIX: Remove multi converting for Sentinel-3

## 0.6.2 (2021-09-10)

### Bug Fixes

- FIX: Better handling of archives for products that needs extraction
- FIX: TerraSAR-X products need to be extracted to be processed by SNAP !

## 0.6.1 (2021-09-10)

### Bug Fixes

- FIX: Fixing critical bug for Sentinel-3 (mapping between clean bands and SNAP bands)

## 0.6.0 (2021-09-02)

### Enhancements

- **ENH: Ensuring EOReader supports Dask**

### Bug Fixes

- FIX: Fixing and adding BAIS2 index in alias
- FIX: Fixing GLI index
- FIX: Fixing a bug when writing reprojected DIMAP band
- FIX: Fixing a bug with SCS Cosmo-SkyMed data

### Other

- DOC: Adding a DASK notebook
- DOC: Updating notebooks

## 0.5.0 (2021-08-24)

### Breaking Changes

- **BREAKING CHANGE: Read metadata/namespaces only once and store it as a private member. Keep accessing it through the `read_mtd` function (#9)**
  **WARNING**: Breaking change for Landsat: `read_mtd()` loses the argument `force_pd=True` as it always returns an Etree

### Enhancements

- **ENH: Adding the [BAIS2](https://www.researchgate.net/publication/323964124_BAIS2_Burned_Area_Index_for_Sentinel-2) index**
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

### Bug Fixes

- FIX: Decoupling classic metadata reading from the name as EOReader accepts now modified product names (#9)
- FIX: Better handling of cloud-stored DEM (raising an exception for non-ortho DIMAP data as GDAL and rasterio does not handle that case)
- FIX: `environment.yml` to respect the stricter use of `file:` syntax.
  See [here](https://stackoverflow.com/questions/68571543/using-a-pip-requirements-file-in-a-conda-yml-file-throws-attributeerror-fileno)
  for more information.
- FIX: Fixing bug when opening an archive product with `name` mode and nested dictionary (when looking for a filename instead of the directory name)

### Other

- CI: Fixing `test_dems_https` and resetting DEM afterward
- CI: Fixing DEM and ds2 database management
- DOC: Adding a FAQ page and enhancing the Main Features page (#3)
- DOC: Read Metadata has its own paragraph in Main Features

## 0.4.8 (2021-07-23)

### Enhancements

- **ENH: Allowing `stack` to take single band in input instead of a list**

### Bug Fixes

- FIX: Fixing a regression loading optical bands which have been previously cleaned (Landsat, Theia, possibly PlanetScope)
- FIX: `load` and `stack` always returns `float32` arrays

### Other

- CI: Testing if loading 2 times a band gives the same result

## 0.4.7.post0 (2021-07-23)

### Bug Fixes

- FIX: Fixing a regression loading Landsat bands which have been previously cleaned

## 0.4.7 (2021-07-23)

### Enhancements

- **ENH: Adding a `default_transform` function returning data from default band (without warping it)**
  -> *mapping `calculate_default_transform` from `rasterio`*
- **ENH: Adding a `clean_tmp` function allowing the user to clean the product's temporary output by hand**
- **ENH: Simplifying DEM warping code**

### Bug Fixes

- FIX: `DIMAP` products return always projected (in UTM) default bands (`get_default_band_path`
  uses `_get_default_utm_band`)
- FIX: Theia Footprint returns a `GeoDataFrame` instead of a `GeoSeries`
- FIX: Better management of the `size` keyword with `load` and `stack` functions
- FIX: Landsat retrieval of multipart cleaned bands (like `SWIR_1`)
- FIX: Some typehints fixes
- FIX: Sentinel-3 open sun angles with NetCDF files stored in the cloud
- FIX: Silently pass the writing of clean bands if we cannot (like if permission error)

### Other

- CI: Do not reinstall everything if not needed (only PyYAML)
- CI: renaming `build` stage into `lint`
- CI: simplifying geometry comparison
- CI: Testing the `size` keyword for every sensor

## 0.4.6 (2021-07-19)

### Bug Fixes

- FIX: Fixing no data for Sentinel-3 cloud bands
- FIX: In alias: `DeprecationWarning: using non-Enums in containment checks will raise TypeError in Python 3.8`

### Other

- CI: Set default S3 client to point to unistra's bucket
- CI: Tox SNAP relay S3_DB_URL_ROOT

## 0.4.5 (2021-07-13)

### Bug Fixes

- FIX: Adding condensed name in the search when loading S3-SLSTR clouds
- FIX: Fixing no data for Sentinel-3 bands processed by SNAP
- FIX: Fix bug when stack path's directory doesn't exist

## 0.4.4 (2021-07-13)

### Bug Fixes

- FIX: Do not verbose empty lists when loading optical bands
- FIX: Sentinel-3: Bands processed by SNAP are written with the condensed name as suffix

## 0.4.3.post1 (2021-07-08)

### Bug Fixes

- FIX: Fixing another bug for DEM_PATH using S3 Paths

### Other

- DOC: Add a DOI

## 0.4.3.post0 (2021-07-08)

### Bug Fixes

- FIX: Fixing DEM_PATH using S3 Paths

## 0.4.3 (2021-07-05)

### Enhancements

- **ENH: Optimizing loading cloud bands for DIMAP Products**
- `stack` accepts `**kwargs` in order to pass options to `rioxarray.to_raster()`

### Bug Fixes

- FIX: Fixing not found masks with S3+zip Sentinel-2 products
- FIX: Fixing some type hints

### Other

- CI: Fixing network directories with pathlib

## 0.4.2 (2021-07-01)

### Enhancements

- **ENH: Enabling the use of products stored in the cloud
  (S3, S3 compatible storage, Google, Azure...) through [`cloudpathlib`](https://cloudpathlib.drivendata.org/)**
- **ENH: Using correct band names in long_name**

### Other

- CI: Use pre-computed cleaned band if existing
- DOC: Adding examples for using S3 data, especially for S3 compatible storage

## 0.4.1.post0 (2021-06-21)

### Bug Fixes

- FIX: cloud mask values were inverted in Sentinel-2 cloud masks
- FIX: Landsat collection 2 cloud masks are now OK

## 0.4.1 (2021-06-21)

### Bug Fixes

- FIX: Improving stacks saved as uint16:
    - Only satellite bands and index are scaled (*10.000)
    - DEM bands are just rounded
    - Cloud bands (booleans) are saved as is
- FIX: Fixing a rasterization bug affecting S2 and DIMAP masks, happening when the vectors have another size than the image
- FIX: Adding a warning on bad georeferencing when using GS and GT Landsat products

### Other

- CI: Minor updates in documentation and code

## 0.4.0 (2021-06-10)

### Enhancements

- **ENH: Adding THR data support:**
    - **PlanetScope**
    - **Pleiades**
    - **SPOT-6/7**
- **ENH: Better handling of SNAP DEMs (using External DEM and other available SNAP DEMs)**

### Bug Fixes

- FIX: More robust way of looking for `data` directory
- FIX: Bug fix in `stack` that causes some bands to be inexplicably empty sometimes
- FIX: Bug fix in `alias.isindex`
- FIX: Forcing extent to UTM

### Optimizations

- OPTIM: Write clean bands on disk to avoid redoing invalid pixel computation and allow the user to remove them on deletion
- OPTIM: `prod.has_bands` / `prod.get_existing_bands` do not orthorectify/despeckle SAR bands anymore

### Other

- CI: Adding a bimonthly test for SNAP processes
- DOC: Adding two new notebooks (SAR and VHR data)
- DOC: Completing the documentation

## 0.3.4 (2021-05-28)

- **BREAKING CHANGES: `read_mtd()` returns a dict for the namespace map in order to manage multi namespace XMLs**
- **ENH: Introduced support for DEM files from web urls (starting with http(s)://)**
- FIX: Landsat Zenith angle computation (mixing elevation and zenith angle)
- CI: Adding weekly tests (`tox` on Python 3.7, 3.8, 3.9 on Linux and Windows)
- DOC: Updating documentation, setting DEM path as an environment variable

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
    - Inverted default resolution between L4/5 MSS and TM sensors
- Removing useless logs when missing DEM but no computed DEM bands
- Adding copyright headers to every python files
- Fixing and adding examples

## 0.3.0 (2021-04-28)

- Going Open Source
