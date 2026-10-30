# Frequently Asked Questions (FAQ)

## EOReader

### Could you give me concrete examples of how EOReader helps?

Sure! Here are several examples:

#### Handling Sentinel-2 from any epoch

Sentinel-2 products have greatly evolved since 2016:
- L2Ap products were not georeferenced back in the day!
- Processing baselines have changed a lot since the beginning; for example:
  - Masks have been translated from vectors to rasters
  - Since a certain baseline, you may need to remove an offset to compute reflectance, which was not the case before
  - ...

EOReader manages these changes for you!

#### Workarounds for bugs in third-party software

Third-party software is not bug-free, especially when it comes to exotic products.
For example, SNAP struggled to handle multiswath COSMO data.
EOReader has a workaround for this.

In the case of well-known errors, EOReader will also provide meaningful error messages, helping you understand whether it is a third-party software bug or not.

#### Geocoding and orthorectification

One example: EOReader geocodes and exports Sentinel-3 data in GeoTIFF, allowing you to open it very easily in any GIS.

Since EOReader only works with orthorectified data, this is also true for any L1B product, as long as you provide a correct DEM.

#### Other really handy automations

Many other handy automations are available. It is up to you to explore them!

One last example: EOReader treats multi-tile Planet data as one product, creating VRTs and metadata on the fly!

### I want to load orthorectified bands, what do I need to do?

EOReader always loads orthorectified bands; you cannot get raw bands!

- For Sentinel-3 data, EOReader creates GCPs and uses `rasterio.reproject` to geocode the desired images. However, the result is slightly different from that obtained by SNAP.
- For SAR images, EOReader uses SNAP to orthorectify the desired images.
- For VHR data, if not already orthorectified, EOReader will use `rasterio.reproject` (with the `RPC_DEM` keyword) to orthorectify the DIMAP stack.  
  However, this comes with several limitations:
    - Be sure to use a DEM with sufficient resolution (does orthorectifying Pleiades data with a 90 m SRTM DEM make sense?)
    - `gdalwarp` cannot access DEMs through S3-compatible storage or HTTPS links. Be sure to provide a DEM stored on disk; otherwise, it will be cached before reprojection.
    - This step is very time-consuming as the whole stack is reprojected once. It may even never finish on your computer with huge images (VHR data can sometimes weigh more than 15 GB). It is best to provide an already orthorectified stack on the side; you can see an example in the [VHR Notebook](https://eoreader.readthedocs.io/latest/notebooks/VHR.html)
- For other constellations, non-orthorectified bands are not yet supported.

### I want to load bands with a custom CRS, what do I need to do?

Currently, EOReader always loads bands with a projected CRS (in UTM). 
Therefore, you would need to perform a reprojection afterward.

We know that this policy may be an issue for:

- Sentinel-3 data, which can be vast and may have inaccurate georeferencing.
- DIMAP data provided in WGS84 that requires reprojection (and therefore time-consuming processes)

If needed, we could change this in the future to allow custom CRS. 
If so, do not hesitate to add comments in [this issue](https://github.com/sertit/eoreader/issues/5) on GitHub!

### I want to use Dask with EOReader, what should I do?

First, be sure to have `dask[distributed]` installed in your environment. 
Then set the environment variable `EOREADER_USE_DASK` to 1.

```{warning}
The only guarantee you have for now is that EOReader will work with Dask arrays. 
However, EOReader is not yet lazy.
```

This goal will be pursued in the near future, but be aware that it may be impossible to implement properly due to ecosystem immaturity in this area.

However, EOReader still relies heavily on libraries that are partially or totally incompatible with Dask (such as `rasterio` for orthorectifying with RPCs) or on SNAP, and these functions can hardly be lazy.
Many optimizations are left to be done; do not hesitate to help us with this!


### SAR data fails to load extent

Sentinel-1 or other SAR constellations may fail to load KML extent files.
The cause is unknown, but a workaround based on `ogr2ogr` has been written.
Please be sure to have `ogr2ogr` (and other GDAL scripts) available in your PATH if you encounter such issues.


### I want to create a mosaic with EOReader, is it possible?

It is not possible with EOReader alone. 
The goal of this library is to manage only one satellite product at a time. 
To handle more complicated sets of products (such as mosaics, pairs, or time series), please consider using [`EOSets`](https://github.com/sertit/eosets).


## SNAP

> ⚠️ Be sure to use SNAP 8.0 or later, and please verify that your software is up to date.

### SNAP DEM vs. other DEM

SNAP can use its own DEMs. This does **not** interfere with the DEM provided to load a DEM band, for example.

However, you can force SNAP to use your own DEM (stored in `EOREADER_DEM_PATH`), provided your DEM is compatible,
by setting the environment variable `EOREADER_SNAP_DEM_NAME` to `External DEM`.

However, it seems that SNAP can only use TIFF DEMs. 

### What SNAP GPT optimizations are you using?

We are using optimizations to improve SNAP GPT speed, as specified [here](https://sertit-utils.readthedocs.io/stable/api/sertit.snap.get_gpt_cli.html#sertit.snap.get_gpt_cli)

- **Memory**: We allow GPT to use 95% of your maximum virtual memory
- **CPU**: We allow GPT to use `max_core` - 2 cores of your computer (e.g., 14 cores out of 16)
- **Tiles**: Width and height are set to 2048 pixels (instead of 512x512), and cache is set to 50% of your maximum memory (instead of 1024 MB)

### SNAP known bugs

#### SNAP error: `Absolute radiometric calibration has already been applied to the product`

If SNAP 8.0 is used without any updates, the calibration step seems unable to be skipped if it has already been applied (see [this issue](https://github.com/sertit/eoreader/issues/42)).
This is resolved when the software is updated.

Using SNAP 9.0 also resolves this.

#### SNAP `secure-processing` not recognized
Sometimes, SNAP processes return `Feature 'http://javax.xml.XMLConstants/feature/secure-processing' is not recognized.`

This is a known SNAP bug.

Add the line `-Djavax.xml.parsers.SAXParserFactory=com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl` to your `gpt.vmoptions` file. 
Please see [this issue](https://forum.step.esa.int/t/xmlfactory-error-using-snap-8/26566) for more information.

#### COSMO-SkyMed orthorectified files are empty

For an unknown reason, the SNAP calibration step does not work and sets nodata everywhere.
A workaround is to set the `EOREADER_PP_GRAPH` environment variable to the file `cplx_no_calib_preprocess_default.xml` stored in `eoreader/data`.
Even if the product will not be calibrated, you will be able to work with orthorectified data.

```python
import os
os.environ["EOREADER_PP_GRAPH"] = "/home/eoreader/data/cplx_no_calib_preprocess_default.xml"
prod.load(VV)
```

#### Other bugs reported to the SNAP forum

- [Error in Terrain Correction with PAZ ScanSAR SSC with multiple strips](https://forum.step.esa.int/t/error-in-terrain-correction-with-paz-scansar-ssc-with-multiple-strips/41259)
- [Error in Terrain Correction with CSG ScanSAR DGM](https://forum.step.esa.int/t/error-in-terrain-correction-with-csg-scansar-dgm/41261)
- [Missing swaths for multiswaths Cosmo-SkyMed SCS data](https://forum.step.esa.int/t/missing-swaths-for-multiswaths-cosmo-skymed-scs-data/38672) (a workaround is ready in EOReader; see [this issue](https://github.com/sertit/eoreader/issues/78))