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
RADARSAT-2 products.
More info `here <https://catalyst.earth/catalyst-system-files/help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs>`_.
"""
import difflib
import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
from lxml import etree
from sertit import files, vectors
from sertit.misc import ListEnum
from sertit.vectors import WGS84

from eoreader import cache
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.reader import Reader
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Rs2ProductType(ListEnum):
    """
    RADARSAT-2 projection identifier.
    Take a look `here <https://catalyst.earth/catalyst-system-files/help/references/gdb_r/RADARSAT-2.html>`_.
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
    Get product default resolution (in meters)
    See here
    <here](https://www.asc-csa.gc.ca/eng/satellites/radarsat/technical-features/radarsat-comparison.asp>`_
    for more information (Beam Modes)

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


class Rs2Product(SarProduct):
    """
    Class for RADARSAT-2 Products

    You can use directly the .zip file
    """

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        # -------------------------------------------------------------
        # Selective Single or Dual Polarization
        # Transmit H and/or V, receive H and/or V
        # F = "Fine", WF = "Wide Fine"
        if self.sensor_mode in [Rs2SensorMode.F, Rs2SensorMode.WF]:
            def_res = 8.0
        # S = "Standard", W = "Wide"
        elif self.sensor_mode in [Rs2SensorMode.S, Rs2SensorMode.W]:
            def_res = 25.0
        # SCN = "ScanSAR Narrow"
        elif self.sensor_mode == Rs2SensorMode.SCN:
            def_res = 50.0
        # SCW = "ScanSAR Wide"
        elif self.sensor_mode == Rs2SensorMode.SCW:
            def_res = 100.0

        # -------------------------------------------------------------
        # Polarimetric
        # Transmit H and V on alternate pulses /
        # receive H and V on any pulse
        # FQ = "Fine Quad-Pol", WFQ = "Wide Fine Quad-Pol"
        elif self.sensor_mode in [Rs2SensorMode.FQ, Rs2SensorMode.WFQ]:
            def_res = 12.0
        # SQ = "Standard Quad-Pol", "Wide Standard Quad-Pol"
        elif self.sensor_mode in [Rs2SensorMode.SQ, Rs2SensorMode.WSQ]:
            def_res = 25.0

        # -------------------------------------------------------------
        # Single Polarization HH
        # Transmit H, receive H
        # EH = "Extended High"
        elif self.sensor_mode == Rs2SensorMode.EH:
            def_res = 25.0
        # EL = "Extended Low"
        elif self.sensor_mode == Rs2SensorMode.EL:
            def_res = 60.0

        # -------------------------------------------------------------
        # Selective Single Polarization
        # Transmit H or V, receive H or V
        # EH = "Extended High"
        # SLA = "Spotlight"
        elif self.sensor_mode == Rs2SensorMode.SLA:
            def_res = 1.0
        # U = "Ultra-Fine", WU = "Wide Ultra-Fine"
        elif self.sensor_mode in [Rs2SensorMode.U, Rs2SensorMode.WU]:
            def_res = 3.0
        # XF = "Extra-Fine"
        elif self.sensor_mode == Rs2SensorMode.XF:
            def_res = 5.0
        # MF = "Multi-Look Fine", WMF = "Wide Multi-Look Fine"
        elif self.sensor_mode in [Rs2SensorMode.MF, Rs2SensorMode.WMF]:
            def_res = 8.0

        # -------------------------------------------------------------
        # Ocean surveillance and detection of vessels
        elif self.sensor_mode == Rs2SensorMode.OSVN:
            def_res = 50.0

        elif self.sensor_mode == Rs2SensorMode.DVWF:
            def_res = 35.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")

        return def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        RADARSAT: https://earth.esa.int/eogateway/missions/radarsat
        """
        self.instrument = "SAR C-band"

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*imagery_{}.tif"
        self._band_folder = self.path
        self.snap_filename = ""

        # Its original filename is its name
        self._use_filename = True

        # SNAP can process non-complex archive
        root, nsmap = self.read_mtd()
        namespace = nsmap[None]

        # Open identifier
        prod_type = root.findtext(f".//{namespace}productType")
        if not prod_type:
            raise InvalidProductError("productType not found in metadata!")

        self.product_type = Rs2ProductType.from_value(prod_type)
        self.needs_extraction = self.product_type == Rs2ProductType.SLC

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """

        # Post init done by the super class
        super()._post_init(**kwargs)

    @cache
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
                product_kml = vectors.read(self.path, archive_regex=r".*product\.kml")
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
        if self.product_type == Rs2ProductType.SLC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            self.sar_prod_type = SarProductType.GDRG

        if self.product_type not in [Rs2ProductType.SGF, Rs2ProductType.SLC]:
            LOGGER.warning(
                "Other product types than SGF or SLC haven't been tested for %s data. "
                "Use it at your own risks !",
                self.constellation.value,
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
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
        if self.datetime is None:
            # Get MTD XML file
            root, nsmap = self.read_mtd()
            namespace = nsmap[None]

            # Open identifier
            acq_date = root.findtext(f".//{namespace}rawDataStartTime")
            if not acq_date:
                raise InvalidProductError("rawDataStartTime not found in metadata!")

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        name = self.filename

        # Test filename
        reader = Reader()
        if not reader.valid_name(name, self._get_constellation()):
            LOGGER.warning(
                "This RADARSAT-2 filename is not valid. "
                "However RADARSAT-2 files do not provide anywhere the true name of the product. "
                "Use it with caution."
            )

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
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
        mtd_archived = r"product\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = files.get_archived_rio_path(
                    self.path, file_regex=r".*BrowseImage\.tif"
                )
            else:
                quicklook_path = str(next(self.path.glob("BrowseImage.tif")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    @cache
    def get_orbit_direction(self) -> OrbitDirection:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_orbit_direction().value
            "DESCENDING"

        Returns:
            OrbitDirection: Orbit direction (ASCENDING/DESCENDING)
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()
        namespace = nsmap[None]

        # Get the orbit direction
        try:
            od = OrbitDirection.from_value(
                root.findtext(f".//{namespace}passDirection").upper()
            )

        except TypeError:
            raise InvalidProductError("passDirection not found in metadata!")

        return od
