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
"""Environment variable for SAR default pixel ize, used for SNAP orthorectification to override default pixel size."""

DEM_PATH = "EOREADER_DEM_PATH"
"""Environment variable for overriding default DEM path"""

SNAP_DEM_NAME = "EOREADER_SNAP_DEM_NAME"
"""
Environment variable for overriding default DEM name used in SNAP.

Default is :code:`Copernicus 30m Global DEM`.
Can be :code:`GETASSE30`, :code:`SRTM 3Sec`, :code:`External DEM`...

If :code:`EOREADER_SNAP_DEM_NAME` is set to :code:`External DEM`,
SNAP will use your DEM stored in  :code:`EOREADER_DEM_PATH` as an external DEM.
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
If set, overrides the default tile size used in chunking (1024 by default, i.e. default chunk is {"band": 1, "x": 1024, "y": 1024}).
Only used if :code:`EOREADER_USE_DASK` is set to 1.
If 'auto' is set, the value passed as chunks will be 'auto'.
"""

NOF_BANDS_IN_CHUNKS = "EOREADER_NOF_BANDS_IN_CHUNKS"
"""
If set, overrides the default number of bands to be considered used in chunking (1 by default, i.e. default chunk is {"band": 1, "x": 1024, "y": 1024}).
Only used if :code:`EOREADER_USE_DASK` is set to 1.
Not used in case of :code:`EOREADER_USE_DASK` set as 'auto'.
"""
