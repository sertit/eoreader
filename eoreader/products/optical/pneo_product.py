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
"""
Pleiades-Neo products.
See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
for more information.
"""

import logging

from eoreader import EOREADER_NAME
from eoreader.bands import BLUE, CA, GREEN, NIR, PAN, RED, VRE_1, SpectralBand
from eoreader.products import DimapV2Product
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN

LOGGER = logging.getLogger(EOREADER_NAME)


class PneoProduct(DimapV2Product):
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

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _map_bands(self) -> None:
        """Set products type"""
        # Create spectral bands
        ca = SpectralBand(
            eoreader_name=CA,
            **{NAME: "DEEP BLUE", ID: 5, GSD: self._ms_res, WV_MIN: 400, WV_MAX: 450},
        )

        pan = SpectralBand(
            eoreader_name=PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 450, WV_MAX: 800},
        )

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self._ms_res, WV_MIN: 450, WV_MAX: 520},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self._ms_res, WV_MIN: 490, WV_MAX: 610},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 600, WV_MAX: 720},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 4, GSD: self._ms_res, WV_MIN: 750, WV_MAX: 830},
        )

        vre = SpectralBand(
            eoreader_name=VRE_1,
            **{NAME: "RED EDGE", ID: 6, GSD: self._ms_res, WV_MIN: 700, WV_MAX: 750},
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
