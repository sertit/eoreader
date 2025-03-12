# Frequently Asked Questions (FAQ)

## EOReader

### Concretely, could you give me examples where EOReader really helps me?

Sure thing! Here is a handful of examples:

#### Handling Sentinel-2 from any epoch

Sentinel-2 products have greatly evolved since 2016:
- L2Ap products were not georeferenced back in the days!
- processing baselines have changed a lot since the beginning, i.e.:
  - masks have been translated from vectors to rasters
  - since some baseline you are not interested in, you need to remove an offset to compute in the reflectance, which wasn't the case before
  - ...

EOReader manages these changes for you!

#### Workarounds for bugs in third-party software

Third-party software are not bug free, especially when it comes to exotic products.
For example SNAP struggled to handle multiswath COSMO data
EOReader has a workaround for this.

In case of well known errors, EOReader will also give meaningful errors, helping you understand if this is a third-party software bug or not.

#### Geocoding and orthorectification

One example : EOReader geocodes and exports Sentinel-3 data in GeoTiff, allowing you to open them very easily in any GIS.

As EOReader only works with orthorectified data, this is also the case for any L1B product, as long as you provide a correct DEM.

#### Other really handy automations

A lot of other really handy automation are available. It's up to you to explore them!

one last example, EOReader treats multi-tile Planet data as one product, creating VRT and metadata on the fly!

### I want to load orthorectified bands, what do I need to do ?

EOReader always loads orthorectified bands, you cannot get raw bands !

- For Sentinel-3 data, EOReader creates GCPs and uses `rasterio.reproject` to geocode the wanted images. However, the result is slightly different from the one obtained by SNAP.
- For SAR images, EOReader uses SNAP to orthorectify the wanted images.
- For VHR data, if not already orthorectified, EOReader will use `rasterio.reproject` (with `RPC_DEM` keyword) to orthorectify the DIMAP stack.  
  However, this comes with several limitations:
    - Pay attention to give a sufficiently resolute DEM (does orthorectifying Pleiades data with a 30 m SRTM DEM make sense ?)
    - `gdalwarp` cannot access DEM through S3-compatible storage or https links. Be sure to link a DEM stored on disk, otherwise it'll be cached before reprojection.
    - This step is very time-consuming as the whole stack is reprojected for once. It may even never finish on your computer with very big images (sometimes VHR data can weight more than 15Go). It is best to give an already orthorectified stack on
      the side, you can see an example in the [VHR Notebook](https://eoreader.readthedocs.io/latest/notebooks/VHR.html)
- For other constellations, non-orthorectified bands are not supported yet.

### I want to load bands with a custom CRS, what do I need to do ?

For now, EOReader always loads bands with projected CRS (in UTM). 
So in order to do that, you sadly need a reprojection afterward.

We know that this policy may be an issue for:

- Sentinel-3 data that are very wide and may have inaccurate georeferencing.
- DIMAP data provided in WGS84 that need reprojection (and therefore time-consuming processes)

If needed, we could change in the future this to allow custom CRS. 
If so, do not hesitate to add comments in [this issue](https://github.com/sertit/eoreader/issues/5) on GitHub !

### I want to use Dask with EOReader, what should I do ?

First of all, be sure to have `dask[distributed]` installed in your environment. Then set the environment variable `EOREADER_USE_DASK` to 1.

The bands will be read and written using `rioxarray`'s dask functionalities, see [here](https://corteva.github.io/rioxarray/stable/examples/dask_read_write.html) for more information.

However, EOReader still relies a lot on `rasterio` (to orthorectify DIMAP products for example) or on SNAP, and these functions cannot be daskified. A lot of optimizations are left to do, do not hesitate to help us on that !

```{warning}
Dask is a functionality not really tested on EOReader, use it at your own risk
```

### SAR data fails to load extent

Sentinel-1 or other SAR constellations may fail to load KML extent files.
The cause is unknown, but a workaround based on `ogr2ogr` has been written.
Please be sure to have `ogr2ogr` (and other `GDAL` scripts available in your PATH)

For example, if you downloaded QGIS on Windows, you could simply put in your PATH:  
![qgis](https://zupimages.net/up/23/13/njvv.png)  
All GDAL scripts, exe, DLL, etc. are stored in the `bin` folder.

### I want to create a mosaic with EOReader, is it possible?

It is not possible with EOReader only. 
The goal of this library is to manage only one satellite product at a time. 
To handle more complicated sets of products (such as mosaics, pairs or time series), please consider using [`EOSets`](https://github.com/sertit/eosets).


## SNAP

> ⚠ Be sure to use SNAP 8.0 or more, and please verify that your software is up-to-date.

### SNAP DEM vs other DEM

SNAP has a capability to use its own DEMs. This does **not** interfere with the DEM provided to load a DEM band for example.

However, you can force SNAP to use your own DEM (stored in `EOREADER_DEM_PATH`, providing your DEM is compatible)
by setting the environment variable `EOREADER_SNAP_DEM_NAME` to `External DEM`.

However, it seems that SNAP can only use TIF dems... 

### What SNAP's GPT optimizations are you using ?

We are using some optimizations in order to optimize SNAP's GPT speed, as specified [here](https://sertit-utils.readthedocs.io/stable/api/sertit.snap.get_gpt_cli.html#sertit.snap.get_gpt_cli)

- **Memory**: We are allowing GPT to use 95% of your max virtual memory
- **CPU**: We are allowing GPT to use `max_core` - 2 cores of your computer (i.e. 14 cores out of 16)
- **Tiles**: Width and height are set to 2048 pixels (instead of 512x512) and cache to 50% of your max memory (instead of 1024Mo)

### SNAP known bugs

#### SNAP error: `Absolute radiometric calibration has already been applied to the product`

If SNAP 8.0 is used without any updates, the calibration step seems not be able to be skipped if the calibration step has already been applied. (see this [issue](https://github.com/sertit/eoreader/issues/42))
This is resolved when the software is updated.

Using SNAP 9.0 also resolves this.

#### SNAP `secure-processing` not recognized
Sometimes SNAP process returns `Feature 'http://javax.xml.XMLConstants/feature/secure-processing' is not recognized.`

This is a known SNAP bug.  

Just add the line `-Djavax.xml.parsers.SAXParserFactory=com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl` to your `gpt.vmoptions` file.  
Please look at [this issue](https://forum.step.esa.int/t/xmlfactory-error-using-snap-8/26566) for more information.

#### COSMO-SkyMed orthorectified files are empty

For an unknown reason, the SNAP calibration step doesn't work and set nodata everywhere.
A workaround is to set the file `cplx_no_calib_preprocess_default.xml` stored in `eoreader/data` in the `EOREADER_PP_GRAPH` environment variable.
Even if the product won't be calibrated, you will be able to work with some orthorectified data.

```python
import os
os.env["EOREADER_PP_GRAPH"] = "/home/eoreader/data/cplx_no_calib_preprocess_default.xml"
prod.load(VV)
```

#### Other bugs reported to SNAP forum

- [Error in Terrain Correction with PAZ ScanSAR SSC with multiple strips](https://forum.step.esa.int/t/error-in-terrain-correction-with-paz-scansar-ssc-with-multiple-strips/41259)
- [Error in Terrain Correction with CSG ScanSAR DGM](https://forum.step.esa.int/t/error-in-terrain-correction-with-csg-scansar-dgm/41261)
- [Missing swaths for multiswaths Cosmo-SkyMed SCS data](https://forum.step.esa.int/t/missing-swaths-for-multiswaths-cosmo-skymed-scs-data/38672) (a workaround is ready in EOReader, see [this issue](https://github.com/sertit/eoreader/issues/78))