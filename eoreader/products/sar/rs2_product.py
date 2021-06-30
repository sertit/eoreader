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
RADARSAT-2 products.
More info `here <https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs>`_.
"""
import difflib
import logging
import warnings
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import rasterio
from lxml import etree

from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.sar.sar_product import SarProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME
from sertit import vectors
from sertit.misc import ListEnum
from sertit.vectors import WGS84

LOGGER = logging.getLogger(EOREADER_NAME)

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class Rs2ProductType(ListEnum):
    """
    RADARSAT-2 projection identifier.
    Take a look `here <https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html>`_.
    """

    SLC = "SLC"
    """Single-look complex"""

    SGX = "SGX"
    """SAR georeferenced extra"""

    SGF = "SGF"
    """SAR georeferenced fine"""

    SCN = "SCN"
    """ScanSAR narrow beam"""

    SCW = "SCW"
    """ScanSAR wide beam"""

    SCF = "SCF"
    """ScanSAR fine"""

    SCS = "SCS"
    """ScanSAR sampled"""

    SSG = "SSG"
    """SAR systematic geocorrected"""

    SPG = "SPG"
    """SAR precision geocorrected"""


@unique
class Rs2SensorMode(ListEnum):
    """
    RADARSAT-2 sensor mode.
    Take a look `here <https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html>`_.

    .. WARNING:: The name in the metadata may vary !
    """

    # Single Beam Modes
    S = "Standard"
    """Standard Mode"""

    W = "Wide"
    """Spotlight Mode"""

    F = "Fine"
    """Wide Mode"""

    WF = "Wide Fine"
    """Wide Fine Mode"""

    MF = "Multi-Look Fine"
    """Multi-Look Fine Mode"""

    WMF = "Wide Multi-Look Fine"
    """Wide Multi-Look Fine Mode"""

    XF = "Extra-Fine"
    """Extra-Fine Mode"""

    U = "Ultra-Fine"
    """Ultra-Fine Mode"""

    WU = "Wide Ultra-Fine"
    """Wide Ultra-Fine Mode"""

    EH = "Extended High"
    """Extended High Mode"""

    EL = "Extended Low"
    """Extended Low Mode"""

    SQ = "Standard Quad-Pol"
    """Standard Quad-Pol Mode"""

    WSQ = "Wide Standard Quad-Pol"
    """Wide Standard Quad-Pol Mode"""

    FQ = "Fine Quad-Pol"
    """Fine Quad-Pol Mode"""

    WFQ = "Wide Fine Quad-Pol"
    """Spotlight Mode"""

    # ScanSAR Modes
    SCN = "ScanSAR Narrow"
    """Spotlight Mode"""

    SCW = "ScanSAR Wide"
    """Spotlight Mode"""

    OSVN = "Ocean Surveillance"
    """Ocean Surveillance Mode"""

    DVWF = "Ship Detection"
    """Ship Detection Mode"""

    # Spotlight Mode
    SLA = "Spotlight"
    """Spotlight Mode"""


@unique
class Rs2Polarization(ListEnum):
    """
    RADARSAT-2 polarization mode.
    Take a look `here <https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs>`_
    """

    HH = "HH"
    VV = "VV"
    VH = "VH"
    HV = "HV"


class Rs2Product(SarProduct):
    """
    Class for RADARSAT-2 Products

    You can use directly the .zip file
    """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        def_res = None

        # Read metadata
        try:
            root, nsmap = self.read_mtd()
            namespace = nsmap[None]
            def_res = float(root.findtext(f"{namespace}sampledPixelSpacing"))
        except (InvalidProductError, TypeError):
            pass

        # If we cannot read it in MTD, initiate survival mode
        if not def_res:
            if self.sensor_mode == Rs2SensorMode.SLA:
                def_res = 1.0 if self.product_type == Rs2ProductType.SGX else 0.5
            elif self.sensor_mode in [Rs2SensorMode.U, Rs2SensorMode.WU]:
                def_res = 1.0 if self.product_type == Rs2ProductType.SGX else 1.56
            elif self.sensor_mode in [
                Rs2SensorMode.MF,
                Rs2SensorMode.WMF,
                Rs2SensorMode.F,
                Rs2SensorMode.WF,
            ]:
                def_res = 3.13 if self.product_type == Rs2ProductType.SGX else 6.25
            elif self.sensor_mode == Rs2SensorMode.XF:
                def_res = 2.0 if self.product_type == Rs2ProductType.SGX else 3.13
                if self.product_type in [Rs2ProductType.SGF, Rs2ProductType.SGX]:
                    LOGGER.debug(
                        "This product is considered to have one look (not checked in metadata)"
                    )  # TODO
            elif self.sensor_mode in [Rs2SensorMode.S, Rs2SensorMode.EH]:
                def_res = 8.0 if self.product_type == Rs2ProductType.SGX else 12.5
            elif self.sensor_mode in [Rs2SensorMode.W, Rs2SensorMode.EL]:
                def_res = 10.0 if self.product_type == Rs2ProductType.SGX else 12.5
            elif self.sensor_mode in [Rs2SensorMode.FQ, Rs2SensorMode.WQ]:
                def_res = 3.13
            elif self.sensor_mode in [Rs2SensorMode.SQ, Rs2SensorMode.WSQ]:
                raise NotImplementedError(
                    "Not squared pixels management are not implemented in EOReader."
                )
            elif self.sensor_mode == Rs2SensorMode.SCN:
                def_res = 25.0
            elif self.sensor_mode == Rs2SensorMode.SCW:
                def_res = 50.0
            elif self.sensor_mode == Rs2SensorMode.DVWF:
                def_res = 40.0 if self.product_type == Rs2ProductType.SCF else 20.0
            elif self.sensor_mode == Rs2SensorMode.SCW:
                if self.product_type == Rs2ProductType.SCF:
                    def_res = 50.0
                else:
                    raise NotImplementedError(
                        "Not squared pixels management are not implemented in EOReader."
                    )
            else:
                raise InvalidTypeError(f"Unknown sensor mode {self.sensor_mode}")

        return def_res

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        # Private attributes
        self._raw_band_regex = "*imagery_{}.tif"
        self._band_folder = self.path
        self._snap_path = ""

        # Zipped and SNAP can process its archive
        self.needs_extraction = False

        # Post init done by the super class
        super()._post_init()

    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                                        geometry
            1  POLYGON ((106.57999 -6.47363, 107.06926 -6.473...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open extent KML file
        try:
            if self.is_archived:
                product_kml = vectors.read(self.path, archive_regex=".*product\.kml")
            else:
                extent_file = next(self.path.glob("*product.kml"))
                product_kml = vectors.read(extent_file)
        except IndexError as ex:
            raise InvalidProductError(
                f"Extent file (product.kml) not found in {self.path}"
            ) from ex

        extent_wgs84 = product_kml[
            product_kml.Name == "Polygon Outline"
        ].envelope.to_crs(WGS84)

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_product_type(self) -> None:
        """Set products type"""
        self._get_sar_product_type(
            prod_type_pos=-1,
            gdrg_types=Rs2ProductType.SGF,
            cplx_types=Rs2ProductType.SLC,
        )
        if self.product_type != Rs2ProductType.SGF:
            LOGGER.warning(
                "Other products type than SGF has not been tested for %s data. "
                "Use it at your own risks !",
                self.platform.value,
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from RADARSAT-2 products name (could check the metadata too)
        """
        # Get metadata
        root, nsmap = self.read_mtd()
        namespace = nsmap[None]

        # Get sensor mode
        # WARNING: this word may differ from the Enum !!! (no docs available)
        # Get the closest match
        sensor_mode_xml = root.findtext(f".//{namespace}acquisitionType")

        if sensor_mode_xml:
            sensor_mode = difflib.get_close_matches(
                sensor_mode_xml, Rs2SensorMode.list_values()
            )[0]
            try:
                self.sensor_mode = Rs2SensorMode.from_value(sensor_mode)
            except ValueError as ex:
                raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex
        else:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2016, 2, 28, 11, 24, 18)
            >>> prod.get_datetime(as_datetime=False)
            '20160228T112418'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        split_name = self.split_name

        date = f"{split_name[5]}T{split_name[6]}"

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element {http://www.rsi.ca/rs2/prod/xml/schemas}product at 0x1c0efbd37c8>,
            {None: '{http://www.rsi.ca/rs2/prod/xml/schemas}'})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        mtd_from_path = "product.xml"
        mtd_archived = "product\.xml"

        return self._read_mtd(mtd_from_path, mtd_archived)
