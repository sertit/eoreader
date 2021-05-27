# Release History

## X.Y.Z (YYYY-MM-DD)

## 0.3.3 (2021-05-21)

- Introduced support for DEM files from web urls (starting with http(s)://)
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
