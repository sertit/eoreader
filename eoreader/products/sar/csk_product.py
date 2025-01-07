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
COSMO-SkyMed products.
More info `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
"""

import logging
from enum import unique

from sertit.misc import ListEnum

from eoreader import EOREADER_NAME
from eoreader.exceptions import InvalidProductError
from eoreader.products import CosmoProduct, CosmoProductType

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

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        See here
        `here <https://earth.esa.int/eogateway/documents/20142/37627/COSMO-SkyMed-Mission-Products-Description.pdf>`_
        for more information (p. 30)
        """
        if self.sensor_mode == CskSensorMode.HI:
            def_pixel_size = 2.5
            def_res = 3.0 if self.product_type == CosmoProductType.SCS else 5.0
        elif self.sensor_mode == CskSensorMode.PP:
            def_pixel_size = 10.0
            def_res = 20.0
        elif self.sensor_mode == CskSensorMode.WR:
            def_pixel_size = 15.0
            def_res = 30.0
        elif self.sensor_mode == CskSensorMode.HR:
            def_pixel_size = 50.0
            def_res = 100.0
        elif self.sensor_mode == CskSensorMode.S2:
            def_pixel_size = 0.5
            def_res = 1.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")

        self.pixel_size = def_pixel_size
        self.resolution = def_res

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        if self.nof_swaths > 1:
            # Calibration fails with CSG data
            LOGGER.debug(
                "SNAP Error: Calibration currently fails for CSK data with multiple swaths. Removing this step."
            )
            self._calibrate = False

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_sensor_mode(self) -> None:
        """Get sensor mode"""
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
