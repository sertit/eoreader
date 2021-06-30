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
""" Sentinel-1 products """
import logging
import os
import re
import tempfile
import warnings
import zipfile
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

LOGGER = logging.getLogger(EOREADER_NAME)

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class S1ProductType(ListEnum):
    """
    S1 products types. Take a look here:
    https://earth.esa.int/web/sentinel/missions/sentinel-1/data-products
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
    https://earth.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes

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


class S1Product(SarProduct):
    """
    Class for Sentinel-1 Products

    You can use directly the .zip file
    """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)

        .. WARNING:: We assume being in High Resolution (except for WV where we must be in medium resolution)
        """
        def_res = None

        # Read metadata
        try:
            root, _ = self.read_mtd()
            def_res = float(root.findtext(".//rangePixelSpacing"))
        except (InvalidProductError, TypeError):
            pass

        # If we cannot read it in MTD, initiate survival mode
        if not def_res:
            if self.sensor_mode in [S1SensorMode.SM, S1SensorMode.IW]:
                def_res = 10.0
            elif self.sensor_mode in [S1SensorMode.EW, S1SensorMode.WV]:
                def_res = 25.0
            else:
                raise InvalidTypeError(f"Unknown sensor mode {self.sensor_mode}")

            LOGGER.debug(
                f"Default resolution is set to {def_res}. "
                f"The product is considered being in "
                f"{'Medium' if self.sensor_mode == S1SensorMode.WV else 'High'}-Resolution"
            )

        return def_res

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        # Private attributes
        self._raw_band_regex = "*-{!l}-*.tiff"  # Just get the SLC-iw1 image for now

        self._band_folder = self.path.joinpath("measurement")
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
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                   Name  ...                                           geometry
            0  Sentinel-1 Image Overlay  ...  POLYGON ((0.85336 42.24660, -2.32032 42.65493,...
            [1 rows x 12 columns]

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        tmp_dir = tempfile.TemporaryDirectory()

        try:
            # Open the map-overlay file
            if self.is_archived:
                # We need to extract the file here as we need a proper file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    filenames = [f.filename for f in zip_ds.filelist]
                    regex = re.compile(".*preview.*map-overlay.kml")
                    preview_overlay = zip_ds.extract(
                        list(filter(regex.match, filenames))[0], tmp_dir.name
                    )
            else:
                preview_overlay = self.path.joinpath("preview", "map-overlay.kml")

            if os.path.isfile(preview_overlay):
                # Open the KML file
                extent_wgs84 = vectors.read(preview_overlay)
                if extent_wgs84.empty:
                    raise InvalidProductError(
                        f"Cannot determine the WGS84 extent of {self.name}"
                    )
            else:
                raise InvalidProductError(
                    f"Impossible to find the map-overlay.kml in {self.path}"
                )

        except Exception as ex:
            raise InvalidProductError(ex) from ex

        finally:
            tmp_dir.cleanup()

        return extent_wgs84

    def _set_product_type(self) -> None:
        """Set products type"""
        self._get_sar_product_type(
            prod_type_pos=2, gdrg_types=S1ProductType.GRD, cplx_types=S1ProductType.SLC
        )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from S1 products name (could check the metadata too)
        """
        sensor_mode_name = self.split_name[1]

        # Get sensor mode
        for sens_mode in S1SensorMode:
            if sens_mode.value in sensor_mode_name:
                self.sensor_mode = sens_mode

        # Discard invalid sensor mode
        if self.sensor_mode != S1SensorMode.IW:
            raise NotImplementedError(
                f"For now, only IW sensor mode is used in EOReader processes: {self.name}"
            )
        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.platform.value} name: {self.name}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

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
        date = self.split_name[4]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def read_mtd(self) -> (etree._Element, dict):
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
        mtd_archived = "annotation.*\.xml"

        return self._read_mtd(mtd_from_path, mtd_archived)
