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
TerraSAR-X & TanDEM-X & PAZ products.
More info `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_.
"""
import logging
import warnings
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import rasterio
from lxml import etree
from sertit import files, vectors
from sertit.misc import ListEnum

from eoreader import cache, cached_property
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.sar.sar_product import SarProduct, SarProductType
from eoreader.reader import Platform
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class TsxProductType(ListEnum):
    """
    TerraSAR-X & TanDEM-X & PAZ projection identifier.
    Take a look
    `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
    """

    SSC = "SSC"
    """Single Look Slant Range, Complex representation"""

    MGD = "MGD"
    """Multi Look Ground Range, Detected representation"""

    GEC = "GEC"
    """Geocoded Ellipsoid Corrected, Detected representation"""

    EEC = "EEC"
    """Enhanced Ellipsoid Corrected, Detected representation"""


@unique
class TsxSensorMode(ListEnum):
    """
    TerraSAR-X & TanDEM-X & PAZ sensor mode.
    Take a look
    `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
    """

    HS = "HS"
    """High Resolution Spotlight"""

    SL = "SL"
    """Spotlight"""

    ST = "ST"
    """Staring Spotlight"""

    SM = "SM"
    """Stripmap"""

    SC = "SC"
    """ScanSAR"""


@unique
class TsxPolarization(ListEnum):
    """
    TerraSAR-X & TanDEM-X & PAZ polarization mode.
    Take a look
    `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
    """

    SINGLE = "S"
    """"Single Polarization"""

    DUAL = "D"
    """"Dual Polarization"""

    QUAD = "Q"
    """"Quad Polarization"""

    TWIN = "T"
    """"Twin Polarization"""


@unique
class TsxSatId(ListEnum):
    """
    TerraSAR-X products satellite IDs + PAZ

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 29)
    """

    TDX = "TanDEM-X"
    """
    TanDEM-X
    """

    TSX = "TerraSAR-X"
    """
    TerraSAR-X
    """

    PAZ = "PAZ"
    """
    PAZ
    """


class TsxProduct(SarProduct):
    """Class for TerraSAR-X & TanDEM-X & PAZ Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)

        .. WARNING::
            - We assume being in High Resolution (except for WV where we must be in medium resolution)
            - Incidence angle: we consider the best option, around 55 degrees
        """
        # Read metadata
        try:
            root, _ = self.read_mtd()
            image_data = root.find(".//imageDataInfo")
            def_res = float(image_data.findtext(".//rowSpacing"))  # Square pixels
        except (InvalidProductError, TypeError):
            raise InvalidProductError(
                "imageDataInfo or rowSpacing not found in metadata!"
            )

        return def_res

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*IMAGE_{}_*"
        self._band_folder = self.path.joinpath("IMAGEDATA")

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Post init done by the super class
        super()._pre_init()

    def _get_platform(self) -> Platform:
        """ Getter of the platform """
        # TerraSAR-X & TanDEM-X products are all similar, we must check into the metadata to know the sensor
        root, _ = self.read_mtd()
        sat_id = root.findtext(".//mission")
        if not sat_id:
            raise InvalidProductError("Cannot find mission in the metadata file")
        sat_id = getattr(TsxSatId, sat_id.split("-")[0]).name
        return getattr(Platform, sat_id)

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self._snap_path = f"{self.name}.xml"

        # Post init done by the super class
        super()._post_init()

    @cached_property
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent
                                                        geometry
            0  POLYGON ((106.65491 -6.39693, 106.96233 -6.396...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open extent KML file
        try:
            extent_file = next(self.path.glob("**/*SUPPORT/GEARTH_POLY.kml"))
        except IndexError as ex:
            raise InvalidProductError(
                f"Extent file (products.kml) not found in {self.path}"
            ) from ex

        extent_wgs84 = vectors.read(extent_file).envelope

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            prod_type = root.findtext(".//productVariant")
        except TypeError:
            raise InvalidProductError("mode not found in metadata!")

        self.product_type = TsxProductType.from_value(prod_type)

        if self.product_type == TsxProductType.MGD:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == TsxProductType.SSC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )
        if self.product_type != TsxProductType.MGD:
            LOGGER.warning(
                "Other products type than MGD has not been tested for %s data. "
                "Use it at your own risks !",
                self.platform.value,
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from TerraSAR-X products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            imaging_mode = root.findtext(".//imagingMode")
        except TypeError:
            raise InvalidProductError("imagingMode not found in metadata!")

        # Get sensor mode
        try:
            self.sensor_mode = TsxSensorMode.from_value(imaging_mode)
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2016, 2, 29, 22, 30, 18)
            >>> prod.get_datetime(as_datetime=False)
            '20160229T223018'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            try:
                acq_date = root.findtext(".//start/timeUTC")
            except TypeError:
                raise InvalidProductError("start/timeUTC not found in metadata!")

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        if self.name is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            try:
                name = files.get_filename(
                    root.find(".//generalHeader").attrib.get("fileName")
                )
            except TypeError:
                raise InvalidProductError("ProductName not found in metadata!")
        else:
            name = self.name

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20200605T042203_20200605T042211"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element level1Product at 0x1b845b7ab88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        # Cloud paths
        try:
            mtd_from_path = "SAR*SAR*xml"

            return self._read_mtd_xml(mtd_from_path)
        except InvalidProductError:
            # Normal paths
            mtd_from_path = "SAR*xml"

            return self._read_mtd_xml(mtd_from_path)
