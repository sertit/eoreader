# Copyright 2025, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Environment variables that can change the processes"""

PP_GRAPH = "EOREADER_PP_GRAPH"
"""Environment variable for overriding default pre-processing graph path"""

DSPK_GRAPH = "EOREADER_DSPK_GRAPH"
"""Environment variable for overriding default despeckling graph path"""

SAR_DEF_PIXEL_SIZE = "EOREADER_SAR_DEFAULT_PIXEL_SIZE"
"""Environment variable for SAR default pixel size, used for SNAP orthorectification to override default pixel size."""

DEM_PATH = "EOREADER_DEM_PATH"
"""Environment variable for overriding default DEM path"""

DEM_VCRS = "EOREADER_DEM_VCRS"
"""
Environment variable for setting the vertical CRS of the DEM. 
Only useful to reproject your data with RPCs. 
Not useful if your DEM has already a vertical CRS or if its height is already taken from the ellipsoid.

- EOReader is able to detect the vertical CRS of the COPDEM (if COPDEM or Copernicus in its name).
- :code:`xdem` has also a mechanism of auto-detection of some CRS. See their documentation for more details.
"""

SNAP_DEM_NAME = "EOREADER_SNAP_DEM_NAME"
"""
Environment variable for overriding default DEM name used in SNAP.

Default is :code:`Copernicus 30m Global DEM`.
Can be :code:`GETASSE30`, :code:`SRTM 3Sec`, :code:`External DEM`...

If :code:`EOREADER_SNAP_DEM_NAME` is set to :code:`External DEM`,
SNAP will use your DEM stored in :code:`EOREADER_DEM_PATH` as an external DEM.
"""

S3_DB_URL_ROOT = "S3_DB_URL_ROOT"
"""Environment variable used for specify DB base url (e.g. :code:`https://s3.unistra.fr/bucket_name/`) """

TEST_USING_S3_DB = "TESTING_USING_S3_DB"
"""Environment variable to specify to use external DB as a opposed to local one. (For testing purposes only)"""

CI_EOREADER_BAND_FOLDER = "CI_EOREADER_BAND_FOLDER"
"""
Environment variable used in CI to override the existing band path
in order to bypass SNAP process and DEM reprojection.
"""

USE_DASK = "EOREADER_USE_DASK"
"""
If set (to 1) and :code:`dask` is installed, EOReader will read products as dask arrays instead of numpy arrays with the chunking defined in :code:`EOREADER_TILE_SIZE`.
"""

TILE_SIZE = "EOREADER_TILE_SIZE"
"""
If set, overrides the default tile size used in chunking (1024 by default, i.e. default chunk is :code:`{"band": 1, "x": 1024, "y": 1024}`).
Only used if :code:`EOREADER_USE_DASK` is set to 1.
If 'auto' is set, the value passed as chunks will be :code:`'auto'`.
"""

NOF_BANDS_IN_CHUNKS = "EOREADER_NOF_BANDS_IN_CHUNKS"
"""
If set, overrides the default number of bands to be considered used in chunking (1 by default, i.e. default chunk is :code:`{"band": 1, "x": 1024, "y": 1024}`).
Only used if :code:`EOREADER_USE_DASK` is set to 1.
Not used in case of :code:`EOREADER_USE_DASK` set as :code:`'auto'`.
"""

BAND_RESAMPLING = "EOREADER_BAND_RESAMPLING"
"""
Overrides the default resampling (bilinear) used when loading bands. 
Note that for discrete files such as masks, the nearest resampling is set in stone.

Available values (use the number and see rasterio's Resampling for more details and limitations):

- :code:`nearest = 0`
- :code:`bilinear = 1`
- :code:`cubic = 2`
- :code:`cubic_spline = 3`
- :code:`lanczos = 4`
- :code:`average = 5`
- :code:`mode = 6`
- :code:`gauss = 7`
- :code:`max = 8`
- :code:`min = 9`
- :code:`med = 10`
- :code:`q1 = 11`
- :code:`q3 = 12`
- :code:`sum = 13`
- :code:`rms = 14`

Examples:

    >>> import os
    >>>
    >>> # Nearest
    >>> os.environ["EOREADER_BAND_RESAMPLING"] = "0"
    >>> 
    >>> # Cubic
    >>> from rasterio.enums import Resampling
    >>> os.environ["EOREADER_BAND_RESAMPLING"] = str(Resampling.cubic)
"""

DEFAULT_DRIVER = "EOREADER_DEFAULT_DRIVER"
"""
Default driver for writing files on disk. 
Especially useful for intermediary files. 

Default is :code:`COG`. 

See GDAL supported raster drivers for more information: https://gdal.org/en/stable/drivers/raster/index.html
"""

LEGACY_BAND_NAME_RESOLUTION = "EOREADER_LEGACY_BAND_NAME_RESOLUTION"
"""
Keep legacy resolution in band name (:code:`1000-00m` instead of :code:`1000m`, or :code:`0-50m` instead of :code:`0-5m`)
"""

FIX_MAXAR = "EOREADER_FIX_MAXAR"
"""
Fix faulty Maxar product (corrupted shapes in metadata). 
This requires an alteration of the raw data, hence the possibility to block it by setting this environment variable to :code:`'0'`.
"""
