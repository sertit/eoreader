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
"""
COSMO-SkyMed products.
More info `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
"""
import logging
import warnings
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
from cloudpathlib import AnyPath, CloudPath
from lxml import etree
from sertit import files, strings, vectors
from sertit.misc import ListEnum
from shapely.geometry import Polygon

from eoreader import utils
from eoreader.exceptions import InvalidProductError
from eoreader.products.sar.sar_product import SarProduct, SarProductType
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class CskProductType(ListEnum):
    """
    COSMO-SkyMed products types.
    Take a look `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
    """

    RAW = "RAW"
    """Level 0"""

    SCS = "SCS"
    """Level 1A, Single-look Complex Slant, (un)balanced"""

    DGM = "DGM"
    """Level 1B, Detected Ground Multi-look"""

    GEC = "GEC"
    """Level 1C, Geocoded Ellipsoid Corrected"""

    GTC = "GTC"
    """Level 1D, Geocoded Terrain Corrected"""


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


@unique
class CskPolarization(ListEnum):
    """
    COSMO-SkyMed polarizations used during the acquisition.
    Take a look `here <https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description>`_.
    """

    HH = "HH"
    """Horizontal Tx/Horizontal Rx for Himage, ScanSAR and Spotlight modes"""

    VV = "VV"
    """Vertical Tx/Vertical Rx for Himage, ScanSAR and Spotlight modes"""

    HV = "HV"
    """Horizontal Tx/Vertical Rx for Himage, ScanSAR"""

    VH = "VH"
    """Vertical Tx/Horizontal Rx for Himage, ScanSAR"""

    CO = "CO"
    """Co-polar acquisition (HH/VV) for PingPong mode"""

    CH = "CH"
    """Cross polar acquisition (HH/HV) with Horizontal Tx polarization for PingPong mode"""

    CV = "CV"
    """Cross polar acquisition (VV/VH) with Vertical Tx polarization for PingPong mode"""


class CskProduct(SarProduct):
    """
    Class for COSMO-SkyMed Products

    .. code-block:: python

        >>> from eoreader.reader import Reader
        >>> # CSK products could have any folder but needs to have a .h5 file correctly formatted
        >>> # ie. "CSKS1_SCS_B_HI_15_HH_RA_SF_20201028224625_20201028224632.h5"
        >>> path = r"1011117-766193"
        >>> prod = Reader().open(path)
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        try:
            product_path = AnyPath(product_path)
            self._img_path = next(product_path.glob("*.h5"))
        except IndexError as ex:
            raise InvalidProductError(
                f"Image file (*.h5) not found in {product_path}"
            ) from ex
        self._real_name = files.get_filename(self._img_path)

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp)

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        def_res = None

        # Read metadata for default resolution
        try:
            root, _ = self.read_mtd()
            def_res = float(root.findtext(".//GroundRangeGeometricResolution"))
        except (InvalidProductError, TypeError):
            raise InvalidProductError(
                "GroundRangeGeometricResolution or rowSpacing not found in metadata !"
            )

        return def_res

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """

        # Private attributes
        self._raw_band_regex = "*_{}_*.h5"
        self._band_folder = self.path
        self._snap_path = self._img_path.name

        # Post init done by the super class
        super()._post_init()

    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1011117-766193"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                                        geometry
            0  POLYGON ((108.09797 15.61011, 108.48224 15.678...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        def from_str_to_arr(geo_coord: str):
            return np.array(strings.str_to_list(geo_coord), dtype=float)[:2][::-1]

        bl_corner = from_str_to_arr(root.findtext(".//GeoCoordBottomLeft"))
        br_corner = from_str_to_arr(root.findtext(".//GeoCoordBottomRight"))
        tl_corner = from_str_to_arr(root.findtext(".//GeoCoordTopLeft"))
        tr_corner = from_str_to_arr(root.findtext(".//GeoCoordTopRight"))

        if bl_corner is None:
            raise InvalidProductError("Invalid XML: missing extent.")

        extent_wgs84 = gpd.GeoDataFrame(
            geometry=[Polygon([tl_corner, tr_corner, br_corner, bl_corner])],
            crs=vectors.WGS84,
        )

        return extent_wgs84

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            # DGM_B, or SCS_B -> remove last 2 characters
            prod_type = root.findtext(".//ProductType")[:-2]
        except TypeError:
            raise InvalidProductError("mode not found in metadata !")

        self.product_type = CskProductType.from_value(prod_type)

        if self.product_type == CskProductType.DGM:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == CskProductType.SCS:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from S2 products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            acq_mode = root.findtext(".//AcquisitionMode")
        except TypeError:
            raise InvalidProductError("AcquisitionMode not found in metadata !")

        # Get sensor mode
        self.sensor_mode = CskSensorMode.from_value(acq_mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.platform.value} name: {self._real_name}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1011117-766193"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 10, 28, 22, 46, 25)
            >>> prod.get_datetime(as_datetime=False)
            '20201028T224625'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            acq_date = root.findtext(".//SceneSensingStartUTC")
        except TypeError:
            raise InvalidProductError("SceneSensingStartUTC not found in metadata !")

        # Convert to datetime
        # 2020-10-28 22:46:24.808662850
        # To many milliseconds (strptime accepts max 6 digits) -> needs to be cropped
        date = datetime.strptime(acq_date[:-3], "%Y-%m-%d %H:%M:%S.%f")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_split_name(self) -> list:
        """
        Get split name (erasing empty strings in it by precaution, especially for S1 data)

        Returns:
            list: Split products name
        """
        # Use the real name
        return utils.get_split_name(self._real_name)

    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1001513-735093"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element DeliveryNote at 0x2454ad4ee88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = f"DFDN_{self._real_name}.h5.xml"

        return self._read_mtd_xml(mtd_from_path)
