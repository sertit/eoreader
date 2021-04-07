# Optical data
Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/Optical) to learn
more about that.

## Enabled optical satellites

|Satellites | Allowed Product Types | Use archive|
|--- | --- | ---|
|Sentinel-2 | L1C & L2A | Yes|
|Sentinel-2 Theia | L2A | Yes|
|Sentinel-3 SLSTR | RBT | No|
|Sentinel-3 OLCI | EFR | No|
|Landsat-8 OLCI | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-7 ETM | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-5 TM | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-4 TM | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-5 MSS | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-4 MSS | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-3 MSS | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-2 MSS | Level 1 | Collection 1: No, Collection 2: Yes|
|Landsat-1 MSS | Level 1 | Collection 1: No, Collection 2: Yes|

## Band mapping

|Bands (names) | Coastal aerosol | Blue | Green | Red | Vegetation red edge | Vegetation red edge | Vegetation red edge | NIR | Narrow NIR | Water vapor | SWIR – Cirrus | SWIR | SWIR | Panchromatic | Thermal IR | Thermal IR|
|--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---|
|**Bands enum** | `CA` | `BLUE` | `GREEN` | `RED` | `VRE_1` | `VRE_2` | `VRE_3` | `NIR` | `NNIR` | `WP` | `SWIR_CIRRUS` | `SWIR_1` | `SWIR_2` | `PAN` | `TIR_1` | `TIR_2`|
|Sentinel-2 | 1 (60m) | 2 (10m) | 3 (10m) | 4 (10m) | 5 (20m) | 6 (20m) | 7 (20m) | 8 (10m) | 8A (20m) | 9 (60m) | 10 (60m) | 11 (20m) | 12 (20m) |  |  | |
|Sentinel-2 Theia | *Not available* | 2 (10m) | 3 (10m) | 4 (10m) | 5 (20m) | 6 (20m) | 7 (20m) | 8 (10m) | 8A (20m) | *Not available* | 10 (60m) | 11 (20m) | 12 (20m) |  |  | |
|Sentinel-3 OLCI* | 2 (300m) | 3 (300m) | 6 (300m) | 8 (300m) | 11 (300m) | 12 (300m) | 16 (300m) | 17 (300m) | 17 (300m) | 20 (300m) |  |  |  |  |  | |
|Sentinel-3 SLSTR* |  | 1 (500m) | 2 (500m) |  |  |  | 3 (500m) | 3 (500m) |  | 4 (500m) | 5 (500m) | 6 (500m) |  | 8 (1km | 9 (1km|
|Landsat-8 | 1 (30m) | 2 (30m) | 3 (30m) | 4 (30m) |  |  |  | 5 (30m) | 5 (30m) |  | 9 (30m) | 6 (30m) | 7 (30m) | 8 (15m | 10 (100m) | 11 (100m)|
|Landsat-7 |  | 1 (30m) | 2 (30m) | 3 (30m) |  |  |  | 4 (30m) | 4 (30m) |  |  | 5 (30m) | 7 (30m) | 8 (15m | 6 (60m) | 6 (60m)|
|Landsat-5 TM |  | 1 (30m) | 2 (30m) | 3 (30m) |  |  |  | 4 (30m) | 4 (30m) |  |  | 5 (30m) | 7 (30m) |  | 6 (120m) | 6 (120m)|
|Landsat-4 TM |  | 1 (30m) | 2 (30m) | 3 (30m) |  |  |  | 4 (30m) | 4 (30m) |  |  | 5 (30m) | 7 (30m) |  | 6 (120m) | 6 (120m)|
|Landsat-5 MSS |  |  | 1 (60m) | 2 (60m) | 3 (60m) | 3 (60m) | 3 (60m) | 4 (60m) | 4 (60m) |  |  |  |  |  |  | |
|Landsat-4 MSS |  |  | 1 (60m) | 2 (60m) | 3 (60m) | 3 (60m) | 3 (60m) | 4 (60m) | 4 (60m) |  |  |  |  |  |  | |
|Landsat-3 |  |  | 4 (60m) | 5 (60m) | 6 (60m) | 6 (60m) | 6 (60m) | 7 (60m) | 7 (60m) |  |  |  |  |  | 8 (240m) | 8 (240m)|
|Landsat-2 |  |  | 4 (60m) | 5 (60m) | 6 (60m) | 6 (60m) | 6 (60m) | 7 (60m) | 7 (60m) |  |  |  |  |  |  | |
|Landsat-1 |  |  | 4 (60m) | 5 (60m) | 6 (60m) | 6 (60m) | 6 (60m) | 7 (60m) | 7 (60m) |  |  |  |  |  |  | |

\* Not all bands of this satellite are used in EOReader

## Cloud bands
|Satellites | Clouds Bands|
|--- | ---|
|Sentinel-2 | `RAW_CLOUDS`, `CLOUDS`, `CIRRUS`, `ALL_CLOUDS`|
|Sentinel-2 Theia | `RAW_CLOUDS`, `CLOUDS`, `SHADOWS`, `CIRRUS`, `ALL_CLOUDS`|
|Sentinel-3 OLCI | *No cloud file available for S3-OLCI data* |
|Sentinel-3 SLSTR | `RAW_CLOUDS`, `CLOUDS`, `CIRRUS`, `ALL_CLOUDS`|
|Landsat-8 | `RAW_CLOUDS`, `CLOUDS`, `SHADOWS`, `CIRRUS`, `ALL_CLOUDS`|
|Landsat-7 | `RAW_CLOUDS`, `CLOUDS`, `SHADOWS`, `ALL_CLOUDS`|
|Landsat-5 TM | `RAW_CLOUDS`, `CLOUDS`, `SHADOWS`, `ALL_CLOUDS`|
|Landsat-4 TM | `RAW_CLOUDS`, `CLOUDS`, `SHADOWS`, `ALL_CLOUDS`|
|Landsat-5 MSS | `RAW_CLOUDS`, `CLOUDS`, `ALL_CLOUDS`|
|Landsat-4 MSS | `RAW_CLOUDS`, `CLOUDS`, `ALL_CLOUDS`|
|Landsat-3 | `RAW_CLOUDS`, `CLOUDS`, `ALL_CLOUDS`|
|Landsat-2 | `RAW_CLOUDS`, `CLOUDS`, `ALL_CLOUDS`|
|Landsat-1 | `RAW_CLOUDS`, `CLOUDS`, `ALL_CLOUDS`|

## DEM bands
Optical satellites can all load `DEM`, `SLOPE` and `HILLSHADE` bands.

## Available index

|Index | Needed bands | Accepted satellites|
|--- | --- | ---|
|`AFRI_1_6` | `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`AFRI_2_1` | `NIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`AWEInsh` | `BLUE`, `GREEN`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`AWEIsh` | `GREEN`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`BAI` | `RED`, `NIR` | All optical satellites|
|`BSI` | `BLUE`, `RED`, `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`CIG` | `GREEN`, `NIR` | All optical satellites|
|`DSWI` | `GREEN`, `RED`, `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`GLI` | `GREEN`, `RED`, `BLUE` | Sentinel-2, Sentinel-3 OLCI, Landsat OLCI, (E)TM|
|`GNDVI` | `GREEN`, `NIR` | All optical satellites|
|`MNDWI` | `GREEN`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`NBR` | `NNIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`NDGRI` | `GREEN`, `RED` | All optical satellites|
|`NDMI` | `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`NDRE2` | `NIR`, `VRE_1` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`NDRE3` | `NIR`, `VRE_2` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`NDVI` | `RED`, `NIR` | All optical satellites|
|`NDWI` | `GREEN`, `NIR` | All optical satellites|
|`RDI` | `NNIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`RGI` | `GREEN`, `RED` | All optical satellites|
|`RI` | `GREEN`, `VRE_1` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`SRSWIR` | `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`TCBRI` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`TCGRE` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`TCWET` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`WI` | `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|

## Default SNAP resolution

You can override default SNAP resolution (in meters) when orthorecifying SAR and S3 bands by setting the following
environment variables:

- `EOREADER_S3_DEFAULT_RES` (500m for SLSTR and 300m for OLCI data by default)