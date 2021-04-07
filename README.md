# EOReader

This project allows you to read and open satellite data.

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Your variables
>>> path = r"path/to/your/satellite/product"  # Optical in this example
>>> # WARNING: you can leave the output_path empty, 
>>> # but EOReader will create an output directory right next to the product path
>>> output = r"path/to/your/output"

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()  # This is a singleton
>>> prod = eoreader.open(path, output_path=output)  # The Reader will recognize the satellite type from its name

>>> # Get the footprint of the product (usable data) and its extent (envelope of the tile)
>>> footprint = prod.footprint
>>> extent = prod.extent

>>> # Load some bands and index
>>> bands, meta = prod.load([NDVI, MNDWI, GREEN, DEM, HILLSHADE, CLOUDS])  # Resolution not specified: use product resolution
>>> ndvi = bands[NDVI]
>>> mndwi = bands[MNDWI]
>>> green = bands[GREEN]
>>> dem = bands[DEM]
>> > hillshade = bands[HILLSHADE]
>> > clouds = bands[CLOUDS]
>>> # NOTE: every array that comes out `load` are collocated, which isn't the case if you load arrays separately 
>>> # (important for DEM data as they may have different grids)

>>> # Create a stack with some other bands
>>> stack, stk_meta = prod.stack([NDVI, MNDWI, GREEN, SLOPE, CIRRUS])  # Resolution not specified: use product resolution

>>> # Read Metadata
>>> mtd, namespace = prod.read_mtd()
```

:bulb:  
Index and bands are opened as `numpy.ma.maskedarrays` 
(see [here](https://numpy.org/doc/stable/reference/maskedarray.generic.html) to learn more about it) and converted to float.
The mask corresponds to the nodata of your product, that is set to 0 by convention.

:warning:  

- This software relies on satellite's name to open them, so please do not modify them !
- Sentinel-3 and SAR products need [`SNAP gpt`](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to work.  
Ensure that you have the folder containing your `gpt.exe` in your `PATH`.

## Optical data
Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/Optical) to learn
more about that.

### Enabled optical satellites

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

### Band mapping between optical satellites is:

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

### Cloud bands
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

### DEM bands
Optical satellites can all load `DEM`, `SLOPE` and `HILLSHADE` bands.


## SAR data

|Satellites | Allowed Product Types | Use archive|
|--- | --- | ---|
|Sentinel-1 | SLC & GRD | Yes|
|COSMO-Skymed | DGM & SCS, (others should also be OK) | No|
|TerraSAR-X | MGD (SSC should be OK) | No|
|RADARSAT-2 | SGF (SLC should be OK) | Yes|

SAR satellites can only load `DEM` and `SLOPE` bands.

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/SAR) to learn more
about that.

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

See [here](https://extracteo.pages.sertit.unistra.fr/eoreader/index.m.html) for more info.

## Available functions

### For both SAR and Optical data

See [here](https://extracteo.pages.sertit.unistra.fr/eoreader/products/product.html) for more info.

### Only for Optical data

See [here](https://extracteo.pages.sertit.unistra.fr/eoreader/products/optical/optical_product.html) for more info.

### Only for SAR data

See [here](https://extracteo.pages.sertit.unistra.fr/eoreader/products/sar/sar_product.html) for more info.

## Environment variables

### GPT graphs
You can change the SAR GPT graphs used by setting the following environment variables:

- `EOREADER_PP_GRAPH`: Environment variables for pre-processing graph path.  
- `EOREADER_DSPK_GRAPH`: Environment variables for despeckling graph path

:warning:  
For performance reasons, the `Terrain Correction` step is done **before** the `Despeckle` step.
Indeed this step is very time-consuming and better done 
one time on the raw image than two times on both the raw and the despeckled image.  
Even if this is not the regular way of handling SAR data, 
this shouldn't really affect the quality of any extraction done after that.

#### What to know if you are changing a graph
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

Pay attention to set `$file` and `$out` and leave the `BEAM-DIMAP` file format. The first graph must orthorectify your
SAR data, but should not despeckle it. The second graph is precisely charged to do it.

The pre-processing graph should also have a `Terrain Correction` step with the following wildcards that are set automatically in the module:
- `$res_m`: Resolution in meters
- `$res_deg`: Resolution in degrees
- `$crs`: CRS
- The nodata value should **always** be set to 0.

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
You can override default SNAP resolution (in meters) when orthorecifying SAR and S3 bands by 
setting the following environment variables:

- `EOREADER_SAR_DEFAULT_RES` (0.0 by default, which means using the product's default resolution)
- `EOREADER_S3_DEFAULT_RES` (500m for SLSTR and 300m for OLCI data by default)