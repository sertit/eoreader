# -*- coding: utf-8 -*-
# Copyright 2022, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" Cloud Bands """
from eoreader.bands.bands import BandNames


class CloudsBandNames(BandNames):
    """Clouds Band names"""

    RAW_CLOUDS = "RAW CLOUDS"
    """ Raw cloud raster (can be either QA raster, rasterized cloud vectors...) """

    CLOUDS = "CLOUDS"
    """ Binary mask of clouds (High confidence) """

    SHADOWS = "SHADOWS"
    """ Binary mask of shadows (High confidence) """

    CIRRUS = "CIRRUS"
    """ Binary mask of cirrus (High confidence) """

    ALL_CLOUDS = "ALL CLOUDS"
    """ All clouds (Including all high confidence clouds, shadows and cirrus) """


RAW_CLOUDS = CloudsBandNames.RAW_CLOUDS
CLOUDS = CloudsBandNames.CLOUDS
SHADOWS = CloudsBandNames.SHADOWS
CIRRUS = CloudsBandNames.CIRRUS  # Cirrus detected
ALL_CLOUDS = CloudsBandNames.ALL_CLOUDS


def is_clouds(clouds) -> bool:
    """
    Returns True if we have a Clouds-related keyword

    .. code-block:: python

        >>> from eoreader.bands import *
        >>> is_clouds(NDVI)
        False
        >>> is_clouds(HH)
        False
        >>> is_clouds(GREEN)
        False
        >>> is_clouds(SLOPE)
        False
        >>> is_clouds(CLOUDS)
        True
    """
    try:
        is_valid = CloudsBandNames(clouds)
    except ValueError:
        is_valid = False
    return is_valid
