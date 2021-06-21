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
""" Landsat-7 products """
import logging

import geopandas as gpd

from eoreader.products.optical.landsat_product import LandsatProduct
from eoreader.utils import EOREADER_NAME
from sertit import rasters

LOGGER = logging.getLogger(EOREADER_NAME)


class L7Product(LandsatProduct):
    """Class of Landsat-7 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT PAN AND TIRS RES
        return 30.0

    def _set_product_type(self) -> None:
        """Set products type"""
        self._set_etm_product_type()

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. WARNING::
            As Landsat 7 is broken (with nodata stripes all over the bands),
            the footprint is not easily computed and may take some time to be delivered.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        Indeed, nodata pixels vary according to the band sensor footprint,
        whereas QA nodata is where at least one band has nodata.

        We chose to keep QA nodata values for the footprint in order to show where all bands are valid.

        **TL;DR: We use the QA nodata value to determine the product's footprint**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        LOGGER.warning(
            "Due to the Landsat-7 gaps, this function returns a rounded footprint on the corners. "
            "Sorry for the inconvenience."
        )

        # Read the file with a very low resolution -> use raster_rio that is faster !
        gap_msk = rasters.read(
            self._get_path(self._pixel_quality_id),
            resolution=self.resolution * 50,
            masked=False,
        )

        # Vectorize the nodata band
        # Take the convex hull to discard the stripes of L7 to simplify the geometries
        footprint = rasters.vectorize(
            gap_msk, values=1, keep_values=False, dissolve=True
        )

        # Keep only the convex hull
        footprint.geometry = footprint.geometry.convex_hull

        return footprint
