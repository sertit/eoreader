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
COSMO-SkyMed 2nd Generation products.
More info `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
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
from sertit.rasters import XDS_TYPE
from shapely.geometry import Polygon, box

from eoreader import cache, cached_property
from eoreader.bands.bands import BandNames
from eoreader.exceptions import InvalidProductError
from eoreader.products.sar.sar_product import SarProduct, SarProductType
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class CsgProductType(ListEnum):
    """
    COSMO-SkyMed 2nd Generation products types.

    The product classed are not specified here.

    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    RAW = "RAW"
    """Level 0"""

    SCS = "SCS"
    """Level 1A, Single-look Complex Slant"""

    DGM = "DGM"
    """Level 1B, Detected Ground Multi-look"""

    GEC = "GEC"
    """Level 1C, Geocoded Ellipsoid Corrected"""

    GTC = "GTC"
    """Level 1D, Geocoded Terrain Corrected"""


@unique
class CsgSensorMode(ListEnum):
    """
    COSMO-SkyMed 2nd Generation sensor mode.
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    S1A = "SPOTLIGHT-1A"
    """SPOTLIGHT-1A"""

    S1B = "SPOTLIGHT-1B"
    """SPOTLIGHT-1B"""

    S2A = "SPOTLIGHT-2A"
    """SPOTLIGHT-2A (standard and apodized). Resolution: 0.25m"""

    S2B = "SPOTLIGHT-2B"
    """SPOTLIGHT-2B (standard and apodized). Resolution: 0.45m"""

    S2C = "SPOTLIGHT-2C"
    """SPOTLIGHT-2C (standard and apodized). Resolution: 0.56m"""

    S1_MSOR = "SPOTLIGHT-1-MSOR"
    """SPOTLIGHT-1-MSOR"""

    S2_MSOS = "SPOTLIGHT-2-MSOS"
    """SPOTLIGHT-2-MSOS"""

    S2_MSJN = "SPOTLIGHT-2-MSJN"
    """SPOTLIGHT-2-MSJN"""

    S1_OQR = "SPOTLIGHT-1-OQR"
    """SPOTLIGHT-1-OQR"""

    S2_OQS = "SPOTLIGHT-2-OQS"
    """SPOTLIGHT-2-OQS"""

    S1_EQR = "SPOTLIGHT-1-EQR"
    """SPOTLIGHT-1-EQR"""

    S2_EQS = "SPOTLIGHT-2-EQS"
    """SPOTLIGHT-2-EQS"""

    SM = "STRIPMAP"
    """SPOTLIGHT-2C (standard and apodized). Resolution: Natural"""

    PP = "PINGPONG"
    """PingPong. Resolution: 8.0m"""

    QP = "QUADPOL"
    """QuadPol. Resolution: Natural"""

    SC1 = "SCANSAR-1"
    """ScanSar-1. Resolution: 14.0m"""

    SC2 = "SCANSAR-2"
    """ScanSar-2. Resolution: 27.0m"""

    NA = "N/A"
    """N/A"""


@unique
class CsgPolarization(ListEnum):
    """
    COSMO-SkyMed 2nd Generation polarizations used during the acquisition.
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    HH = "HH"
    """Horizontal Tx/Horizontal Rx for Himage, ScanSAR and Spotlight modes"""

    VV = "VV"
    """Vertical Tx/Vertical Rx for Himage, ScanSAR and Spotlight modes"""

    HV = "HV"
    """Horizontal Tx/Vertical Rx for Himage, ScanSAR"""

    VH = "VH"
    """Vertical Tx/Horizontal Rx for Himage, ScanSAR"""


class CsgProduct(SarProduct):
    """
    Class for COSMO-SkyMed 2nd Generation Products
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
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
        # Read metadata for default resolution
        try:
            root, _ = self.read_mtd()
            def_res = float(root.findtext(".//GroundRangeGeometricResolution"))
        except (InvalidProductError, TypeError):
            raise InvalidProductError(
                "GroundRangeGeometricResolution not found in metadata!"
            )
        except ValueError:
            if self.product_type == CsgProductType.SCS:
                if self.sensor_mode == CsgSensorMode.S2A:
                    def_res = 0.25
                elif self.sensor_mode == CsgSensorMode.S2B:
                    def_res = 0.45
                elif self.sensor_mode == CsgSensorMode.S2C:
                    def_res = 0.56
                elif self.sensor_mode == CsgSensorMode.PP:
                    def_res = 8.0
                elif self.sensor_mode == CsgSensorMode.SC1:
                    def_res = 14.0
                elif self.sensor_mode == CsgSensorMode.SC2:
                    def_res = 27.0
                else:
                    # Complex data has an empty field and its resolution is not known (STRIPMAP and QUADPOL)
                    def_res = -1.0
            else:
                raise InvalidProductError(
                    "GroundRangeGeometricResolution empty in metadata!"
                )

        return def_res

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*_{}_*.h5"
        self._band_folder = self.path
        self._snap_path = self._img_path.name

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Post init done by the super class
        super()._pre_init()

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """

        # Post init done by the super class
        super()._post_init()

    @cached_property
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1011117-766193"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent
                                                        geometry
            0  POLYGON ((108.09797 15.61011, 108.48224 15.678...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:

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
        except ValueError:

            def from_str_to_arr(geo_coord: str):
                str_list = [
                    it
                    for it in strings.str_to_list(geo_coord, additional_separator="\n")
                    if "+" not in it
                ]

                # Create tuples of 2D coords
                coord_list = []
                coord = np.zeros((2, 1), dtype=float)
                for it_id, it in enumerate(str_list):
                    if it_id % 3 == 0:
                        # Invert lat and lon
                        coord[1] = float(it)
                    elif it_id % 3 == 1:
                        # Invert lat and lon
                        coord[0] = float(it)
                    elif it_id % 3 == 2:
                        # Z coordinates: do not store it

                        # Append the last coordinates
                        coord_list.append(coord.copy())

                        # And reinit it
                        coord = np.zeros((2, 1), dtype=float)

                return coord_list

            bl_corners = from_str_to_arr(root.findtext(".//GeoCoordBottomLeft"))
            br_corners = from_str_to_arr(root.findtext(".//GeoCoordBottomRight"))
            tl_corners = from_str_to_arr(root.findtext(".//GeoCoordTopLeft"))
            tr_corners = from_str_to_arr(root.findtext(".//GeoCoordTopRight"))

            if not bl_corners:
                raise InvalidProductError("Invalid XML: missing extent.")

            assert (
                len(bl_corners) == len(br_corners) == len(tl_corners) == len(tr_corners)
            )

            polygons = [
                Polygon(
                    [
                        tl_corners[coord_id],
                        tr_corners[coord_id],
                        br_corners[coord_id],
                        bl_corners[coord_id],
                    ]
                )
                for coord_id in range(len(bl_corners))
            ]
            extents_wgs84 = gpd.GeoDataFrame(
                geometry=polygons,
                crs=vectors.WGS84,
            )

            extent_wgs84 = gpd.GeoDataFrame(
                geometry=[box(*extents_wgs84.total_bounds)],
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
            raise InvalidProductError("mode not found in metadata!")

        self.product_type = CsgProductType.from_value(prod_type)

        if self.product_type == CsgProductType.DGM:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == CsgProductType.SCS:
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
            raise InvalidProductError("AcquisitionMode not found in metadata!")

        # Get sensor mode
        self.sensor_mode = CsgSensorMode.from_value(acq_mode)

        if not self.sensor_mode:
            raise InvalidProductError(
                f"Invalid {self.platform.value} name: {self.name}"
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
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            try:
                acq_date = root.findtext(".//SceneSensingStartUTC")
            except TypeError:
                raise InvalidProductError("SceneSensingStartUTC not found in metadata!")

            # Convert to datetime
            # 2020-10-28 22:46:24.808662850
            # To many milliseconds (strptime accepts max 6 digits) -> needs to be cropped
            date = datetime.strptime(acq_date[:-3], "%Y-%m-%d %H:%M:%S.%f")
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
                name = files.get_filename(root.findtext(".//ProductName"))
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
            >>> path = r"1001513-735093"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element DeliveryNote at 0x2454ad4ee88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = "DFDN_*.h5.xml"

        return self._read_mtd_xml(mtd_from_path)

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            CSG SCS Products do not have a default resolution

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            XDS_TYPE: Band xarray

        """
        # In case of SCS data that doesn't have any resolution in the mtd
        if self.resolution < 0.0:
            with rasterio.open(path) as ds:
                self.resolution = ds.res[0]

        try:
            if resolution < 0.0:
                resolution = self.resolution
        except TypeError:
            pass

        return super()._read_band(
            path=path, band=band, resolution=resolution, size=size, **kwargs
        )
