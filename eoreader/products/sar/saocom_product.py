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
from typing import Union

import geopandas as gpd
from lxml import etree
from sertit import files, rasters, vectors
from sertit.misc import ListEnum
from shapely.geometry import Polygon

from eoreader import cache
from eoreader.bands import SarBandNames
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.products.sar.sar_product import _ExtendedFormatter
from eoreader.utils import DATETIME_FMT, EOREADER_NAME, simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class SaocomProductType(ListEnum):
    """
    SAOCOM Processing levels.
    Take a look
    `here <https://earth.esa.int/eogateway/catalog/saocom-data-products>`_
    """

    SLC = "L1A"
    """L1A - SLC (single look complex, slant range)"""

    DI = "L1B"
    """L1B - DI (detected image, ground range)"""

    GEC = "L1C"
    """L1C - GEC (geocoded on ellipsoid)"""

    GTC = "L1D"
    """L1D - GTC (geocoded on DEM)"""


@unique
class SaocomSensorMode(ListEnum):
    """
    SAOCOM Acquisition Mode mode.
    Take a look
    `here <https://saocom.veng.com.ar/L1-product-format-EN.pdf>`_
    """

    SM = "STRIPMAP"
    """Stripmap"""

    TN = "TOPSAR Narrow"
    """TOPSAR Narrow"""

    TW = "TOPSAR Wide"
    """TOPSAR Wide"""


@unique
class SaocomPolarization(ListEnum):
    """
    SAOCOM polarization mode.
    Take a look
    `here <https://saocom.veng.com.ar/L1-product-format-EN.pdf>`_

    acquiredPols:
    - HH
    - HV
    - VH
    - VV
    - HH-HV
    - VH-VV
    - HH-HV-VH-VV
    - LeftH-LeftV
    - RightH-RightV

    Polarization
    - HH
    - VV
    - HV
    - VH
    - CL/H
    - CL/V
    - CR/H
    - CR/V
    """

    SP = "SP"
    """"Single Polarization (HH or VV)"""

    DP = "DP"
    """"Dual Polarization (HH/HV or VV/VH)"""

    QP = "QP"
    """"Quadruple Polarization (HH/HV/VH/VV)"""

    CP = "CP"
    """"Compact Polarization (LH/LV or RH/RV): Not yet available"""


class SaocomProduct(SarProduct):
    """Class for SAOCOM-1 Products"""

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        See here
        <here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf>`_
        for more information (Beam Modes)

        .. WARNING::
            For SSC data:
                - We assume being in High Resolution (SE)
                - Incidence angle: we consider the worst option, around 20 degrees
        """
        # Find the polarization
        root, _ = self.read_mtd()

        # Open identifier
        polarization = SaocomPolarization.from_value(root.findtext(".//polMode"))
        if not polarization:
            raise InvalidProductError("polMode not found in metadata!")

        def_res = None
        # For complex data, set regular ground range resolution provided by the constructor
        if self.sensor_mode == SaocomSensorMode.SM:
            def_res = 10.0
        elif self.sensor_mode == SaocomSensorMode.TN:
            if polarization == SaocomPolarization.QP:
                def_res = 50.0
            else:
                def_res = 30.0
        elif self.sensor_mode == SaocomSensorMode.TW:
            if polarization == SaocomPolarization.QP:
                def_res = 100.0
            else:
                def_res = 50.0

        return def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        SAOCOM: https://earth.esa.int/eogateway/missions/saocom
        """
        self.instrument = "SAR L-band"

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*Data*-{!l}*"
        self._band_folder = self.path.joinpath("Data")

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self.snap_filename = f"{self.name}.xemt"

        # Post init done by the super class
        super()._post_init(**kwargs)

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
        root, _ = self.read_mtd()

        # Compute extent corners
        corners = [
            [float(vertex.findtext("lon")), float(vertex.findtext("lat"))]
            for vertex in root.iterfind(".//frame/vertex")
        ]
        # TODO: ensure that the polygon is valid ?

        return gpd.GeoDataFrame(
            geometry=[Polygon(corners)],
            crs=vectors.WGS84,
        )

        # # Open extent KML file
        # if self.product_type == SaocomProductType.SLC:
        #     pass
        #
        # else:
        #     try:
        #         extent_file = next(self.path.glob("**/Images/*.kml"))
        #     except IndexError as ex:
        #         raise InvalidProductError(
        #             f"Extent file (products.kml) not found in {self.path}"
        #         ) from ex
        #
        #     extent_wgs84 = vectors.read(extent_file).envelope
        #
        #     return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # WARNING: Sometimes the product seems to contain several tiles that are not contiguous
        # Do not simplify geometry then
        return rasters.get_valid_vector(
            self.get_default_band_path()
        )  # Processed by SNAP: the nodata is set

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the existing band paths (as they come with the archived products).

        Args:
            **kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        extended_fmt = _ExtendedFormatter()
        cuss_file = next(self.path.glob("*.zip"))
        band_paths = {}
        for band in SarBandNames.speckle_list():
            band_regex = extended_fmt.format(self._raw_band_regex, band.value)

            try:
                # Get as a list but keep only the first item (SLC with multiple swaths)
                raw_paths = files.get_archived_rio_path(
                    cuss_file, band_regex.replace("*", ".*"), as_list=True
                )

                # Remove .xml files and keep only the first item
                band_paths[band] = [
                    path for path in raw_paths if not path.endswith(".xml")
                ][0]
            except FileNotFoundError:
                continue

        return band_paths

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        prod_type = root.findtext(".//procLevel")
        if not prod_type:
            raise InvalidProductError("procLevel not found in metadata!")

        self.product_type = SaocomProductType.from_value(prod_type)

        if self.product_type in [
            SaocomProductType.DI,
            SaocomProductType.GEC,
            SaocomProductType.GTC,
        ]:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == SaocomProductType.SLC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )
        if self.product_type == SaocomProductType.DI:
            LOGGER.warning(
                "DI (Detected Image) product type has never been tested for %s data. "
                "Use it at your own risks !",
                self.constellation.value,
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from TerraSAR-X products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        imaging_mode = root.findtext(".//acqMode")
        if not imaging_mode:
            raise InvalidProductError("acqMode not found in metadata!")

        # Get sensor mode
        try:
            self.sensor_mode = getattr(SaocomSensorMode, imaging_mode)
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
            acq_date = root.findtext(".//acquisitionTime/startTime")
            if not acq_date:
                raise InvalidProductError(
                    "acquisitionTime/startTime not found in metadata!"
                )

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%f")
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
            name = files.get_filename(root.findtext(".//dataFile/componentPath"))
        except TypeError:
            raise InvalidProductError("dataFile/componentPath not found in metadata!")

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
        mtd_from_path = "xemt"

        return self._read_mtd_xml(mtd_from_path)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            try:
                quicklook_path = files.get_archived_rio_path(
                    next(self.path.glob(f"{self.name}.zip")), file_regex="Images/.*png"
                )
            except FileNotFoundError:
                quicklook_path = str(next(self.path.glob("Images/*.png")))
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
            od = OrbitDirection.from_value(root.findtext(".//OrbitDirection"))

        except TypeError:
            raise InvalidProductError("orbitDirection not found in metadata!")

        return od
