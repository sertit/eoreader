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
""" DEM Bands """
from eoreader.bands.bands import BandNames


class DemBandNames(BandNames):
    """DEM Band names"""

    DEM = "DEM"
    """ DEM """

    SLOPE = "SLOPE"
    """ Slope """

    HILLSHADE = "HILLSHADE"
    """ Hillshade """


DEM = DemBandNames.DEM
SLOPE = DemBandNames.SLOPE
HILLSHADE = DemBandNames.HILLSHADE


def is_dem(dem) -> bool:
    """
    Returns True if we have a DEM-related keyword

    .. code-block:: python

        >>> from eoreader.bands import *
        >>> is_dem(NDVI)
        False
        >>> is_dem(HH)
        False
        >>> is_dem(GREEN)
        False
        >>> is_dem(SLOPE)
        True
        >>> is_dem(CLOUDS)
        False
    """
    try:
        is_valid = DemBandNames(dem)
    except ValueError:
        is_valid = False
    return is_valid
