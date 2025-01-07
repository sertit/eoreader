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
COSMO-SkyMed 2nd Generation products.
More info `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
"""

import logging
from enum import unique

from sertit.misc import ListEnum

from eoreader import EOREADER_NAME
from eoreader.exceptions import InvalidProductError
from eoreader.products import CosmoProduct

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CsgSensorMode(ListEnum):
    """
    COSMO-SkyMed 2nd Generation sensor mode.
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    S1A = "SPOTLIGHT-1A"
    """SPOTLIGHT-1A"""

    S1B = "SPOTLIGHT-1B"
    """SPOTLIGHT-1B"""

    S2A = "SPOTLIGHT-2A"
    """SPOTLIGHT-2A (standard and apodized)"""

    S2B = "SPOTLIGHT-2B"
    """SPOTLIGHT-2B (standard and apodized)"""

    S2C = "SPOTLIGHT-2C"
    """SPOTLIGHT-2C (standard and apodized)"""

    S1_MSOR = "SPOTLIGHT-1-MSOR"
    """SPOTLIGHT-1-MSOR"""

    S2_MSOS = "SPOTLIGHT-2-MSOS"
    """SPOTLIGHT-2-MSOS, DI2S"""

    S2_MSJN = "SPOTLIGHT-2-MSJN"
    """SPOTLIGHT-2-MSJN"""

    S1_OQR = "SPOTLIGHT-1-OQR"
    """SPOTLIGHT-1-OQR"""

    S2_OQS = "SPOTLIGHT-2-OQS"
    """SPOTLIGHT-2-OQS"""

    S1_EQR = "SPOTLIGHT-1-EQR"
    """SPOTLIGHT-1-EQR"""

    S2_EQS = "SPOTLIGHT-2-EQS"
    """SPOTLIGHT-2-EQS"""

    SM = "STRIPMAP"
    """SPOTLIGHT-2C (standard and apodized)"""

    PP = "PINGPONG"
    """PingPong"""

    QP = "QUADPOL"
    """QuadPol"""

    SC1 = "SCANSAR-1"
    """ScanSar-1"""

    SC2 = "SCANSAR-2"
    """ScanSar-2. Resolution: 27.0m"""

    NA = "N/A"
    """N/A"""


class CsgProduct(CosmoProduct):
    """
    Class for COSMO-SkyMed 2nd Generation Products
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        See here
        `here <https://earth.esa.int/eogateway/documents/20142/37627/COSMO-SkyMed-Second-Generation-Mission-Products-Description.pdf>`_
        for more information (tables 23-24: L1B/C/D Product features, table 20: L1A Product features for missing values).
        Taking the :code:`CSK legacy` values
        """
        # Complex data has an empty field and its pixel size is not known
        def_res = -1.0
        def_pixel_size = -1.0

        # See page 63
        nof_range_looks = int(self.split_name[4][:2])
        nof_az_looks = int(self.split_name[4][:-2])

        if self.sensor_mode == CsgSensorMode.S2A:
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 0.4
                def_pixel_size = 0.15
                # Apodized: 0.12
            elif nof_range_looks == 2 and nof_az_looks == 2:
                def_res = 0.7
                def_pixel_size = 0.3
            elif nof_range_looks == 3 and nof_az_looks == 3:
                def_res = 1.0
                def_pixel_size = 0.45

        elif self.sensor_mode in [CsgSensorMode.S2B, CsgSensorMode.S2_MSOS]:
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 0.7
                def_pixel_size = 0.25
                # Apodized: 0.2
            elif nof_range_looks == 2 and nof_az_looks == 2:
                def_res = 1.2
                def_pixel_size = 0.5
            elif nof_range_looks == 4 and nof_az_looks == 4:
                def_res = 2.3
                def_pixel_size = 1.0

        elif self.sensor_mode == CsgSensorMode.S2C:
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 0.8
                def_pixel_size = 0.3
                # Apodized: 0.24
            elif nof_range_looks == 2 and nof_az_looks == 2:
                def_res = 1.4
                def_pixel_size = 0.6
            elif nof_range_looks == 3 and nof_az_looks == 3:
                def_res = 2.1
                def_pixel_size = 0.9

        elif self.sensor_mode == CsgSensorMode.PP:
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 12.0
                def_pixel_size = 2.0
            elif nof_range_looks == 2 and nof_az_looks == 1:
                def_res = 12.0
                def_pixel_size = 4.0
            elif nof_range_looks == 5 and nof_az_looks == 2:
                def_res = 22.5
                def_pixel_size = 10.0

        elif self.sensor_mode == CsgSensorMode.SC1:
            # Case SCS
            # TODO: is this OK ?
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 20.0
                def_pixel_size = 14.0
            # GRD
            elif nof_range_looks == 3 and nof_az_looks == 1:
                def_res = 20.0
                def_pixel_size = 5.0
            elif nof_range_looks == 5 and nof_az_looks == 1:
                def_res = 23.0
                def_pixel_size = 10.0
            elif nof_range_looks == 8 and nof_az_looks == 2:
                def_res = 35.0
                def_pixel_size = 15.0

        elif self.sensor_mode == CsgSensorMode.SC2:
            # Case SCS
            # TODO: is this OK ?
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 40.0
                def_pixel_size = 27.0
            # GRD
            elif nof_range_looks == 4 and nof_az_looks == 1:
                def_res = 40.0
                def_pixel_size = 10.0
            elif nof_range_looks == 7 and nof_az_looks == 1:
                def_res = 47.0
                def_pixel_size = 20.0
            elif nof_range_looks == 16 and nof_az_looks == 3:
                def_res = 115.0
                def_pixel_size = 50.0

        elif self.sensor_mode in [CsgSensorMode.SM, CsgSensorMode.QP]:
            if nof_range_looks == 1 and nof_az_looks == 1:
                def_res = 3.0
                def_pixel_size = 1.25
            elif nof_range_looks == 2 and nof_az_looks == 2:
                def_res = 5.6
                def_pixel_size = 2.5
            elif nof_range_looks == 4 and nof_az_looks == 4:
                def_res = 11.2
                def_pixel_size = 5.0

        self.pixel_size = def_pixel_size
        self.resolution = def_res

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        # Calibration fails with CSG data
        LOGGER.debug(
            "SNAP Error: Calibration is useless for CSG data. Removing this step."
        )
        self._calibrate = False

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_instrument(self) -> None:
        """
        Set instrument

        CSG: https://earth.esa.int/eogateway/missions/cosmo-skymed-second-generation
        """
        self.instrument = "SAR X-band"

    def _set_sensor_mode(self) -> None:
        """Get sensor mode"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        acq_mode = root.findtext(".//AcquisitionMode")
        if not acq_mode:
            raise InvalidProductError("AcquisitionMode not found in metadata!")

        # Get sensor mode
        self.sensor_mode = CsgSensorMode.from_value(acq_mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.constellation.value} name: {self.name}"
            )
