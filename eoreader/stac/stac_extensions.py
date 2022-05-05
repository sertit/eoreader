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


class EoExtension:
    """
    Class of `Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        self.cloud_cover = None

        try:
            if prod._has_cloud_cover:
                self.cloud_cover = prod.get_cloud_cover()
        except AttributeError:
            pass

        self.bands = prod.bands


class ProjExtension:
    """
    Class `Projection Extension Specification <https://github.com/stac-extensions/projection/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        self._prod = prod

    @cache
    def crs(self) -> CRS:
        """
        Getter of the projected CRS

        Returns:
            CRS: Projected CRS
        """
        return self._prod.crs()

    @cache
    def geometry(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected geometry (footprint)

        Returns:
            gpd.GeoDataFrame: Projected geometry
        """
        if self._prod.is_ortho:
            return self._prod.footprint().to_crs(self.crs())
        else:
            return self.bbox()

    @cache
    def bbox(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected bbox (extent)

        Returns:
            gpd.GeoDataFrame: Projected bbox
        """
        return self._prod.extent().to_crs(self.crs())


class ViewExtension:
    """
    Class `View Extension Specification <https://github.com/stac-extensions/view/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        try:
            sun_az, sun_el = prod.get_mean_sun_angles()
            self.sun_az = sun_az
            self.sun_el = sun_el
        except AttributeError:
            self.sun_az = None
            self.sun_el = None

        # TODO: Others will come
        # VIEW_OFF_NADIR = "view:off_nadir"
        # VIEW_INCIDENCE_ANGLE = "view:incidence_angle"
        # VIEW_AZIMUTH = "view:azimuth"
