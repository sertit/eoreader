# SAR data

## Implemented SAR satellites

|Satellites | Class | Product Types | Use archive|
|--- | --- | --- | ---|
|Sentinel-1 | {meth}`~eoreader.products.sar.s1_product.S1Product` | SLC & GRD | Yes|
|COSMO-Skymed | {meth}`~eoreader.products.sar.csk_product.CskProduct` | DGM & SCS, (others should also be OK) | No|
|TerraSAR-X | {meth}`~eoreader.products.sar.tsx_product.TsxProduct` | MGD (SSC should be OK) | No|
|RADARSAT-2 | {meth}`~eoreader.products.sar.rs2_product.Rs2Product` | SGF (SLC should be OK) | Yes|

```{warning}
Satellites products that cannot be used as archived have to be extracted before use.
```

## SAR Bands
According to what contains the products, allowed SAR bands are:

- {meth}`~eoreader.bands.bands.SarBandNames.VV`
- {meth}`~eoreader.bands.bands.SarBandNames.VH`
- {meth}`~eoreader.bands.bands.SarBandNames.HH`
- {meth}`~eoreader.bands.bands.SarBandNames.HV`

You also can load despeckled bands:

- {meth}`~eoreader.bands.bands.SarBandNames.VV_DSPK`
- {meth}`~eoreader.bands.bands.SarBandNames.VH_DSPK`
- {meth}`~eoreader.bands.bands.SarBandNames.HH_DSPK`
- {meth}`~eoreader.bands.bands.SarBandNames.HV_DSPK`


## DEM bands

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_SAR_DEFAULT_RES`

- `DEM`
- `SLOPE`

SAR satellites can only load {meth}`~eoreader.bands.bands.DemBandNames.DEM` and {meth}`~eoreader.bands.bands.DemBandNames.SLOPE`
bands as the sun position does not impact SAR data. The `SLOPE` band is computed with
the [`gdaldem`](https://gdal.org/programs/gdaldem.html) tool.

These bands need a valid worldwide DEM path positioned thanks to the environment variable `EOREADER_DEM_PATH`.
You can use both a local path e.g. `/mnt/dataserver/dems/srtm_30_v4/index.vrt` or `\\dataserver\DEMS\srtm_30_v4\index.vrt` or
a URL pointing to a web resources hosted on a S3 compatible storage e.g. 
`https://s3.storage.com/dem-bucket/srtm_cog.tif` (not available on Windows for now).

## Default resolution

The default resolution of SAR products depends on their type. Complex data are **always** converted back to ground range
to be used.

The product resolution is read in the metadata file if possible, so the following values are given as hints:

### Sentinel-1

| **Sentinel-1** | Single Look Complex (SLC) |Ground Range Detected (GRD)<br>Full Resolution (FR) | Ground Range Detected (GRD)<br>High Resolution (HR) | Ground Range Detected (GRD)<br>Medium Resolution (MR)|
|--- | --- | --- | --- | ---|
|StripMap (SM) | 1.5x3.6   m to 3.1x4.1 m | 3.5m | 10.0m | 40.0m|
|Interferometric   Wide swath (IW) | 2.3x14.1   m |  | 10.0m | 40.0m|
|Extra-Wide swath (EW) | 5.9x19.9 m |  | 25.0m | 40.0m|
|Wave (WV) | 1.7x4.1 m and 2.7x4.1 m |  |  | 25.0m|

### COSMO-Skymed

| **COSMO-Skymed** | Single-look Complex Slant (SCS) | Detected Ground Multi-look (DGM)<br>Geocoded Ellipsoid Corrected (GEC)<br>Geocoded Terrain Corrected (GTC)|
|--- | --- | ---|
|**Spotlight**<br>Mode-2 (S2) | 1.1-0.9x0.91m | 1.0m|
|**StripMap**<br>Himage (HI) | 3.0-2.6x2.4-2.6m | 5.0m|
|**StripMap**<br>PingPong (PP) | 11-10x9.7m | 20.0m|
|**ScanSAR**<br>Wide Region (WR) | 13.5x23m | 30.0m|
|**ScanSAR**<br>Huge Region (HR) | 13.5x38.0m | 100.0m|

### TerraSAR-X

|**TerraSAR-X** | Single-look Slant Range (SSC) | Multi Look Ground Range (MGD)<br>Geocoded Ellipsoid Corrected (GEC)<br>Enhanced Ellipsoid Corrected (EEC)<br>Spatially enhanced <br>(high resolution, SE)| Multi Look Ground Range (MGD)<br>Geocoded Ellipsoid Corrected (GEC)<br>Enhanced Ellipsoid Corrected (EEC)<br>Radiometrically enhanced<br>(high radiometry, RE)|
|--- | --- | --- | ---|
|**StripMap (SM)**<br>Single-Pol | 0.9x2.0m | 1.5m   or 1.25m | 4.0m   or 3.25m|
|**StripMap (SM)**<br>Dual-Pol | 0.9x2.5m | 3.0m | 5.5m   or 4.5m|
|**High Resolution Spotlight (HS)**<br>Single-Pol | 0.9x0.8m | 1.5m or 0.5m | 2.0m or 1.5m|
|**High Resolution Spotlight (HS)**<br>Dual-Pol | 0.9x1.5m | 1.5m or 1.0m | 3.0m or 2.0m|
|**Spotlight (SL)**<br>Single-Pol | 0.9x1.3m | 1.5m or 0.75m | 3.0m or 1.75m|
|**Spotlight (SL)**<br>Dual-Pol | 0.9x2.6m | 3.5m or 3.4m | 8.5m or 5.5m|
|**Staring Spotlight (ST)**<br>Single-Pol | 0.5x0.2m | 0.4m or 0.2m | 0.8m or 0.4m|
|**ScanSAR (SC)**<br>Four Beams | 0.9x13m |  | 8.25m|
|**ScanSAR (SC)**<br>Six Beams | 1.4x?m |  | 15.0m|

### RADARSAT-2

|**RADARSAT-2** | Single-look   complex (SLC) | SAR   georeferenced extra(SGX) | SAR   georeferenced fine (SGF) | SAR   systematic geocorrected (SSG) | SAR   precision geocorrected (SPG) | ScanSAR   narrow beam (SCN) | ScanSAR   wide beam (SCW) | ScanSAR   fine (SCF) | ScanSAR   sampled (SCS)|
|--- | --- | --- | --- | --- | --- | --- | --- | --- | ---|
|Spotlight | 1.3x0.4m | 1.0   or 0.8x1/3m | 0.5m | 0.5m | 0.5m |  |  |  | |
|Ultra-Fine | 1.3x2.1m | 1.0x1.0   or 0.8x0.8m | 1.56m | 1.56m | 1.56m |  |  |  | |
|Wide Ultra-Fine | 1.3x2.1m | 1.0m | 1.56m | 1.56m | 1.56m |  |  |  | |
|Multi-Look Fine | 2.7x2.9m | 3.13m | 6.25m | 6.25m | 6.25m |  |  |  | |
|Wide Multi-Look Fine | 2.7x2.9m | 3.13m | 6.25m | 6.25m | 6.25m |  |  |  | |
|Extra-Fine | Full Res: 2.7x2.9m<br>Fine Res: 4.3x5.8m<br>Full Res: 7.1x5.8m<br>Wide Res: 10.6x5.8m | 1 look: 2.0m<br>4 looks: 3.13m<br>28 looks: 5.0m | 1 look: 3.13m<br>4 looks: 6.25m<br>28 looks: 8.0m | 3.13m | 3.13m |  |  |  | |
|Fine | 4.7x5.1m | 3.13m | 6.25m | 6.25m | 6.25m |  |  |  | |
|Wide-Fine | 4.7x5.1m | 3.13m | 6.25m | 6.25m | 6.25m |  |  |  | |
|Standard | 8.0 or 11.8x5.1m | 8.0m | 12.5m | 12.5m | 12.5m |  |  |  | |
|Wide | 11.8x5.1m | 10.0m | 12.5m | 12.5m | 12.5m |  |  |  | |
|Extended High | 11.8x5.1m | 8.0m | 12.5m | 12.5m | 12.5m |  |  |  | |
|Extended Low | 8.0x5.1m | 10.0m | 12.5m | 12.5m | 12.5m |  |  |  | |
|Fine Quad-Pol | 4.7x5.1m | 3.13m | 3.13m | 3.13m | 3.13m |  |  |  | |
|Wide Quad-Pol | 4.7x5.1m | 3.13m | 3.13m | 3.13m | 3.13m |  |  |  | |
|Standard Quad-Pol | 8.0 or 11.8x5.1m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m |  |  |  | |
|Wide Standard Quad-Pol | 8.0 or 11.8x5.1m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m |  |  |  | |
|ScanSAR Narrow |  |  |  |  |  | 25.0m |  | 25.0m | 25.0m|
|ScanSAR Wide |  |  |  |  |  |  | 50.0m | 50.0m | 50.0m|
|Ship (Detection of vessels) |  |  |  |  |  |  |  | 40.0m | 20.0m|
|Ocean Surveillance |  |  |  |  |  |  |  | 50.0m | 35.0x25.0m|

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
- `Copernicus 30m Global DEM` ([buggy](https://forum.step.esa.int/t/terrain-correction-with-copernicus-dem/29025/11) for now, do not use it)
- `Copernicus 90m Global DEM` ([buggy](https://forum.step.esa.int/t/terrain-correction-with-copernicus-dem/29025/11) for now, do not use it)
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

    The pre-processing graph should also have a `Terrain Correction` step with the following wildcards that are set automatically in the module:

    - `$res_m`: Resolution in meters
    - `$res_deg`: Resolution in degrees
    - `$crs`: CRS
    - The nodata value should **always** be set to 0.
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
        <demName>GETASSE30</demName>
        <externalDEMFile/>
        <externalDEMNoDataValue>0.0</externalDEMNoDataValue>
        <externalDEMApplyEGM>true</externalDEMApplyEGM>
        <demResamplingMethod>BILINEAR_INTERPOLATION</demResamplingMethod>
        <imgResamplingMethod>BILINEAR_INTERPOLATION</imgResamplingMethod>
        <pixelSpacingInMeter>$res_m</pixelSpacingInMeter>
        <pixelSpacingInDegree>$res_deg</pixelSpacingInDegree>
        <mapProjection>$crs</mapProjection>
        <alignToStandardGrid>false</alignToStandardGrid>
        <standardGridOriginX>0.0</standardGridOriginX>
        <standardGridOriginY>0.0</standardGridOriginY>
        <nodataValueAtSea>true</nodataValueAtSea>
        <saveDEM>false</saveDEM>
        <saveLatLon>false</saveLatLon>
        <saveIncidenceAngleFromEllipsoid>false</saveIncidenceAngleFromEllipsoid>
        <saveLocalIncidenceAngle>false</saveLocalIncidenceAngle>
        <saveProjectedLocalIncidenceAngle>false</saveProjectedLocalIncidenceAngle>
        <saveSelectedSourceBand>true</saveSelectedSourceBand>
        <outputComplex>false</outputComplex>
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

- `EOREADER_SAR_DEFAULT_RES` (0.0 by default, which means using the product's default resolution)

## Documentary Sources

### Sentinel-1

- [Data Products](https://earth.esa.int/web/sentinel/missions/sentinel-1/data-products)
- [Acquisition Mode](https://earth.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes)

### Others

- [COSMO-Skymed Product Description](https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description)
- [TerraSAR-X Product Description](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)
- [RADARSAT-2 Product Description](https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html)
