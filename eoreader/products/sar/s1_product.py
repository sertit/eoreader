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
"""Sentinel-1 products"""

import logging
import os
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
from lxml import etree
from sertit import path, vectors
from sertit.misc import ListEnum

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.exceptions import InvalidProductError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S1ProductType(ListEnum):
    """
    S1 products types. Take a look here:
    https://sentinel.esa.int/web/sentinel/missions/sentinel-1/data-products
    """

    RAW = "RAW"
    """Raw products (lvl 0): **not used by EOReader**"""

    SLC = "SLC"
    """Single Look Complex (SLC, lvl 1)"""

    GRD = "GRD"
    """Ground Range Detected (GRD, lvl 1, phase lost)"""

    OCN = "OCN"
    """Ocean products (lvl 2): **not used by EOReader**"""


@unique
class S1SensorMode(ListEnum):
    """
    S1 sensor mode. Take a look here:
    https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes

    The primary conflict-free modes are IW, with VV+VH polarisation over land,
    and WV, with VV polarisation, over open ocean.
    EW mode is primarily used for wide area coastal monitoring including ship traffic, oil spill and sea-ice monitoring.
    SM mode is only used for small islands and on request for extraordinary events such as emergency management.
    """

    SM = "SM"
    """Stripmap (SM)"""

    IW = "IW"
    """Interferometric Wide swath (IW)"""

    EW = "EW"
    """Extra-Wide swath (EW)"""

    WV = "WV"
    """Wave (WV) -> single polarisation only (HH or VV)"""


@unique
class S1ResolutionClass(ListEnum):
    """
    S1 resolution class:
    https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/resolutions/level-1-ground-range-detected
    """

    FR = "F"
    """Full Resolution (FR)"""

    HR = "H"
    """High Resolution (HR)"""

    MR = "M"
    """Medium Resolution (MR)"""

    NONE = "_"
    """No specified resolution for other product type than GRD"""


class S1Product(SarProduct):
    """
    Class for Sentinel-1 Products

    You can use directly the .zip file
    """

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        See here
        `here <https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/resolutions/level-1-ground-range-detected>`_
        for more information
        """

        if self.product_type == S1ProductType.GRD:
            res_class = S1ResolutionClass.from_value(self.split_name[2][-1])
        else:
            res_class = S1ResolutionClass.NONE

        # Using the az resolution between rg and az
        default_res = {
            S1SensorMode.SM: {
                S1ResolutionClass.NONE: 9.0,
                S1ResolutionClass.FR: 9.0,
                S1ResolutionClass.HR: 23.0,
                S1ResolutionClass.MR: 84.0,
            },
            S1SensorMode.IW: {
                S1ResolutionClass.NONE: 20.0,
                S1ResolutionClass.HR: 20.0,
                S1ResolutionClass.MR: 87.0,
            },
            S1SensorMode.EW: {
                S1ResolutionClass.NONE: 50.0,
                S1ResolutionClass.HR: 50.0,
                S1ResolutionClass.MR: 87.0,
            },
            S1SensorMode.WV: {
                S1ResolutionClass.NONE: 51.0,
                S1ResolutionClass.MR: 51.0,
            },
        }

        # Pixel sizes are squared -> no issue between rg and az
        default_pix_size = {
            S1SensorMode.SM: {
                S1ResolutionClass.NONE: 3.5,
                S1ResolutionClass.FR: 3.5,
                S1ResolutionClass.HR: 10.0,
                S1ResolutionClass.MR: 40.0,
            },
            S1SensorMode.IW: {
                S1ResolutionClass.NONE: 20.0,
                S1ResolutionClass.HR: 20.0,
                S1ResolutionClass.MR: 40.0,
            },
            S1SensorMode.EW: {
                S1ResolutionClass.NONE: 25.0,
                S1ResolutionClass.HR: 25.0,
                S1ResolutionClass.MR: 40.0,
            },
            S1SensorMode.WV: {
                S1ResolutionClass.NONE: 25.0,
                S1ResolutionClass.MR: 25.0,
            },
        }

        try:
            def_pixel_size = default_pix_size[self.sensor_mode][res_class]
            def_res = default_res[self.sensor_mode][res_class]
        except KeyError as exc:
            raise InvalidProductError(
                f"Unknown sensor mode: {self.sensor_mode}"
            ) from exc

        self.pixel_size = def_pixel_size
        self.resolution = def_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        Sentinel-1: https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1/instrument-payload
        """
        self.instrument = "SAR C-band"

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*-{!l}-*.tiff"  # Just get the SLC-iw1 image for now
        self._band_folder = self.path.joinpath("measurement")
        self.snap_filename = ""

        # Its original filename is its name
        self._use_filename = True

        # Zipped and SNAP can process its archive
        self.needs_extraction = False

        # Pre init done by the super class
        super()._pre_init(**kwargs)

        # Check if COG in name (S1 needs always SNAP)
        if "_COG" in self.filename and not self._has_snap_10_or_higher():
            raise NotImplementedError(
                "S1 COG products are only handled by SNAP 10.0 or higher. "
                "Please upgrade your software to process this product."
            )

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
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                   Name  ...                                           geometry
            0  Sentinel-1 Image Overlay  ...  POLYGON ((0.85336 42.24660, -2.32032 42.65493,...
            [1 rows x 12 columns]

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        try:
            # Open the map-overlay file
            if self.is_archived:
                extent_wgs84 = self._read_archived_vector(
                    archive_regex=".*preview.*map-overlay.kml"
                )
            else:
                preview_overlay = self.path.joinpath("preview", "map-overlay.kml")

                if os.path.isfile(preview_overlay):
                    # Open the KML file
                    extent_wgs84 = vectors.read(preview_overlay)
                else:
                    # raise to be caught by fallback
                    raise InvalidProductError

        except Exception:
            # Sometimes, map-overlay.kml of S1 products cannot be read properly
            extent_wgs84 = self._fallback_wgs84_extent("preview/map-overlay.kml")

        return extent_wgs84

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        prod_type = root.findtext(".//productType")
        if not prod_type:
            raise InvalidProductError("mode not found in metadata!")

        self.product_type = S1ProductType.from_value(prod_type)

        if self.product_type == S1ProductType.GRD:
            self.sar_prod_type = SarProductType.GRD
        elif self.product_type == S1ProductType.SLC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from S1 products name (could check the metadata too)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        mode = root.findtext(".//mode")
        if not mode:
            raise InvalidProductError("mode not found in metadata!")

        # Mono swath SM
        if mode in ["S1", "S2", "S3", "S4", "S5", "S6"]:
            mode = "SM"

        # Get sensor mode
        self.sensor_mode = S1SensorMode.from_value(mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.constellation.value} name: {self.name}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 12, 15, 6, 9, 6)
            >>> prod.get_datetime(as_datetime=False)
            '20191215T060906'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//startTime")
            if not acq_date:
                raise InvalidProductError("startTime not found in metadata!")

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
        try:
            if self.is_archived:
                pdf_file = self._get_archived_path(r".*\.pdf", as_list=False)
            else:
                pdf_file = next(self.path.glob("*.pdf"))
        except (FileNotFoundError, StopIteration):
            # The name is not in the classic metadata, but can be found in the product-preview
            try:
                mtd_from_path = "preview/product-preview.html"
                mtd_archived = r"preview.*product-preview\.html"

                root = self._read_mtd_html(mtd_from_path, mtd_archived)

                # Open identifier
                name = root.findtext(".//head/title")
                if not name:
                    raise InvalidProductError("title not found in metadata!")

                LOGGER.warning(
                    "Product filename is not a valid Sentinel-1 name, and the retrieved name is missing the unique ID."
                )

            except InvalidProductError as exc:
                raise InvalidProductError(
                    "product-preview.html not found in the product, the name will be the filename (which is not a valid Sentinel-1 name)"
                ) from exc
        else:
            name = path.get_filename(pdf_file)
            if ".SAFE" in name:
                name = name.split(".SAFE")[0]

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element product at 0x1832895d788>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = "annotation/*.xml"

        # When archived, other XML (in calibration folder) can be found
        mtd_archived = r"annotation/(?!rfi)(?!cal)(?!noise).*\.xml"

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
                quicklook_path = self.path / self._get_archived_path(
                    regex=r".*preview.quick-look\.png"
                )
            else:
                quicklook_path = next(self.path.glob("preview/quick-look.png"))
            quicklook_path = str(quicklook_path)
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
        root, _ = self.read_mtd()

        # Get the orbit direction
        try:
            od = OrbitDirection.from_value(root.findtext(".//pass").upper())

        except TypeError as exc:
            raise InvalidProductError("pass not found in metadata!") from exc

        return od
