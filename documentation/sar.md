# SAR data

|Satellites | Allowed Product Types | Use archive|
|--- | --- | ---|
|Sentinel-1 | SLC & GRD | Yes|
|COSMO-Skymed | DGM & SCS, (others should also be OK) | No|
|TerraSAR-X | MGD (SSC should be OK) | No|
|RADARSAT-2 | SGF (SLC should be OK) | Yes|

SAR satellites can only load `DEM` and `SLOPE` bands.

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/SAR) to learn more
about that.

## GPT graphs
You can change the SAR GPT graphs used by setting the following environment variables:

- `EOREADER_PP_GRAPH`: Environment variables for pre-processing graph path.  
- `EOREADER_DSPK_GRAPH`: Environment variables for despeckling graph path
  
**WARNING**:  
For performance reasons, the `Terrain Correction` step is done **before** the `Despeckle` step.
Indeed this step is very time-consuming and better done 
one time on the raw image than two times on both the raw and the despeckled image.  
Even if this is not the regular way of handling SAR data, 
this shouldn't really affect the quality of any extraction done after that.

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