# SAR data

## Implemented SAR satellites

|Satellites | Class | Product Types | Use archive|
|--- | --- | --- | ---|
|Sentinel-1 | `eoreader.products.sar.s1_product.S1Product` | SLC & GRD | Yes|
|COSMO-Skymed | `eoreader.products.sar.csk_product.CskProduct` | DGM & SCS, (others should also be OK) | No|
|TerraSAR-X | `eoreader.products.sar.tsx_product.TsxProduct` | MGD (SSC should be OK) | No|
|RADARSAT-2 | `eoreader.products.sar.rs2_product.Rs2Product` | SGF (SLC should be OK) | Yes|

.. WARNING::
    Satellites products that cannot be used as archived have to be extracted before use.

## SAR Bands
According to what contains the products, allowed SAR bands are:

- `VV` (`eoreader.bands.bands.SarBandNames.VV`)
- `VH` (`eoreader.bands.bands.SarBandNames.VH`)
- `HH` (`eoreader.bands.bands.SarBandNames.HH`)
- `HV` (`eoreader.bands.bands.SarBandNames.HV`)

You also can load despeckled bands:

- `VV_DSPK` (`eoreader.bands.bands.SarBandNames.VV_DSPK`)
- `VH_DSPK` (`eoreader.bands.bands.SarBandNames.VH_DSPK`)
- `HH_DSPK` (`eoreader.bands.bands.SarBandNames.HH_DSPK`)
- `HV_DSPK` (`eoreader.bands.bands.SarBandNames.HV_DSPK`)


## DEM bands

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_SAR_DEFAULT_RES`

- `DEM`
- `SLOPE`

See [here](https://sertit.github.io/eoreader/eoreader/products/sar/index.html#dem-bands) for more information.
