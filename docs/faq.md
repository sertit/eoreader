# Frequently Asked Questions (FAQ)

## EOReader

### I want to load orthorectified bands, what do I need to do ?
EOReader always loads orthorectified bands, you cannot get raw bands !
- For Sentinel-3 data, EOReader creates GCPs and uses `rasterio.reproject` SNAP to geocode the wanted images. The result is slightly different than the one obtained by SNAP !
- For SAR images, EOReader uses SNAP to orthorectify the wanted images.
- For DIMAP data, if not already orthorectified, EOReader will use `rasterio.reproject` (with `RPC_DEM` keyword) to orthorectify the DIMAP stack.  
  However, this comes with several limitations:
  - Pay attention to give a sufficiently resolute DEM (does orthorectifying Pleiades data with a 30m SRTM DEM make sense ?)
  - `gdalwarp` cannot access DEM through S3-compatible storage or https links. Be sure to link a DEM stored on disk.
- For other sensors, non-orthorectified bands are not supported yet.

### I want to load projected bands, what do I need to do ?
EOReader always loads projected bands (in UTM). This may be an issue for:
- Sentinel-3 data that are very wide and may have inaccurate georeferencing.
- DIMAP data provided in WGS84 that need reprojection (and therefore time-consuming processes)

If needed, we could change this to allow WGS84 representation. If so, do not hesitate to open an issue on GitHub !

### I want to use Dask with EOReader, what should I do ?
First of all, be sure to have `dask[distributed]` installed in your environment.
Then set the environment variable `EOREADER_USE_DASK` to 1.

The bands will be read and written using `rioxarray`'s dask functionalities, 
see [here](https://corteva.github.io/rioxarray/stable/examples/dask_read_write.html) for more information.

However, EOReader still relies a lot on `rasterio` (to orthorectify DIMAP products for example) or on SNAP, 
and these functions cannot be daskified. A lot of optimizations are left to do, do not hesitate to help us on that !

```{warning}
Dask is a functionality not really tested on EOReader, use it at your own risk
```

## SNAP

### SNAP DEM vs other DEM
SNAP has a capability to use its own DEMs. 
This does **not** interfere with the DEM provided to load a DEM band for example.

However, you can force SNAP to use your own DEM (stored in `EOREADER_DEM_PATH`, providing your DEM is compatible) 
by setting the environment variable `EOREADER_SNAP_DEM_NAME` to `External DEM`.

### What SNAP's GPT optimizations are you using ?
We are using some optimizations in order to optimize SNAP's GPT speed, as specified [here](https://sertit.github.io/sertit-utils/sertit/snap.html#sertit.snap.get_gpt_cli)
- **Memory**: We are allowing GPT to use 95% of your max virtual memory
- **CPU**: We are allowing GPT to use `max_core` - 2 cores of your computer (i.e. 14 cores out of 16)
- **Tiles**: Width and height are set to 2048 pixels (instead of 512x512) and cache to 50% of your max memory (instead of 1024Mo)

### I have installed EOReader with Conda and I have troubles with SNAP

- Please remember that conda modifies your `PATH`, so the `gpt` exe can be lost.   
Do not hesitate to include it once again. For example:  
```python
import os
os.environ["PATH"] += += r";C:\Program Files\snap\bin"
```
- Sometimes a weird bug appears with conda and the .xml files stored in `eoreader/data` are not in the conda package.  
If it happens, please post an issue and in the meantime download them from [Github](https://github.com/sertit/eoreader/tree/master/eoreader/data), then set the graphs by hand:
```python
import os
os.environ["EOREADER_PP_GRAPH"] = r"your/path/to/grd_s1_preprocess_default.xml" # if you are analyzing S1 GRD data
os.environ["EOREADER_DSPK_GRAPH"] = r"your/path/to/sar_despeckle_default.xml"
```

### Known SNAP bugs

Sometimes SNAP process returns `Feature 'http://javax.xml.XMLConstants/feature/secure-processing' is not recognized.` 
This is a known SNAP bug.  
Just add the line `-Djavax.xml.parsers.SAXParserFactory=com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl` to your `gpt.vmoptions` file.  
Please look at [this issue](https://forum.step.esa.int/t/xmlfactory-error-using-snap-8/26566) for more information.