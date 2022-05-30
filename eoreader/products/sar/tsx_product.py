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
TerraSAR-X & TanDEM-X & PAZ products.
More info `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_.
"""
import logging
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import rasterio
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import crs
from sertit import files, rasters, vectors
from sertit.misc import ListEnum

from eoreader import cache
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.reader import Constellation
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


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

    S = "SINGLE"
    """"Single Polarization"""

    D = "DUAL"
    """"Dual Polarization"""

    Q = "QUAD"
    """"Quad Polarization"""

    T = "TWIN"
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


@unique
class TsxGeometricResolution(ListEnum):
    """
    TerraSAR-X & TanDEM-X & PAZ geometric resolution, either Radiometrically Enhanced Products or Spatially Enhanced Products.
    This would infer on the resolution of the band, but Copernicus EMS doesn't handled this so we keep SSC resolution as is ESA Data Access Portfolio.

    Take a look
    `here <https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
    """

    RE = "Radiometrically Enhanced Products "
    """The radiometrically enhanced product is optimized with respect to radiometry."""

    SE = "Spatially Enhanced Products "
    """The spatially enhanced product is designed for the highest possible square ground resolution."""


class TsxProduct(SarProduct):
    """Class for TerraSAR-X & TanDEM-X & PAZ Products"""

    class IceyeProduct(SarProduct):
        """
        Class for ICEYE Products
        Take a look
        `here <https://www.iceye.com/hubfs/Downloadables/ICEYE-Level-1-Product-Specs-2019.pdf>`_.
        """

        def __init__(
            self,
            product_path: Union[str, CloudPath, Path],
            archive_path: Union[str, CloudPath, Path] = None,
            output_path: Union[str, CloudPath, Path] = None,
            remove_tmp: bool = False,
            **kwargs,
        ) -> None:
            self._geometric_res = None

            # Initialization from the super class
            super().__init__(
                product_path, archive_path, output_path, remove_tmp, **kwargs
            )

            # Geometric resolution
            if self.product_type != TsxProductType.SSC:
                self._geometric_res = getattr(
                    TsxGeometricResolution, self.split_name[3]
                )

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        See here
        <here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
        for more information (Beam Modes)

        .. WARNING::
            - We force Spatially Enhanced Resolution (SE) as we keep SSC resolutions (as per the ESA Data Access Portfolio)
        """
        # TODO: Manage RE case ? Not handled by Copernicus EMS, so be careful...

        # Read metadata
        try:
            root, _ = self.read_mtd()
            acq_info = root.find(".//acquisitionInfo")
            polarization = TsxPolarization.from_value(
                acq_info.findtext(".//polarisationMode")
            )
        except (InvalidProductError, TypeError):
            raise InvalidProductError(
                "acquisitionInfo or polarisationMode not found in metadata!"
            )

        def_res = None
        if self.sensor_mode == TsxSensorMode.HS:
            if polarization == TsxPolarization.S:
                def_res = 1.1
            elif polarization == TsxPolarization.D:
                def_res = 2.2
        elif self.sensor_mode == TsxSensorMode.SL:
            if polarization == TsxPolarization.S:
                def_res = 1.7
            elif polarization == TsxPolarization.D:
                def_res = 3.4
        elif self.sensor_mode == TsxSensorMode.ST:
            if polarization == TsxPolarization.S:
                def_res = 0.24
        elif self.sensor_mode == TsxSensorMode.SM:
            if polarization == TsxPolarization.S:
                def_res = 3.3
            elif polarization == TsxPolarization.D:
                def_res = 6.6
        elif self.sensor_mode == TsxSensorMode.SC:
            # Read metadata
            try:
                root, _ = self.read_mtd()
                acq_info = root.find(".//acquisitionInfo")
                nof_beams = int(acq_info.findtext(".//numberOfBeams"))
            except (InvalidProductError, TypeError):
                raise InvalidProductError(
                    "imageDataInfo or rowSpacing not found in metadata!"
                )
            # Four beams
            if nof_beams == 4:
                def_res = 18.5

            elif nof_beams == 6:
                # Six beams
                def_res = 40.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")

        return def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        TSX+TDX: https://earth.esa.int/eogateway/missions/terrasar-x-and-tandem-x
        PAZ: https://earth.esa.int/eogateway/missions/paz
        """
        self.instrument = "SAR X-band"

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*IMAGE_{}_*"
        self._band_folder = self.path.joinpath("IMAGEDATA")

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Its original filename is its name
        self._use_filename = True

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _get_constellation(self) -> Constellation:
        """ Getter of the constellation """
        # TerraSAR-X & TanDEM-X products are all similar, we must check into the metadata to know the constellation
        root, _ = self.read_mtd()
        mission = root.findtext(".//mission")
        if not mission:
            raise InvalidProductError("Cannot find mission in the metadata file")
        constellation_id = getattr(TsxSatId, mission.split("-")[0]).name
        return getattr(Constellation, constellation_id)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self.snap_filename = f"{self.name}.xml"

        # Post init done by the super class
        super()._post_init(**kwargs)

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                   Name  ...                                           geometry
            0  Sentinel-1 Image Overlay  ...  POLYGON ((817914.501 4684349.823, 555708.624 4...
            [1 rows x 12 columns]

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        if self.product_type == TsxProductType.EEC:
            return rasters.get_extent(self.get_default_band_path()).to_crs(self.crs())
        else:
            return super().extent()

    @cache
    def crs(self) -> crs.CRS:
        """
        Get UTM projection

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_crs()
            CRS.from_epsg(32630)

        Returns:
            crs.CRS: CRS object
        """
        if self.product_type == TsxProductType.EEC:
            with rasterio.open(self.get_default_band_path()) as ds:
                return ds.crs
        else:
            return super().crs()

    @cache
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
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
        prod_type = root.findtext(".//productVariant")
        if not prod_type:
            raise InvalidProductError("productVariant not found in metadata!")

        self.product_type = TsxProductType.from_value(prod_type)

        if self.product_type in [
            TsxProductType.MGD,
            TsxProductType.GEC,
            TsxProductType.EEC,
        ]:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == TsxProductType.SSC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )
        if self.product_type == TsxProductType.GEC:
            LOGGER.warning(
                "GEC (Geocoded Ellipsoid Corrected) products type has never been tested for %s data. "
                "Use it at your own risks !",
                self.constellation.value,
            )
        elif self.product_type == TsxProductType.EEC:
            self.is_ortho = True

    def _set_sensor_mode(self) -> None:
        """
        Get products type from TerraSAR-X products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        imaging_mode = root.findtext(".//imagingMode")
        if not imaging_mode:
            raise InvalidProductError("imagingMode not found in metadata!")

        # Get sensor mode
        try:
            self.sensor_mode = TsxSensorMode.from_value(imaging_mode)
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
            acq_date = root.findtext(".//start/timeUTC")
            if not acq_date:
                raise InvalidProductError("start/timeUTC not found in metadata!")

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
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            name = files.get_filename(
                root.find(".//generalHeader").attrib.get("fileName")
            )
        except TypeError:
            raise InvalidProductError("ProductName not found in metadata!")

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
        # Cloud-stored paths
        try:
            mtd_from_path = "SAR*SAR*xml"

            return self._read_mtd_xml(mtd_from_path)
        except InvalidProductError:
            # Normal paths
            mtd_from_path = "SAR*xml"

            return self._read_mtd_xml(mtd_from_path)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            quicklook_path = str(next(self.path.glob("PREVIEW/BROWSE.tif")))
        except StopIteration:
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
        root, _ = self.read_mtd()

        # Get the orbit direction
        try:
            od = OrbitDirection.from_value(root.findtext(".//orbitDirection"))

        except TypeError:
            raise InvalidProductError("orbitDirection not found in metadata!")

        return od
