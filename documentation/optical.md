# Optical data

## Implemented optical satellites

|Satellites | Class | Product Types | Use archive | Default Resolution |
|--- | --- | --- | --- | ---|
|Sentinel-2 | `eoreader.products.optical.s2_product.S2Product` | L1C & L2A | Yes | 20m|
|Sentinel-2 Theia | `eoreader.products.optical.s2_theia_product.S2TheiaProduct` | L2A | Yes | 20m|
|Sentinel-3 SLSTR | `eoreader.products.optical.s3_product.S3Product` | RBT | No | 300m|
|Sentinel-3 OLCI | `eoreader.products.optical.s3_product.S3Product` | EFR | No | 500m|
|Landsat-8 OLCI | `eoreader.products.optical.l8_product.L8Product` | Level 1 | Collection 1: No, Collection 2: Yes | 30m|
|Landsat-7 ETM | `eoreader.products.optical.l7_product.L7Product` | Level 1 | Collection 1: No, Collection 2: Yes | 30m|
|Landsat-5 TM | `eoreader.products.optical.l5_product.L5Product` | Level 1 | Collection 1: No, Collection 2: Yes | 30m|
|Landsat-4 TM | `eoreader.products.optical.l4_product.L4Product` | Level 1 | Collection 1: No, Collection 2: Yes | 30m|
|Landsat-5 MSS | `eoreader.products.optical.l5_product.L5Product` | Level 1 | Collection 1: No, Collection 2: Yes | 60m|
|Landsat-4 MSS | `eoreader.products.optical.l4_product.L4Product` | Level 1 | Collection 1: No, Collection 2: Yes | 60m|
|Landsat-3 MSS | `eoreader.products.optical.l3_product.L3Product` | Level 1 | Collection 1: No, Collection 2: Yes | 60m|
|Landsat-2 MSS | `eoreader.products.optical.l2_product.L2Product` | Level 1 | Collection 1: No, Collection 2: Yes | 60m|
|Landsat-1 MSS | `eoreader.products.optical.l1_product.L1Product` | Level 1 | Collection 1: No, Collection 2: Yes | 60m|

Satellites products that cannot be used as archived have to be extracted before use.

## Optical bands

The following bands are available in `EOReader`, but may not be available for all sensors.

### Satellite bands
These bands are mainly based on Sentinel-2 bands with some additions:

- `CA`: Coastal Aerosol
- `BLUE`
- `GREEN`
- `RED`
- `VRE_1`: Vegetation Red Edge 1
- `VRE_2`: Vegetation Red Edge 2
- `VRE_3`: Vegetation Red Edge 3
- `NIR`: Near Infrared
- `NARROW_NIR`: Narrow Near Infrared (band `8A` for `Sentinel-2`)
- `WP`: Water vapour
- `SWIR_CIRRUS`
- `SWIR_1`
- `SWIR_2`
- `PAN`: Panchromatic
- `TIR_1`: Thermal Infrared 1
- `TIR_2`: Thermal Infrared 2

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#optical-band-mapping-between-sensors) for more information.

### Index

- `AFRI_1_6`
- `AFRI_2_1`
- `AWEInsh`
- `AWEIsh`
- `BAI`
- `BSI`
- `CIG`
- `DSWI`
- `GLI`
- `GNDVI`
- `MNDWI`
- `NBR`
- `NDGRI`
- `NDMI`
- `NDRE2`
- `NDRE3`
- `NDVI`
- `NDWI`
- `RDI`
- `RGI`
- `RI`
- `SRSWIR`
- `TCBRI`
- `TCGRE`
- `TCWET`
- `WI`

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#available-index) for more information.

### Cloud bands

Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and
orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked.

- `RAW_CLOUDS`: Raw Cloud file as provided (the only changes are the orthorectification and rasterization). Can provide
  other flags, or cloud probability.
- `CLOUDS`: Cloud presence (1) or absence (0).
- `CIRRUS`: Cirrus presence (1) or absence (0).
- `SHADOWS`: Shadows presence (1) or absence (0).
- `ALL_CLOUDS`: Cloud **OR** Cirrus **OR** Shadows presence (1) or absence (0). Do not take into account missing bands (
  ie. for Landsat MSS sensors, `ALL_CLOUDS` == `CLOUDS`)

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#cloud-bands-specifications) for more information.

### DEM bands

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_SAR_DEFAULT_RES`

- `DEM`
- `SLOPE`
- `HILLSHADE`

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#dem-bands-specifications) for more information.
