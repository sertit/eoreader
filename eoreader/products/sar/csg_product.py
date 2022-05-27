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
COSMO-SkyMed 2nd Generation products.
More info `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
"""
import logging
from enum import unique
from pathlib import Path
from typing import Union

import rasterio
import xarray as xr
from cloudpathlib import CloudPath
from sertit.misc import ListEnum

from eoreader.bands.bands import BandNames
from eoreader.exceptions import InvalidProductError
from eoreader.products import CosmoProduct
from eoreader.utils import EOREADER_NAME

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
    """SPOTLIGHT-2-MSOS"""

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
    """SPOTLIGHT-2C (standard and apodized). Resolution: Natural"""

    PP = "PINGPONG"
    """PingPong. Resolution: 8.0m"""

    QP = "QUADPOL"
    """QuadPol. Resolution: Natural"""

    SC1 = "SCANSAR-1"
    """ScanSar-1. Resolution: 14.0m"""

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

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        See here
        <here](https://earth.esa.int/eogateway/documents/20142/37627/COSMO-SkyMed-Second-Generation-Mission-Products-Description.pdf>`_
        for more information (tables 20).
        Taking the :code:`CSK legacy` values
        """
        if self.sensor_mode == CsgSensorMode.S2A:
            def_res = 0.4
        elif self.sensor_mode == CsgSensorMode.S2B:
            def_res = 0.63
        elif self.sensor_mode == CsgSensorMode.S2C:
            def_res = 0.8
        elif self.sensor_mode == CsgSensorMode.PP:
            def_res = 12.0
        elif self.sensor_mode == CsgSensorMode.SC1:
            def_res = 20.0
        elif self.sensor_mode == CsgSensorMode.SC2:
            def_res = 40.0
        elif self.sensor_mode in [CsgSensorMode.SM, CsgSensorMode.QP]:
            def_res = 3.0
        else:
            # Complex data has an empty field and its resolution is not known
            def_res = -1.0

        return def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        CSG: https://earth.esa.int/eogateway/missions/cosmo-skymed-second-generation
        """
        self.instrument = "SAR X-band"

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
        self.sensor_mode = CsgSensorMode.from_value(acq_mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.constellation.value} name: {self.name}"
            )

    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            CSG SCS Products do not have a default resolution

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        # In case of SCS data that doesn't have any resolution in the mtd
        if self.resolution < 0.0:
            with rasterio.open(path) as ds:
                self.resolution = ds.res[0]

        try:
            if resolution < 0.0:
                resolution = self.resolution
        except TypeError:
            pass

        return super()._read_band(
            path=path, band=band, resolution=resolution, size=size, **kwargs
        )
