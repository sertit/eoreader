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
"""
S1 ASF RTC products.
Take a look
`here <https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/#readme-file>`_.
"""

import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
from lxml import etree
from rasterio import crs
from sertit import path, vectors
from sertit.misc import ListEnum
from shapely import box

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.exceptions import InvalidProductError
from eoreader.products import S1SensorMode, SarProduct
from eoreader.products.product import OrbitDirection
from eoreader.reader import Constellation
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S1RtcProductType(ListEnum):
    """
    S1 RTC products type: RTC
    """

    RTC = "RTC"
    """
    RTC product type.
    https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide
    """


class S1RtcAsfProduct(SarProduct):
    """
    Class for S1 RTC from Asf
    Take a look
    `here <https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/#readme-file>`_.
    """

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        try:
            pixel_size = float(self.split_name[4][-2:])
        except ValueError as exc:
            raise InvalidProductError("Incorrect name format!") from exc

        default_res = {
            S1SensorMode.SM: 9.0,
            S1SensorMode.IW: 20.0,
            S1SensorMode.EW: 50.0,
            S1SensorMode.WV: 51.0,
        }

        self.pixel_size = pixel_size
        self.resolution = default_res[self.sensor_mode]

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
        self._band_folder = self.path

        # Already ORTHO, so OK
        self.needs_extraction = False

        # Its original filename is its name
        self._use_filename = True

        # Private attributes
        self._raw_band_regex = "*_{}.tif"

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation: force S1."""
        return Constellation.S1

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                                        geometry
            0  POLYGON ((309780.000 4390200.000, 309780.000 4...

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        footprint = self.footprint()
        return gpd.GeoDataFrame(
            geometry=[box(*footprint.total_bounds)], crs=footprint.crs
        )

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
        # Footprint is always in UTM
        # https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/#image-files
        # Products are distributed as GeoTIFFs (one for each available polarization) projected to the appropriate UTM Zone for the location of the scene.
        if self.is_archived:
            footprint = self._read_archived_vector(archive_regex=r".*\.shp")
        else:
            try:
                footprint = vectors.read(next(self.path.glob("*.shp")))
            except StopIteration as exc:
                raise FileNotFoundError(
                    f"Non existing file *.shp in {self.path}"
                ) from exc

        return footprint

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
        # Products are always in UTM
        # https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/#image-files
        # Products are distributed as GeoTIFFs (one for each available polarization) projected to the appropriate UTM Zone for the location of the scene.

        # Estimate UTM from extent
        return self.footprint().crs

    def _set_product_type(self) -> None:
        """Set products type"""
        self.product_type = S1RtcProductType.RTC

    def _set_sensor_mode(self) -> None:
        """Get sensor mode"""
        mode = self.split_name[1]
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
            # Sentinel-2 datetime (in the filename) is the datatake sensing time, not the granule sensing time !
            sensing_time = self.split_name[2]

            # Convert to datetime
            date = datetime.strptime(sensing_time, "%Y%m%dT%H%M%S")
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
        name = path.get_filename(self.get_quicklook_path())
        if "rgb" in name:
            name = name.replace("_rgb", "")

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
        # No MTD!
        return None, {}

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
                    regex=r".*_rgb\.png"
                )
            else:
                quicklook_path = next(self.path.glob("*_rgb.png"))
        except (StopIteration, FileNotFoundError):
            try:
                if self.is_archived:
                    quicklook_path = self.path / self._get_archived_path(
                        regex=r".*\.png"
                    )
                else:
                    quicklook_path = next(self.path.glob("*.png"))
            except (StopIteration, FileNotFoundError):
                pass

        return str(quicklook_path)

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
        return OrbitDirection.UNKNOWN
