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

from eoreader.bands import SpectralBand
from eoreader.bands import spectral_bands as spb
from eoreader.products import DimapProduct
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


class PneoProduct(DimapProduct):
    """
    Class of Pleiades-Neo products.
    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._pan_res = 0.3
        self._ms_res = 1.2
        self._altitude = 620000

        # Post init done by the super class
        super()._pre_init(**kwargs)

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

    def _map_bands(self) -> None:
        """Set products type"""
        # Create spectral bands
        ca = SpectralBand(
            eoreader_name=spb.CA,
            **{NAME: "DEEP BLUE", ID: 5, GSD: self._ms_res, WV_MIN: 400, WV_MAX: 450}
        )

        pan = SpectralBand(
            eoreader_name=spb.PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 450, WV_MAX: 800}
        )

        blue = SpectralBand(
            eoreader_name=spb.BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self._ms_res, WV_MIN: 450, WV_MAX: 520}
        )

        green = SpectralBand(
            eoreader_name=spb.GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self._ms_res, WV_MIN: 490, WV_MAX: 610}
        )

        red = SpectralBand(
            eoreader_name=spb.RED,
            **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 600, WV_MAX: 720}
        )

        nir = SpectralBand(
            eoreader_name=spb.NIR,
            **{NAME: "NIR", ID: 4, GSD: self._ms_res, WV_MIN: 750, WV_MAX: 830}
        )

        vre = SpectralBand(
            eoreader_name=spb.VRE_1,
            **{NAME: "RED EDGE", ID: 6, GSD: self._ms_res, WV_MIN: 700, WV_MAX: 750}
        )
        self._map_bands_core(
            blue=blue, green=green, red=red, nir=nir, pan=pan, vre=vre, ca=ca
        )

    def _set_instrument(self) -> None:
        """
        Set instrument

        Pleiades: https://earth.esa.int/eogateway/missions/pleiades-neo
        """
        self.instrument = "Pleiades-Neo Imager"

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[-5]
