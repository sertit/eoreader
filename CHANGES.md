# Release History

## X.Y.Z (YYYY-MM-DD)

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
