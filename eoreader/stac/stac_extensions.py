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
"""
STAC extensions:

- `STAC Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_
    - Cloud coverage (if existing)
- `STAC Projection Extension Specification <https://github.com/stac-extensions/projection/>`_
    - Projected (UTM) epsg, bbox, footprint, centroid...
- `STAC View Extension Specification <https://github.com/stac-extensions/view/>`_
    - Sun angles
    - Viewing position (in progress)
"""
import geopandas as gpd
from rasterio.crs import CRS

from eoreader import cache
from eoreader.stac._stac_keywords import (
    BBOX_FCT,
    CRS_FCT,
    EO_CC,
    GEOMETRY_FCT,
    VIEW_SUN_AZIMUTH,
    VIEW_SUN_ELEVATION,
)


class EoExtension:
    """
    Class of `Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_ of STAC items.
    """

    def __init__(self, **kwargs):
        self.cloud_cover = kwargs.get(EO_CC, "N/A")

        # TODO: add bands


class ProjExtension:
    """
    Class `Projection Extension Specification <https://github.com/stac-extensions/projection/>`_ of STAC items.
    """

    def __init__(self, **kwargs):
        self._crs_fct = kwargs.get(CRS_FCT, "N/A")
        self._geometry_fct = kwargs.get(GEOMETRY_FCT, "N/A")
        self._bbox_fct = kwargs.get(BBOX_FCT, "N/A")

    @cache
    def crs(self) -> CRS:
        """
        Getter of the projected CRS

        Returns:
            CRS: Projected CRS
        """
        return self._crs_fct()

    @cache
    def geometry(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected geometry (footprint)

        Returns:
            gpd.GeoDataFrame: Projected geometry
        """
        return self._geometry_fct().to_crs(self.crs())

    @cache
    def bbox(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected bbox (extent)

        Returns:
            gpd.GeoDataFrame: Projected bbox
        """
        return self._bbox_fct().to_crs(self.crs())


class ViewExtension:
    """
    Class `View Extension Specification <https://github.com/stac-extensions/view/>`_ of STAC items.
    """

    def __init__(self, **kwargs):
        self.sun_az = kwargs.get(VIEW_SUN_AZIMUTH, "N/A")
        self.sun_el = kwargs.get(VIEW_SUN_ELEVATION, "N/A")

        # TODO: Others will come
