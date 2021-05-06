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

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#optical-band-mapping-between-sensors)
for more information.

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

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#cloud-bands-specifications) for more
information.

### DEM bands

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_SAR_DEFAULT_RES`

- `DEM`
- `SLOPE`
- `HILLSHADE`

See [here](https://sertit.github.io/eoreader/eoreader/products/optical/index.html#dem-bands-specifications) for more
information.

## Specifications

### Optical band mapping between sensors

|Bands (names) | Coastal aerosol | Blue | Green | Red | Vegetation red edge | Vegetation red edge | Vegetation red edge | NIR | Narrow NIR | Water vapor | SWIR – Cirrus | SWIR | SWIR | Panchromatic | Thermal IR | Thermal IR|
|--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---|
|**Band alias** | `CA` | `BLUE` | `GREEN` | `RED` | `VRE_1` | `VRE_2` | `VRE_3` | `NIR` | `NARROW_NIR` | `WP` | `SWIR_CIRRUS` | `SWIR_1` | `SWIR_2` | `PAN` | `TIR_1` | `TIR_2`|
|Sentinel-2 | **1** (60m) | **2** (10m) | **3** (10m) | **4** (10m) | **5** (20m) |**6** (20m) |**7** (20m) |**8** (10m) | **8A** (20m) |**9** (60m) |**10** (60m) |**11** (20m) |**12** (20m) |  |  | |
|Sentinel-2 Theia | *Not available* | **2** (10m) |**3** (10m) | **4** (10m) | **5** (20m) |**6** (20m) |**7** (20m) |**8** (10m) | **8A** (20m) | *Not available* |**10** (60m) |**11** (20m) |**12** (20m) |  |  | |
|Sentinel-3 OLCI* | **2** (300m) | **3** (300m) |**6** (300m) |**8** (300m) |**11** (300m) |**12** (300m) | **16** (300m) | **17** (300m) | **17** (300m) | **20** (300m) |  |  |  |  |  | |
|Sentinel-3 SLSTR* | | | **1** (500m) | **2** (500m) |  |  |  |**3** (500m) |**3** (500m) |  | **4** (500m) | **5** (500m) |**6** (500m) | |**8** (1km) |**9** (1km)|
|Landsat OLCI (8) | **1** (30m) | **2** (30m) | **3** (30m) | **4** (30m) |  |  |  | **5** (30m) | **5** (30m) |  |**9** (30m) |**6** (30m) |**7** (30m) |**8** (15m) |**10** (100m) |**11** (100m)|
|Landsat ETM (7)|  | **1** (30m) | **2** (30m) | **3** (30m) |  |  |  | **4** (30m) | **4** (30m) |  |  | **5** (30m) |**7** (30m) |**8** (15m) |**6** (60m) |**6** (60m)|
|Landsat TM (5-4)|  | **1** (30m) | **2** (30m) | **3** (30m) |  |  |  | **4**(30m) | **4** (30m) |  |  | **5** (30m) |**7** (30m) |  |**6** (120m) |**6** (120m)|
|Landsat MSS (5-4)|  |  | **1** (60m) | **2** (60m) | **3** (60m) | **3** (60m) | **3** (60m) | **4** (60m) | **4** (60m) |  |  |  |  |  |  | |
|Landsat MSS (1-3)|  |  | **4** (60m) | **5** (60m) | **6** (60m) | **6** (60m) | **6** (60m) | **7** (60m) | **7** (60m) |  |  |  |  |  |**8** (240m)<br>*only for Landsat-3* |**8** (240m)<br>*only for Landsat-3*|

\* Not all bands of this satellite are used in EOReader

### Cloud bands specifications

Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and
orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked.

The only difference with the other bands is that the cloud bands are provided in `uint8` and have a nodata equal to 255.

- `eoreader.bands.bands.CloudsBandNames.RAW_CLOUDS`: Raw Cloud file as provided (the only changes are the
  orthorectification and rasterization). Can provide other flags, or cloud probability.
- `eoreader.bands.bands.CloudsBandNames.CLOUDS`: Cloud presence (1) or absence (0). If clouds are provided in
  probabilities, their presence is determined according to Landsat definition (proba> 67%)
- `eoreader.bands.bands.CloudsBandNames.CIRRUS`: Cirrus presence (1) or absence (0). If clouds are provided in
  probabilities, their presence is determined according to Landsat definition (proba> 67%)
- `eoreader.bands.bands.CloudsBandNames.SHADOWS`: Shadows presence (1) or absence (0). If clouds are provided in
  probabilities, their presence is determined according to Landsat definition (proba> 67%)
- `eoreader.bands.bands.CloudsBandNames.ALL_CLOUDS`: Cloud **OR** Cirrus **OR** Shadows presence (1) or absence (0). Do
  not take into account missing bands (ie. for Landsat MSS sensors, `ALL_CLOUDS` == `CLOUDS`)

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

### DEM bands specifications

Optical satellites can all load `eoreader.bands.bands.DemBandNames.DEM`, `eoreader.bands.bands.DemBandNames.SLOPE`
and `eoreader.bands.bands.DemBandNames.HILLSHADE` bands. The `SLOPE` and `HILLSHADE` bands are computed with
the [`gdaldem`](https://gdal.org/programs/gdaldem.html) tool.

Use the environment variable `EOREADER_SAR_DEFAULT_RES` to position your worldwide DEM.

### Available index

|Index | Needed bands | Accepted satellites|
|--- | --- | ---|
|`eoreader.bands.index.AFRI_1_6` | `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.AFRI_2_1` | `NIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.AWEInsh` | `BLUE`, `GREEN`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.AWEIsh` | `GREEN`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.BAI` | `RED`, `NIR` | All optical satellites|
|`eoreader.bands.index.BSI` | `BLUE`, `RED`, `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.CIG` | `GREEN`, `NIR` | All optical satellites|
|`eoreader.bands.index.DSWI` | `GREEN`, `RED`, `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.GLI` | `GREEN`, `RED`, `BLUE` | Sentinel-2, Sentinel-3 OLCI, Landsat OLCI, (E)TM|
|`eoreader.bands.index.GNDVI` | `GREEN`, `NIR` | All optical satellites|
|`eoreader.bands.index.MNDWI` | `GREEN`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.NBR` | `NNIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.NDGRI` | `GREEN`, `RED` | All optical satellites|
|`eoreader.bands.index.NDMI` | `NIR`, `SWIR_1` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.NDRE2` | `NIR`, `VRE_1` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`eoreader.bands.index.NDRE3` | `NIR`, `VRE_2` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`eoreader.bands.index.NDVI` | `RED`, `NIR` | All optical satellites|
|`eoreader.bands.index.NDWI` | `GREEN`, `NIR` | All optical satellites|
|`eoreader.bands.index.RDI` | `NNIR`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.RGI` | `GREEN`, `RED` | All optical satellites|
|`eoreader.bands.index.RI` | `GREEN`, `VRE_1` | Sentinel-2, Sentinel-3 OLCI, Landsat MSS|
|`eoreader.bands.index.SRSWIR` | `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.TCBRI` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.TCGRE` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.TCWET` | `BLUE`, `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|
|`eoreader.bands.index.WI` | `GREEN`, `RED`, `NIR`, `SWIR_1`, `SWIR_2` | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|

## Default SNAP resolution

You can override default SNAP resolution (in meters) when orthorecifying SAR and S3 bands by setting the following
environment variables:

- `EOREADER_S3_DEFAULT_RES` (500m for SLSTR and 300m for OLCI data by default)

# Documentary Sources

## Landsat

- [Collection 1 vs Collection 2](https://www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary)
- [Quality assessment Collection 1](https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band)
- [Quality assessment Collection 2](https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands)
- [MSS Collection 2 Data Format](https://www.usgs.gov/media/files/landsat-1-5-mss-collection-2-level-1-data-format-control-book)
- [TM Collection 2 Data Format](https://www.usgs.gov/media/files/landsat-4-5-tm-collection-2-level-1-data-format-control-book)
- [ETM Collection 2 Data Format](https://www.usgs.gov/media/files/landsat-7-etm-collection-2-level-1-data-format-control-book)
- [OLCI Collection 2 Data Format](https://www.usgs.gov/media/files/landsat-8-level-1-data-format-control-book)

## Sentinel-2

- [Cloud masks](https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks)
- [Product Specification](https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf)

## Sentinel-2 Theia

- [Product Format](https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/)

## Sentinel-3

- [OLCI Product Format](https://sentinel.esa.int/documents/247904/1872756/Sentinel-3-OLCI-Product-Data-Format-Specification-OLCI-Level-1)
- [SLSTR Clouds](https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/cloud-identification)

## PlanetScope

- [Product Specification](https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf)
- [On Medium](https://medium.com/geoplexing/getting-started-with-planet-imagery-part-3-items-and-ordering-476a1a21618c)

## Band mapping

- You can find a magnificent band comparison chart on the [Imagico](http://blog.imagico.de/satellite-comparison-update/)
  blog.
- [L8-S2](https://reader.elsevier.com/reader/sd/pii/S0034425718301883)
- [L8-S2](https://landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png)
- [L4/L5, MSS-TM](https://landsat.gsfc.nasa.gov/the-multispectral-scanner-system/)
- [All Landsats](https://landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png)
- [S2](https://discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png)
- [S3 OLCI](https://discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png)
- [S3 SLSTR](https://discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png)

## Index

- [Index consistency](https://www.indexdatabase.de/)
- Specific sources inside the index function documentation in `eoreader.bands.index`
