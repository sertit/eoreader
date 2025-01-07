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
RADARSAT-Constellation Mission products.
More info `here <https://www.asc-csa.gc.ca/eng/satellites/radarsat/technical-features/characteristics.asp>`_.
"""

import difflib
import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
from lxml import etree
from sertit import vectors
from sertit.misc import ListEnum
from sertit.vectors import WGS84

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class RcmProductType(ListEnum):
    """
    RADARSAT-Constellation projection identifier.
    Take a look `here <https://catalyst.earth/catalyst-system-files/enterprise-aerial-help/references/gdb_r/RADARSAT_Constellation.html>`_.
    """

    SLC = "SLC"
    """
    SLC represents a SLant range, georeferenced Complex product.
    It is equivalent to a single-look complex product for RADARSAT-1 or RADARSAT-2).
    """

    GRC = "GRC"
    """
    GRC represents GRound range, georeferenced, Complex products.
    """

    GRD = "GRD"
    """
    GRD represents GRound range, georeferenced, Detected.
    GRD is equivalent to an SGX, SCN, or SCW product for RADARSAT-1 or RADARSAT-2.
    """

    GCC = "GCC"
    """
    GCC represents GeoCoded Complex products.
    """

    GCD = "GCD"
    """
    GCD represents GeoCoded Detected products.
    GCD is equivalent to an SSG or SPG product for RADARSAT-1 or RADARSAT-2.
    """

    MLC = "MLC"
    """
    MLC represent Multi-Look slant range Complex products.
    It is for dual Co-/Cross-Polarization1 or Compact Polarization which is a spatially averaged version of the SLC product condensed to a single multi-burst image of the covariance matrix elements.
    The covariance matrix elements consist of two real diagonal elements |xH|2 and |xV|2, and a complex off-diagonal element xH*conj(xV) where x is either Circular,
    H or V depending on the SLC product polarization setting and conj denotes the complex conjugate.
    """


@unique
class RcmSensorMode(ListEnum):
    """
    RADARSAT-Constellation sensor mode.
    Take a look `here <https://www.asc-csa.gc.ca/eng/satellites/radarsat/technical-features/characteristics.asp>`_.

    .. WARNING:: The name in the metadata may vary !
    """

    THREE_M = "Very High Resolution 3m"
    """" Very-High Resolution, 3 meters [3M] """

    FIVE_M = "High Resolution 5m"
    """" High Resolution, 5 meters [5M] """

    QP = "Quad-Polarization"
    """" Quad-Polarization [QP] """

    SIXTEEN_M = "Medium Resolution 16m"
    """" Medium Resolution, 16 meters [16M] """

    THIRTY_M = "Medium Resolution 30m"
    """" Medium Resolution, 30 meters [SC30] """

    FIFTY_M = "Medium Resolution 50m"
    """" Medium Resolution, 50 meters [SC50] """

    SCLN = "Low Noise"
    """" Low Noise [SCLN] """

    HUNDRED_M = "Low Resolution 100m"
    """ Low Resolution, 100 meters [SC100] """

    SD = "Ship Detection"
    """ Ship Detection Mode """

    FSL = "Spotlight Mode"
    """ Spotlight Mode [FSL] """


class RcmProduct(SarProduct):
    """
    Class for RADARSAT-Constellation Products

    You can use directly the .zip file
    """

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        See here
        `here <https://ftp.maps.canada.ca/pub/csa_asc/Space-technology_Technologie-spatiale/radarsat_constellation_mission_plan/RCM-SP-52-9092_Product_Spec_1-15_Public.pdf>`_
        for more information (Table 4-1 Raw and Image Product Description Table - Contents and Volumes, page 18)
        """
        if self.sensor_mode == RcmSensorMode.THREE_M:
            def_pixel_size = 1.25
            def_res = 3.0
        elif self.sensor_mode == RcmSensorMode.FIVE_M:
            def_pixel_size = 2.0
            def_res = 5.0
        elif self.sensor_mode == RcmSensorMode.QP:
            def_pixel_size = 2.5
            def_res = 9.0
        elif self.sensor_mode == RcmSensorMode.SIXTEEN_M:
            def_pixel_size = 6.25
            def_res = 16.0
        elif self.sensor_mode == RcmSensorMode.THIRTY_M:
            def_pixel_size = 12.5
            def_res = 30.0
        elif self.sensor_mode == RcmSensorMode.FIFTY_M:
            def_pixel_size = 20.0
            def_res = 50.0
        elif self.sensor_mode in [RcmSensorMode.HUNDRED_M, RcmSensorMode.SCLN]:
            def_pixel_size = 40.0
            def_res = 100.0
        elif self.sensor_mode == RcmSensorMode.FSL:
            def_pixel_size = 0.33
            def_res = 1.0  # 3.0*1.0
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")

        self.pixel_size = def_pixel_size
        self.resolution = def_res

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # SNAP cannot process zipped RCM
        self.needs_extraction = True

        # Its original filename is its name
        self._use_filename = True

        # Private attributes
        self._raw_band_regex = "*_{}.tif"
        self._band_folder = self.path / "imagery"
        self.snap_filename = ""

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    @cache
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent
                                                        geometry
            1  POLYGON ((106.57999 -6.47363, 107.06926 -6.473...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open extent KML file
        try:
            extent_file = next(self.path.joinpath("preview").glob("*mapOverlay.kml"))
            product_kml = vectors.read(extent_file)

            extent_wgs84 = product_kml[product_kml.Name == "Polygon Outline"].envelope

        except (IndexError, StopIteration):
            # Some RCM products don't have any mapOverlay.kml file as it is not a mandatory file!
            extent_wgs84 = self._fallback_wgs84_extent("preview/mapOverlay.kml")

        # Reproject to be sure
        extent_wgs84 = extent_wgs84.to_crs(WGS84)

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_instrument(self) -> None:
        """
        Set instrument

        RCM: https://earth.esa.int/web/eoportal/satellite-missions/r/rcm
        """
        self.instrument = "SAR C-band"

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, nsmap = self.read_mtd()
        namespace = nsmap.get(None, "")

        # Open identifier
        prod_type = root.findtext(f".//{namespace}productType")
        if not prod_type:
            raise InvalidProductError("productType not found in metadata!")

        self.product_type = RcmProductType.from_value(prod_type)

        if self.product_type in [RcmProductType.GRD, RcmProductType.GRC]:
            self.sar_prod_type = SarProductType.GRD
        elif self.product_type in [RcmProductType.GCD, RcmProductType.GCC]:
            self.sar_prod_type = SarProductType.GEOCODED
        elif self.product_type in [RcmProductType.SLC, RcmProductType.MLC]:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )

        if self.product_type != RcmProductType.GRD:
            LOGGER.warning(
                "Other products type than GRD has not been tested for %s data. "
                "Use it at your own risks !",
                self.constellation.value,
            )

    def _set_sensor_mode(self) -> None:
        """
        Get products type from RADARSAT-2 products name (could check the metadata too)
        """
        # Get metadata
        root, nsmap = self.read_mtd()
        namespace = nsmap.get(None, "")

        # Get sensor mode
        # WARNING: this word may differ from the Enum !!! (no docs available)
        # Get the closest match
        sensor_mode_xml = root.findtext(f".//{namespace}acquisitionType")

        if sensor_mode_xml:
            sensor_mode = difflib.get_close_matches(
                sensor_mode_xml, RcmSensorMode.list_values()
            )[0]
            try:
                self.sensor_mode = RcmSensorMode.from_value(sensor_mode)
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
        # Get MTD XML file
        root, nsmap = self.read_mtd()
        namespace = nsmap.get(None, "")

        # Open identifier
        acq_date = root.findtext(f".//{namespace}rawDataStartTime")
        if not acq_date:
            raise InvalidProductError("rawDataStartTime not found in metadata!")

        # Convert to datetime
        date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # The name is not in the classic metadata, but can be found in the manifest
        try:
            mtd_from_path = "preview/productPreview.html"
            mtd_archived = r"preview.*productPreview\.html"

            root = self._read_mtd_html(mtd_from_path, mtd_archived)

            # Open identifier
            name = root.findtext(".//header/h2")
            if not name:
                raise InvalidProductError("header/h2 not found in metadata!")

        except InvalidProductError:
            LOGGER.warning(
                "productPreview.html not found in the product, the name will be the filename"
            )
            name = self.filename

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
        mtd_from_path = "metadata/product.xml"
        mtd_archived = r"metadata.*product\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_{constellation}_{polarization}_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed RCM name
        """
        # Get back the correct sensor mode name
        if self.sensor_mode == RcmSensorMode.THREE_M:
            mode_name = "3M"
        elif self.sensor_mode == RcmSensorMode.FIVE_M:
            mode_name = "5M"
        elif self.sensor_mode == RcmSensorMode.SIXTEEN_M:
            mode_name = "16M"
        elif self.sensor_mode == RcmSensorMode.THIRTY_M:
            mode_name = "SC30"
        elif self.sensor_mode == RcmSensorMode.FIFTY_M:
            mode_name = "SC50"
        elif self.sensor_mode == RcmSensorMode.HUNDRED_M:
            mode_name = "SC100"
        else:
            mode_name = self.sensor_mode.name

        pol_chan = [pol.value for pol in self.pol_channels]
        return f"{self.get_datetime()}_{self.constellation.name}_{'_'.join(pol_chan)}_{mode_name}_{self.product_type.value}"

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            quicklook_path = str(next(self.path.glob("preview/productOverview.png")))
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
        root, nsmap = self.read_mtd()
        namespace = nsmap.get(None, "")

        # Get the orbit direction
        try:
            od = OrbitDirection.from_value(
                root.findtext(f".//{namespace}passDirection").upper()
            )

        except TypeError as exc:
            raise InvalidProductError("passDirection not found in metadata!") from exc

        return od
