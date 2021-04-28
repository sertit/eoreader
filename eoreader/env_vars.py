# -*- coding: utf-8 -*-
# Copyright 2021, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" Environment variables that can change the processes """

PP_GRAPH = "EOREADER_PP_GRAPH"
"""Environment variables for overriding default pre-processing graph path"""

DSPK_GRAPH = "EOREADER_DSPK_GRAPH"
"""Environment variables for overriding default despeckling graph path"""

SAR_DEF_RES = "EOREADER_SAR_DEFAULT_RES"
"""Environment variables for SAR default resolution, used for SNAP orthorectification to override default resolution."""

S3_DEF_RES = "EOREADER_S3_DEFAULT_RES"
"""Environment variables for S3 default resolution, used for SNAP orthorectification to override default resolution."""

DEM_PATH = "EOREADER_DEM_PATH"
"""Environment variables for overriding default DEM path"""

CI_EOREADER_BAND_FOLDER = "CI_EOREADER_BAND_FOLDER"
"""
Environment variables used in CI to override the existing band path
in order to bypass SNAP process and DEM reprojection.
"""
