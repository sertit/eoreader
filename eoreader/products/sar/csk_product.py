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
COSMO-SkyMed products.
More info `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
"""
import logging
from enum import unique

from sertit.misc import ListEnum

from eoreader.exceptions import InvalidProductError
from eoreader.products import CosmoProduct, CosmoProductType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CskSensorMode(ListEnum):
    """
    COSMO-SkyMed sensor mode.
    Take a look `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
    """

    HI = "HIMAGE"
    """Himage"""

    PP = "PINGPONG"
    """PingPong"""

    WR = "WIDEREGION"
    """Wide Region"""

    HR = "HUGEREGION"
    """Huge Region"""

    S2 = "ENHANCED SPOTLIGHT"
    """Enhanced Spotlight"""


class CskProduct(CosmoProduct):
    """
    Class for COSMO-SkyMed Products

    .. code-block:: python

        >>> from eoreader.reader import Reader
        >>> # CSK products could have any folder but needs to have a .h5 file correctly formatted
        >>> # ie. "CSKS1_SCS_B_HI_15_HH_RA_SF_20201028224625_20201028224632.h5"
        >>> path = r"1011117-766193"
        >>> prod = Reader().open(path)
    """

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        See here
        `here <https://earth.esa.int/eogateway/documents/20142/37627/COSMO-SkyMed-Mission-Products-Description.pdf>`_
        for more information (p. 30)
        """
        if self.sensor_mode == CskSensorMode.HI:
            if self.product_type == CosmoProductType.SCS:
                def_res = 3.0
            else:
                def_res = 5.0
        elif self.sensor_mode == CskSensorMode.PP:
            def_res = 20.0
        elif self.sensor_mode == CskSensorMode.WR:
            def_res = 30.0
        elif self.sensor_mode == CskSensorMode.HR:
            def_res = 100.0
        elif self.sensor_mode == CskSensorMode.S2:
            def_res = 1.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")

        return def_res

    def _set_sensor_mode(self) -> None:
        """
        Get products type from S2 products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        acq_mode = root.findtext(".//AcquisitionMode")
        if not acq_mode:
            raise InvalidProductError("AcquisitionMode not found in metadata!")

        # Get sensor mode
        self.sensor_mode = CskSensorMode.from_value(acq_mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.constellation.value} name: {self.name}"
            )

    def _set_instrument(self) -> None:
        """
        Set instrument

        CSK: https://earth.esa.int/eogateway/missions/cosmo-skymed
        """
        self.instrument = "SAR-2000"
