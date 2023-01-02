# SAR data

You will find a SAR tutorial [here](https://eoreader.readthedocs.io/en/latest/notebooks/SAR.html).

## Implemented SAR constellations

| Constellations                      | Class                                      | Use archive                                 |
|-------------------------------------|--------------------------------------------|---------------------------------------------|
| `Capella`                           | {meth}`~eoreader.products.CapellaProduct`  | ❌                                           |
| `COSMO-Skymed 1st Generation`       | {meth}`~eoreader.products.CskProduct`      | ❌                                           |
| `COSMO-Skymed 2nd Generation`       | {meth}`~eoreader.products.CsgProduct`      | ❌                                           |
| `ICEYE`                             | {meth}`~eoreader.products.IceyeProduct`    | ❌                                           |
| `RADARSAT Constellation Mission`    | {meth}`~eoreader.products.RcmProduct`      | ❌                                           |
| `RADARSAT-2`                        | {meth}`~eoreader.products.Rs2Product`      | ✅ for ground range data, ❌ for complex data |
| `Sentinel-1`                        | {meth}`~eoreader.products.S1Product`       | ✅                                           |
| `SAOCOM-1`                          | {meth}`~eoreader.products.SaocomProduct`   | ❌                                           |
| `TerraSAR-X`, `TanDEM-X`, `PAZ SAR` | {meth}`~eoreader.products.TsxProduct`      | ❌                                           |

```{warning}
Satellites products that cannot be used as archived have to be extracted before use, 
mostly because SNAP doesn't handle them.
```

## Product type handling

| Constellations                      | Product Type                         | Handled |
|-------------------------------------|--------------------------------------|---------|
| `Capella`                           | SLC                                  | ✅       |
| `Capella`                           | GEC                                  | ✅       |
| `Capella`                           | GEO                                  | ✅       |
| `Capella`                           | SICD, SIDD, CPHD                     | ❌       |
| `COSMO-Skymed`                      | SCS                                  | ✅       |
| `COSMO-SkyMed` 1st Generation       | DGM                                  | ✅       |
| `COSMO-SkyMed` 2nd Generation       | DGM                                  | ⚠️      |
| `COSMO-SkyMed`                      | GEC, GTC                             | ⚠️      | 
| `ICEYE`                             | SLC                                  | ✅       |
| `ICEYE`                             | GRD                                  | ✅       | 
| `ICEYE`                             | ORTHO                                | 💤      |
| `RADARSAT Constellation Mission`    | SLC                                  | ⚠️      | 
| `RADARSAT Constellation Mission`    | GRC, GCC, GCD                        | ⚠️      |
| `RADARSAT Constellation Mission`    | GRD                                  | ✅       | 
| `RADARSAT-2`                        | SLC                                  | ✅       | 
| `RADARSAT-2`                        | SGX, SCN, SCW,<br>SCF, SCS, SSG, SPG | ⚠️      |
| `RADARSAT-2`                        | SGF                                  | ✅       |
| `Sentinel-1`                        | SLC                                  | ✅       | 
| `Sentinel-1`                        | GRD                                  | ✅       |
| `SAOCOM-1`                          | SLC                                  | ✅       | 
| `SAOCOM-1`                          | ID                                   | ⚠       |
| `SAOCOM-1`                          | GEC                                  | ✅       |
| `SAOCOM-1`                          | GTC                                  | ✅       |
| `TerraSAR-X`, `TanDEM-X`, `PAZ SAR` | SSC                                  | ✅       | 
| `TerraSAR-X`, `TanDEM-X`, `PAZ SAR` | MGD                                  | ✅       |
| `TerraSAR-X`, `TanDEM-X`, `PAZ SAR` | GEC                                  | ⚠️      |
| `TerraSAR-X`, `TanDEM-X`, `PAZ SAR` | EEC                                  | ✅       |

✅: Tested   
⚠️: Never tested, **use it at your own risk!**  
❌: Not handled   
💤: Waiting for the release  

The goal of **EOReader** is to implement every constellation that can be used in
the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/).
The constellations that can be used during CEMS activations are (as of 09/2021):  
![cems_constellations](https://www.esa.int/var/esa/storage/images/esa_multimedia/images/2021/09/copernicus_contributing_missions_overview/23461131-1-eng-GB/Copernicus_Contributing_Missions_overview_pillars.jpg)

## SAR Bands

```{warning}
- **EOReader** always loads SAR bands in a GRD format. This library is not (yet ?) meant to manage inSAR or other complex processes.
- Only the `Intensity` bands are used (not the `I`, `Q` for complex data or `Amplitude` for ground range data)
- Some SAR band may contain null pixels that are not really nodata (COSMO for example).  
    In this case, the Terrain Correction step applied by SNAP can create large nodata area.  
    If this is the case, you can set the keyword {meth}`~eoreader.keywords.SAR_INTERP_NA` to True when loading or stacking SAR data
```

According to what contains the products, allowed SAR bands are:

- {meth}`~eoreader.bands.SarBandNames.VV`
- {meth}`~eoreader.bands.SarBandNames.VH`
- {meth}`~eoreader.bands.SarBandNames.HH`
- {meth}`~eoreader.bands.SarBandNames.HV`
- {meth}`~eoreader.bands.SarBandNames.RH` (only for RADARSAT-Constellation)
- {meth}`~eoreader.bands.SarBandNames.RV` (only for RADARSAT-Constellation)

You also can load despeckled bands:

- {meth}`~eoreader.bands.SarBandNames.VV_DSPK`
- {meth}`~eoreader.bands.SarBandNames.VH_DSPK`
- {meth}`~eoreader.bands.SarBandNames.HH_DSPK`
- {meth}`~eoreader.bands.SarBandNames.HV_DSPK`
- {meth}`~eoreader.bands.SarBandNames.RH_DSPK` (only for RADARSAT-Constellation)
- {meth}`~eoreader.bands.SarBandNames.RV_DSPK` (only for RADARSAT-Constellation)

### Available indices

EOReader uses (from version 0.18.0) the indices described in
the [awesome spectral indices (ASI)](https://awesome-ee-spectral-indices.readthedocs.io/en/latest/) project.

ASI implements SAR indices, with the list available [here](https://awesome-ee-spectral-indices.readthedocs.io/en/latest/list.html#radar).

## DEM bands

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_SAR_DEFAULT_RES`

- `DEM`
- `SLOPE`

SAR constellations can only load {meth}`~eoreader.bands.DemBandNames.DEM` and {meth}`~eoreader.bands.DemBandNames.SLOPE`
bands as the sun position does not impact SAR data. The `SLOPE` band is given in degrees. Please post an issue if you
need this band in `percent`.

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_DEM_PATH`.
You can use both a local path e.g. `/mnt/dataserver/dems/srtm_30_v4/index.vrt` or `\\dataserver\DEMS\srtm_30_v4\index.vrt` or
a URL pointing to a web resources hosted on a S3 compatible storage e.g. 
`https://s3.storage.com/dem-bucket/srtm_cog.tif` (not available on Windows for now).

## Default resolution

The default resolution of SAR products is the one given in 
[Data Access Portfolio (2014-2022, section 6.2)](https://spacedata.copernicus.eu/documents/20126/0/DAP+Document+-+current+(10).pdf). 
For resolutions not available in this document, we are using the pixel spacing given by the constellation's provider.
Complex data are **always** converted back to ground range to be used, so the complex resolution is **never** used by EOReader.

SAR default resolution is the **pixel spacing** given by the constellation provider, to follow common habits.
Sometimes, especially when converting complex data to ground range, this resolution needs to be adaptated.

> ⚠ Pay attention that for a pixel spacing of 10 meters and a rg x az resolution of 23m, objects under 23m won't be resolved !
> As this may be counter-intuitive, it is recommanded to **always** specify the resolution when loading SAR data.

### Sentinel-1

| **Sentinel-1**                  | Ground Range Detected (GRD)<br>Full Resolution (FR)   | Ground Range Detected (GRD)<br>High Resolution (HR)   | Ground Range Detected (GRD)<br>Medium Resolution (MR)      |
|---------------------------------|-------------------------------------------------------|-------------------------------------------------------|------------------------------------------------------------|
| StripMap (SM) \*                | **pixel spacing: 3.5m**<br>rg x az resolution: 9.0m   | **pixel spacing: 10.0m**<br>rg x az resolution: 23.0m | **pixel spacing: 40.0m**<br>rg x az resolution: 84.0m      |
| Interferometric Wide swath (IW) |                                                       | 20.0m                                                 | **pixel spacing: 40.0m**<br>rg x az resolution: 88.0x87.0m |
| Extra-Wide swath (EW)           |                                                       | **pixel spacing: 25.0m**<br>rg x az resolution: 25.0m | **pixel spacing: 40.0m**<br>rg x az resolution: 93.0x87.0m |
| Wave (WV) \*                    |                                                       |                                                       | **pixel spacing: 25.0m**<br>rg x az resolution: 52.0x51.0m |

\* Resolutions not provided in the Data Access Portfolio. Available [here](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/resolutions/level-1-ground-range-detected).

### COSMO-Skymed 1st Generation

| **COSMO-Skymed<br>1st Generation**   | Detected Ground Multi-look (DGM)<br>Geocoded Ellipsoid Corrected (GEC)<br>Geocoded Terrain Corrected (GTC) |
|--------------------------------------|------------------------------------------------------------------------------------------------------------|
| **Spotlight**<br>Mode-2 (S2)         | 1.0m                                                                                                       | 
| **StripMap**<br>Himage from SCS (HI) | 3.0m                                                                                                       |
| **StripMap**<br>Himage GRD (HI)      | 5.0m                                                                                                       |
| **StripMap**<br>PingPong (PP)        | 20.0m                                                                                                      |
| **ScanSAR**<br>Wide Region (WR)      | 30.0m                                                                                                      |
| **ScanSAR**<br>Huge Region (HR)      | 100.0m                                                                                                     |

### COSMO-Skymed 2nd Generation

Resolutions not provided in the Data Access Portfolio. 
Available [here](https://www.e-geos.it/assets/images/test-img/cosmo-document/gd-com-20-001-e-geos-official-pricelist-june-22nd-2020.pdf).

| **COSMO-Skymed<br>2nd Generation** | Detected Ground Multi-look (DGM)<br>Geocoded Ellipsoid Corrected (GEC)<br>Geocoded Terrain Corrected (GTC) |
|------------------------------------|------------------------------------------------------------------------------------------------------------|
| SPOTLIGHT_2_A                      | ~0.4m                                                                                                      |
| SPOTLIGHT_2_B                      | ~0.63m                                                                                                     |
| SPOTLIGHT-2_C                      | ~0.8m                                                                                                      |
| STRIPMAP & QUADPOL                 | ~3.0m                                                                                                      |
| SCANSAR1                           | ~20.0m                                                                                                     |
| SCANSAR2                           | ~40.0m                                                                                                     |
| PINGPONG                           | ~12.0m                                                                                                     |

### TerraSAR-X & TanDEM-X & PAZ SAR

| **TerraSAR-X<br>TanDEM-X<br>PAZ SAR**            | Multi Look Ground Range (MGD)<br>Geocoded Ellipsoid Corrected (GEC)<br>Enhanced Ellipsoid Corrected (EEC)<br>Spatially enhanced<br>(high resolution, SE) | Multi Look Ground Range (MGD)<br>Geocoded Ellipsoid Corrected (GEC)<br>Enhanced Ellipsoid Corrected (EEC)<br>Radiometrically enhanced<br>(high radiometry, RE) |
|--------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **StripMap (SM)**<br>Single-Pol                  | 3.3m                                                                                                                                                     | 7.0m   \*                                                                                                                                                      |
| **StripMap (SM)**<br>Dual-Pol                    | 6.6m                                                                                                                                                     | 9.9m   \*                                                                                                                                                      |
| **High Resolution Spotlight (HS)**<br>Single-Pol | 1.1m                                                                                                                                                     | 3.0m   \*                                                                                                                                                      |
| **High Resolution Spotlight (HS)**<br>Dual-Pol   | 2.2m                                                                                                                                                     | 4.4m   \*                                                                                                                                                      |
| **Spotlight (SL)**<br>Single-Pol                 | 1.7m                                                                                                                                                     | 3.8m   \*                                                                                                                                                      |
| **Spotlight (SL)**<br>Dual-Pol                   | 3.4m                                                                                                                                                     | 5.5m   \*                                                                                                                                                      |
| **Staring Spotlight (ST)**<br>Single-Pol         | 0.24m                                                                                                                                                    | 0.9m   \*                                                                                                                                                      |
| **ScanSAR (SC)**<br>Four Beams                   |                                                                                                                                                          | 18.5m                                                                                                                                                          |
| **ScanSAR (SC)**<br>Six Beams                    |                                                                                                                                                          | 40.0m                                                                                                                                                          |

\* Resolutions not provided in the Data Access Portfolio. Available [here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf).

### RADARSAT-2

| **RADARSAT-2**              | Maximal spatial resolution |
|-----------------------------|----------------------------|
| Spotlight                   | 1.0m                       |
| Ultra-Fine                  | 3.0m                       |
| Wide Ultra-Fine             | 3.0m                       |
| Multi-Look Fine             | 5.0m                       |
| Wide Multi-Look Fine        | 5.0m                       |
| Extra-Fine                  | 5.0m                       |
| Fine                        | 8.0m                       |
| Wide-Fine                   | 8.0m                       |
| Standard                    | 25.0m                      |
| Wide                        | 25.0m                      |
| Extended High               | 25.0m                      |
| Extended Low                | 25.0m                      |
| Fine Quad-Pol               | 12.0m                      |
| Wide Quad-Pol               | 12.0m                      |
| Standard Quad-Pol           | 25.0m                      |
| Wide Standard Quad-Pol      | 25.0m                      |
| ScanSAR Narrow              | 60.0m                      |
| ScanSAR Wide                | 100.0m                     |
| Ship (Detection of vessels) | 35.0m                      |
| Ocean Surveillance          | 50.0m                      |


### RADARSAT-Constellation

Resolutions not provided in the Data Access Portfolio. 
Available [here](https://www.asc-csa.gc.ca/eng/satellites/radarsat/technical-features/radarsat-comparison.asp).

| **RADARSAT-Constellation**          | Resolution |
|-------------------------------------|------------|
| Spotlight [FSL]                     | 1.0m       |
| Very-High Resolution, 3 meters [3M] | 3.0m       |
| High Resolution, 5 meters [5M]      | 5.0m       |
| Quad-Polarization [QP]              | 9.0m       |
| Medium Resolution, 16 meters [16M]  | 16.0m      |
| Medium Resolution, 30 meters [SC30] | 30.0m      |
| Medium Resolution, 50 meters [SC50] | 50.0m      |
| Low Noise [SCLN]                    | 100.0m     |
| Low Resolution, 100 meters [SC100]  | 100.0m     |
| Ship Detection                      | Variable   |

### ICEYE

Resolutions not provided in the Data Access Portfolio. 
Available [here](https://iceye-ltd.github.io/product-documentation/latest/productguide/collectioncharacteristics/).

| **ICEYE**         | Resolution |
|-------------------|------------|
| Spotlight [SL(H)] | 1.0m       |
| StripMap [SM(H)]  | 3.0m       |
| Scan [SC]         | < 15.0m    |

### SAOCOM-1

Resolutions not provided in the Data Access Portfolio. 
Available [here](https://saocom.veng.com.ar/en/).

| **SAOCOM-1**                                  | Detected Image (DI)<br>Geocoded Ellipsoid Corrected (GEC)<br>Geocoded Terrain Corrected (GTC) |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------|
| **StripMap (SM)**<br>Single and Dual Pol      | 10.0m                                                                                         |
| **StripMap (SM)**<br>Quad Pol                 | 10.0m                                                                                         |
| **TOPSAR Narrow (TN)**<br>Single and Dual Pol | 30.0m                                                                                         |
| **TOPSAR Narrow (TN)**<br>Quad Pol            | 50.0m                                                                                         |
| **TOPSAR Wide (TW)**<br>Single and Dual Pol   | 50.0m                                                                                         |
| **TOPSAR Wide (TW)**<br>Quad Pol              | 100.0m                                                                                        |

### Capella

Resolutions not provided in the Data Access Portfolio. 
Available [here](https://support.capellaspace.com/hc/en-us/articles/360059224291-What-SAR-imagery-products-are-available-with-Capella-).

| **ICEYE**              | Resolution |
|------------------------|------------|
| Spotlight [SP]         | 0.35m      |
| StripMap [SM]          | 0.8m       |
| Sliding Spotlight [SS] | 0.6m       |                                                                                    |

## GPT graphs

You can change the SAR GPT graphs used by setting the following environment variables:

- `EOREADER_PP_GRAPH`: Environment variables for pre-processing graph path.
- `EOREADER_DSPK_GRAPH`: Environment variables for despeckling graph path

```{warning}
For performance reasons, the `Terrain Correction` step is done **before** the `Despeckle` step. Indeed this step is very
time-consuming and better done one time on the raw image than two times on both the raw and the despeckled image. Even
if this is not the regular way of handling SAR data, this shouldn't really affect the quality of any extraction done
after that.
```

You can change the DEM used for the Terrain Correction step by positioning the `EOREADER_SNAP_DEM_NAME` environment variable. 
Available DEMs are:
- `ACE2_5Min` 
- `ACE30`
- `ASTER 1sec GDEM`
- `Copernicus 30m Global DEM`
- `Copernicus 90m Global DEM`
- `GETASSE30` (by default)
- `SRTM 1Sec HGT`
- `SRTM 3Sec`
- `External DEM`

If `External DEM` is set, you must specify the DEM you want by positioning the `EOREADER_DEM_PATH` to a DEM that can be read by SNAP.


### What to know if you are changing a graph

Those graphs should have a reader and a writer on this model:

```xml

<graph id="Graph">
 <version>1.0</version>
 <node id="Read">
  <operator>Read</operator>
  <sources/>
  <parameters class="com.bc.ceres.binding.dom.XppDomElement">
  <file>$file</file>
  </parameters>
 </node>
 <node id="Write">
  <operator>Write</operator>
  <sources>
  <sourceProduct refid="????"/>
  </sources>
  <parameters class="com.bc.ceres.binding.dom.XppDomElement">
  <file>$out</file>
  <formatName>BEAM-DIMAP</formatName>
  </parameters>
 </node>
</graph>
```

```{warning}
Pay attention to set `$file` and `$out` and leave the `BEAM-DIMAP` file format. The first graph must orthorectify your
SAR data, but should not despeckle it. The second graph is precisely charged to do it.

SNAP graphs are run on every band separatly.

 The pre-processing graph should also have a `Calibration` and a `Terrain Correction` step with the following wildcards that are set automatically in the module:

 - `$calib_pola`: Polarization of the band to calibrate
 - `$dem_name`: SNAP DEM name
 - `$dem_path`: DEM path (that can be use by SNAP, so only TIFF DEMs)
 - `$res_m`: Resolution in meters
 - `$res_deg`: Resolution in degrees
 - `$crs`: CRS
 - The nodata value should **always** be set to 0.
```

The default `Calibration` step is:

```xml
<node id="Calibration">
    <operator>Calibration</operator>
    <sources>
        <sourceProduct refid="ThermalNoiseRemoval"/>
    </sources>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
        <sourceBands/>
        <auxFile>Latest Auxiliary File</auxFile>
        <externalAuxFile/>
        <outputImageInComplex>false</outputImageInComplex>
        <outputImageScaleInDb>false</outputImageScaleInDb>
        <createGammaBand>false</createGammaBand>
        <createBetaBand>false</createBetaBand>
        <selectedPolarisations>${calib_pola}</selectedPolarisations>
        <outputSigmaBand>true</outputSigmaBand>
        <outputGammaBand>false</outputGammaBand>
        <outputBetaBand>false</outputBetaBand>
    </parameters>
</node>
```

The default `Terrain Correction` step is:

```xml
<node id="Terrain-Correction">
    <operator>Terrain-Correction</operator>
    <sources>
        <sourceProduct refid="LinearToFromdB"/>
    </sources>
    <parameters class="com.bc.ceres.binding.dom.XppDomElement">
        <sourceBands/>
        <demName>${dem_name}</demName>
        <externalDEMFile>${dem_path}</externalDEMFile>
        <externalDEMNoDataValue>0.0</externalDEMNoDataValue>
        <externalDEMApplyEGM>true</externalDEMApplyEGM>
        <demResamplingMethod>BILINEAR_INTERPOLATION</demResamplingMethod>
        <imgResamplingMethod>BILINEAR_INTERPOLATION</imgResamplingMethod>
        <pixelSpacingInMeter>${res_m}</pixelSpacingInMeter>
        <pixelSpacingInDegree>${res_deg}</pixelSpacingInDegree>
        <mapProjection>${crs}</mapProjection>
        <alignToStandardGrid>false</alignToStandardGrid>
        <standardGridOriginX>0.0</standardGridOriginX>
        <standardGridOriginY>0.0</standardGridOriginY>
        <nodataValueAtSea>false</nodataValueAtSea>
        <saveDEM>false</saveDEM>
        <saveLatLon>false</saveLatLon>
        <saveIncidenceAngleFromEllipsoid>false</saveIncidenceAngleFromEllipsoid>
        <saveLocalIncidenceAngle>false</saveLocalIncidenceAngle>
        <saveProjectedLocalIncidenceAngle>false</saveProjectedLocalIncidenceAngle>
        <saveSelectedSourceBand>true</saveSelectedSourceBand>
        <applyRadiometricNormalization>false</applyRadiometricNormalization>
        <saveSigmaNought>false</saveSigmaNought>
        <saveGammaNought>false</saveGammaNought>
        <saveBetaNought>false</saveBetaNought>
        <incidenceAngleForSigma0>Use projected local incidence angle from DEM</incidenceAngleForSigma0>
        <incidenceAngleForGamma0>Use projected local incidence angle from DEM</incidenceAngleForGamma0>
        <auxFile>Latest Auxiliary File</auxFile>
        <externalAuxFile/>
    </parameters>
</node>
```

### Default SNAP resolution

You can override default SNAP resolution (in meters) when geocoding SAR bands by setting the following environment
variable:

- `EOREADER_SAR_DEFAULT_RES`: 0.0 by default, which means using the product's default resolution

## Documentary Sources

- [Data Access Portfolio (2014-2022)](https://spacedata.copernicus.eu/documents/20126/0/DAP+Document+-+current+%2810%29.pdf)

### Copernicus 
- [Copernicus Contributing Missions](https://www.esa.int/ESA_Multimedia/Images/2021/09/Copernicus_Contributing_Missions_overview)

### Sentinel-1

- [Data Products](https://sentinel.esa.int/web/sentinel/missions/sentinel-1/data-products)
- [Acquisition Mode](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes)

### RADARSAT

- [RADARSAT-2 Product Description](https://catalyst.earth/catalyst-system-files/help/references/gdb_r/RADARSAT-2.html)
- [RADARSAT-Constellation Product Description](https://catalyst.earth/catalyst-system-files/help/references/gdb_r/RADARSAT_Constellation.html)
- [Comparison between RS2 and RCM](https://www.asc-csa.gc.ca/eng/satellites/radarsat/technical-features/radarsat-comparison.asp)

### COSMO-Skymed

- [COSMO-Skymed 1st Generation Product Description](https://earth.esa.int/eogateway/missions/cosmo-skymed)
- [COSMO-Skymed 1st Generation Product Description 2](https://catalyst.earth/catalyst-system-files/help/references/gdb_r/SPW_reuse/COSMO-SkyMed.html)
- [COSMO-Skymed 1st Generation Product Handbook](https://earth.esa.int/eogateway/documents/20142/37627/Cosmo-SkyMed-Product-Handbook.pdf)
- [COSMO-Skymed 2nd Generation System and Products Description](https://earth.esa.int/eogateway/documents/20142/37627/COSMO-SkyMed-Second-Generation-Mission-Products-Description.pdf)

### TerraSAR-X, TanDEM-X and PAZ SAR

- [TerraSAR-X & TanDEM-X Product Description](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)
- [TerraSAR-X & TanDEM-X Product Description 2](https://catalyst.earth/catalyst-system-files/help/references/gdb_r/TerraSAR-X.html)
- [PAZ SAR Image Product Guide](https://www.hisdesat.es/wp-content/uploads/2019/10/PAZ-HDS-GUI-001-PAZ-Image-Product-Guide-issue-1.1-.pdf)
- [PAZ SAR Product Description](https://catalyst.earth/catalyst-system-files/help/references/gdb_r/PAZ.html)

### ICEYE

- [ICEYE Product Specifications](https://www.iceye.com/hubfs/Downloadables/ICEYE-Level-1-Product-Specs-2019.pdf)
- [ICEYE Product Documentation](https://iceye-ltd.github.io/product-documentation/5.1/)

### SAOCOM-1
- [SAOCOM Description](https://saocom.veng.com.ar/en/)
- [SAOCOM Product Format](https://saocom.veng.com.ar/L1-product-format-EN.pdf)
- [SAOCOM Data Products](https://earth.esa.int/eogateway/catalog/saocom-data-products)

### Capella
- [Capella SAR Imagery Products](https://support.capellaspace.com/hc/en-us/categories/360002612692-SAR-Imagery-Products)
- [Capella Product Guide](https://support.capellaspace.com/hc/en-us/articles/4626115099796-SAR-Imagery-Products-Guide)
- [Capella Products Format Specification](https://support.capellaspace.com/hc/en-us/articles/5607458273940-SAR-Imagery-Products-Format-Specification)*

*Documentation last accessed on the 02/12/2022*