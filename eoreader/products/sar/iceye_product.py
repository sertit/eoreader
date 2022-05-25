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
ICEYE products.
Take a look
`here <https://www.iceye.com/hubfs/Downloadables/ICEYE-Level-1-Product-Specs-2019.pdf>`_.
"""
import logging
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
from cloudpathlib import CloudPath
from lxml import etree
from sertit import files, vectors
from sertit.misc import ListEnum

from eoreader import cache
from eoreader.bands import SarBandNames as sab
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.keywords import ICEYE_USE_SLC
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class IceyeProductType(ListEnum):
    """
    ICEYE products types.
    Take a look
    `here <https://www.iceye.com/hubfs/Downloadables/ICEYE-Level-1-Product-Specs-2019.pdf>`_.
    """

    GRD = "GRD"
    """ Level-1 Ground Range Detected (GRD) """

    SLC = "SLC"
    """ Level-1 Single Look Complex (SLC) """

    # Not released yet
    # ORTHO = "ORTHO"
    # """ ORTHO """


@unique
class IceyeSensorMode(ListEnum):
    """
    ICEYE imaging mode.
    Take a look
    `here <https://www.iceye.com/hubfs/Downloadables/ICEYE-Level-1-Product-Specs-2019.pdf>`_.
    """

    SM = "stripmap"
    """SM - Stripmap, StripmapWide, StripmapHI"""

    SL = "spotlight"
    """SL - Spotlight"""

    SC = "scan"
    """SC - ScanSAR"""


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
        self._use_slc = kwargs.pop(ICEYE_USE_SLC, None)

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        See here
        <here](https://www.iceye.com/hubfs/Downloadables/ICEYE_SAR_Product_Guide_2021_V4.0.pdf>`_
        for more information (table B.3).
        """
        if self.sensor_mode == IceyeSensorMode.SM:
            def_res = 3.0
        elif self.sensor_mode == IceyeSensorMode.SL:
            def_res = 1.0
        elif self.sensor_mode == IceyeSensorMode.SC:
            def_res = 15.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")
        return def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        ICEYE: https://earth.esa.int/eogateway/missions/iceye
        """
        self.instrument = "SAR X-band"

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._band_folder = self.path

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Its original filename is its name
        self._use_filename = True

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        # Private attributes
        if self._use_slc:
            self.snap_filename = str(next(self.path.glob("*ICEYE*SLC*.xml")).name)
            self._raw_band_regex = "*ICEYE*SLC*.h5"
        else:
            self.snap_filename = str(next(self.path.glob("*ICEYE*GRD*.xml")).name)
            self._raw_band_regex = "*ICEYE*GRD*.tif"

        # Post init done by the super class
        super()._post_init(**kwargs)

    @cache
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
        # Open extent KML file
        try:
            extent_file = next(self.path.glob("*ICEYE*QUICKLOOK*.kml"))
        except IndexError as ex:
            raise InvalidProductError(
                f"Extent file (*.kml) not found in {self.path}"
            ) from ex

        extent_wgs84 = vectors.read(extent_file).envelope

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Some ICEYE product metadata has a namespace some don't
        namespace = nsmap.get(None, "")

        # Open identifier
        prod_type = root.findtext(f".//{namespace}product_level")
        if not prod_type:
            raise InvalidProductError("mode not found in metadata!")

        self.product_type = IceyeProductType.from_value(prod_type)

        if self.product_type == IceyeProductType.GRD:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == IceyeProductType.SLC:
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
        root, nsmap = self.read_mtd()

        # Some ICEYE product metadata has a namespace some don't
        namespace = nsmap.get(None, "")

        # Open identifier
        imaging_mode = root.findtext(f".//{namespace}acquisition_mode")
        if not imaging_mode:
            raise InvalidProductError("imagingMode not found in metadata!")

        # Get sensor mode
        try:
            self.sensor_mode = IceyeSensorMode.from_value(imaging_mode)
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
        if self.datetime is None:
            # Get MTD XML file
            root, nsmap = self.read_mtd()

            # Some ICEYE product metadata has a namespace some don't
            namespace = nsmap.get(None, "")

            # Open identifier
            acq_date = root.findtext(f".//{namespace}acquisition_start_utc")
            if not acq_date:
                raise InvalidProductError(
                    "acquisition_start_utc not found in metadata!"
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
        root, nsmap = self.read_mtd()

        # Some ICEYE product metadata has a namespace some don't
        namespace = nsmap.get(None, "")

        # Open identifier
        name = root.findtext(f".//{namespace}product_name")
        if not name:
            raise InvalidProductError("product_name not found in metadata!")

        # Check if use_slc is compatible
        if self._use_slc and IceyeProductType.SLC.value not in name:
            raise InvalidProductError(f"This product {self.name} has no SLC image!")
        elif not self._use_slc and IceyeProductType.GRD.value not in name:
            raise InvalidProductError(f"This product {self.name} has no GRD image!")

        return name

    @cache
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

        def __read_mtd(prod_type: IceyeProductType):
            return self._read_mtd_xml(f"ICEYE*{prod_type.value}*.xml")

        if self._use_slc is None:
            try:
                root, nsmap = __read_mtd(IceyeProductType.GRD)
                self._use_slc = False
            except InvalidProductError:
                root, nsmap = __read_mtd(IceyeProductType.SLC)
                self._use_slc = True
        else:
            if self._use_slc:
                try:
                    root, nsmap = __read_mtd(IceyeProductType.SLC)
                except InvalidProductError:
                    LOGGER.warning("SLC image is not available for this product.")
                    self._use_slc = False
                    root, nsmap = __read_mtd(IceyeProductType.GRD)
            else:
                try:
                    root, nsmap = __read_mtd(IceyeProductType.GRD)
                except InvalidProductError:
                    LOGGER.warning("GRD image is not available for this product.")
                    self._use_slc = True
                    root, nsmap = __read_mtd(IceyeProductType.SLC)

        return root, nsmap

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the existing path of the VV band (as they come with the archived products).
        ICEYE product only contains a VV band !

        Args:
            **kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        band_paths = {}
        try:
            band_paths[sab.VV] = files.get_file_in_dir(
                self._band_folder, self._raw_band_regex, exact_name=True, get_list=False
            )
        except FileNotFoundError:
            raise InvalidProductError(
                "An ICEYE product should at least contain a VV band !"
            )

        return band_paths

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            quicklook_path = str(next(self.path.glob("*.png")))
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
            od = OrbitDirection.from_value(root.findtext(".//orbit_direction"))

        except TypeError:
            raise InvalidProductError("orbit_direction not found in metadata!")

        return od
