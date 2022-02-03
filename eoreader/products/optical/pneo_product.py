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
Pleiades products.
See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
for more information.
"""
import logging
from pathlib import Path
from typing import Union

from cloudpathlib import CloudPath

from eoreader.products import DimapBandCombination, DimapProduct
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


class PneoProduct(DimapProduct):
    """
    Class of Pleiades-Neo products.
    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    for more information.
    """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # Not Pansharpened images
        if self.band_combi in [
            DimapBandCombination.MS,
            DimapBandCombination.MS_X,
            DimapBandCombination.MS_N,
            DimapBandCombination.MS_FS,
        ]:
            return 1.2
        # Pansharpened images
        else:
            return 0.3

    def _get_ortho_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """
        if self.product_type in self._proj_prod_type:
            # ERROR BECAUSE RASTERIO/GDAL DOES NOT HANDLE PLEIADES-NEO RPCs
            raise NotImplementedError(
                "Pleiades-Neo RPCs file nomenclature is not yet handled by rasterio. "
                "See https://github.com/rasterio/rasterio/issues/2388. "
                "GDAL PR is here: https://github.com/OSGeo/gdal/pull/5090"
            )

        else:
            ortho_path = self._get_tile_path()

        return ortho_path
