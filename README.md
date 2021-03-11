# EOReader

This project allows you to read and open satellite data.

```python
>>> from eoreader.reader import Reader
>>> from eoreader.bands.alias import *

>>> # Your variables
>>> path = r"path\to\your\satellite"  # Optical in this example

>>> # Create the reader object and open satellite data
>>> eoreader = Reader()  # This is a singleton
>>> prod = eoreader.open(path)  # The Reader will recognize the satellite type from its name

>>> # Get the footprint of the product (usable data) and its extent (envelope of the tile)
>>> footprint = prod.footprint
>>> extent = prod.extent

>>> # Load some bands and index
>>> bands, meta = prod.load([NDVI, MNDWI, GREEN, DEM])  # Resolution not specified: use product resolution
>>> ndvi = bands[NDVI]
>>> mndwi = bands[MNDWI]
>>> green = bands[GREEN]
>>> dem = bands[DEM]

>>> # Create a stack with some other bands
>>> stack, stk_meta = prod.stack([NDVI, MNDWI, GREEN, SLOPE])  # Resolution not specified: use product resolution

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

Accepted optical satellites are:

- `Sentinel-2`: **L2A** and **L1C**, zip files are accepted
- `Sentinel-2 Theia`: **L2A**, zip files are accepted
- `Sentinel-3`: **OLCI** and **SLSTR**
- `Landsat-1`: **MSS**
- `Landsat-2`: **MSS**
- `Landsat-3`: **MSS**
- `Landsat-4`: **TM** and **MSS**
- `Landsat-5`: **TM** and **MSS**
- `Landsat-7`: **ETM**
- `Landsat-8`: **OLCI**

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/Optical) to learn more about that.

## SAR data

Accepted SAR satellites are:

- `Sentinel-1` **GRD** + **SLC**, zip files are accepted
- `COSMO-SkyMed` **DGM** + **SCS**
- `TerraSAR-X` **MGD** (+ **SSC**, :warning: not tested, use it at your own risk)
- `RADARSAT-2` **SGF** (+ **SLC**, :warning: not tested, use it at your own risk), zip files are accepted

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/SAR) to learn more about that.

## Available index

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
- `LWCI`
- `MNDWI`
- `NBR`
- `NDGRI`
- `NDMI`
- `NDRE2`
- `NDRE3`
- `NDVI`
- `NDWI`
- `PGR`
- `RDI`
- `RGI`
- `RI`
- `SRSWIR`
- `TCBRI`
- `TCGRE`
- `TCWET`
- `WI`

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