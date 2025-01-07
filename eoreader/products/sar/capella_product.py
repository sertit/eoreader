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
Capella products.
Take a look
`here <https://support.capellaspace.com/hc/en-us/categories/360002612692-SAR-Imagery-Products>`_.
"""

import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
from affine import Affine
from dicttoxml import dicttoxml
from lxml import etree
from rasterio import CRS, transform
from sertit import files, path, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType
from sertit.vectors import WGS84
from shapely.geometry import Point, box

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import SarBandNames as sab
from eoreader.exceptions import InvalidProductError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CapellaProductType(ListEnum):
    """
    Capella products types.
    Take a look
    `here <https://support.capellaspace.com/hc/en-us/articles/360039702691-SAR-Data-Formats>`_.
    """

    SLC = "SLC"
    """
    Single Look Complex (SLC)

    - Contains both amplitude and phase of the radar signal
    - Range-compressed and focused SAR image in slant-range geometry
    - Georeferenced using orbit data and Range-Doppler projected
    """

    GEC = "GEC"
    """
    Geocoded Ellipsoid Corrected (GEC)

    - Contains amplitude information only
    - Range-compressed, detected, focused and multi-looked SAR image
    - Multi-look techniques applied to enhance radiometric resolution
    - Resampled and projected onto WGS84 ellipsoid with average scene center height
    - Universal Transverse Mercator (UTM) and Universal Polar Stereographic (UPS) projections
    """

    GEO = "GEO"
    """
    Geocoded Terrain Corrected (GEO)

    - Contains amplitude information only
    - Range-compressed, detected, focused and multi-looked SAR image
    - Multi-look techniques applied to enhance radiometric resolution
    - Terrain-height corrected using a high-resolution Digital Elevation Model (DEM)
    - Universal Transverse Mercator (UTM) and Universal Polar Stereographic (UPS) projections
    """

    SICD = "SICD"
    """
    Sensor Independent Complex Data (SICD)

    - Contains both amplitude and phase of the radar signal
    - Range-compressed and focused SAR image in slant-range geometry
    - Sensor independent format

    Not used by EOReader.
    """

    SIDD = "SIDD"
    """
    Sensor Independent Derived Data (SIDD)

    - Contains amplitude information only
    - Range-compressed, detected, focused and multi-looked SAR image
    - Multi-look techniques applied to enhance radiometric resolution
    - Planar Gridded Display (PGD) projection
    - Sensor independent format

    Not used by EOReader.
    """

    CPHD = "CPHD"
    """
    Compensated Phase History Data (CPHD)

    - Contains raw phase history data that is compensated for hardware timing & platform motion
    - Sensor independent format
    - Only available to United States Government customers

    Not used by EOReader.
    """


@unique
class CapellaSensorMode(ListEnum):
    """
    Capella imaging mode.
    Take a look
    `here <https://support.capellaspace.com/hc/en-us/articles/360059224291-What-SAR-imagery-products-are-available-with-Capella->`_.
    """

    SM = "stripmap"
    """Stripmap"""

    SP = "spotlight"
    """Spotlight"""

    SS = "sliding_spotlight"
    """Sliding Spotlight"""


class CapellaProduct(SarProduct):
    """
    Class for Capella Products
    Take a look
    `here <https://support.capellaspace.com/hc/en-us/categories/360002612692-SAR-Imagery-Products>`_.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._has_stac_mtd = False

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        See here
        `here <https://support.capellaspace.com/hc/en-us/articles/360059224291-What-SAR-imagery-products-are-available-with-Capella->`_
        """
        # Using az resolution
        if self.sensor_mode == CapellaSensorMode.SP:
            def_pixel_size = 0.35
            def_res = 0.5
        elif self.sensor_mode == CapellaSensorMode.SS:
            def_pixel_size = 0.6
            def_res = 1.0
        elif self.sensor_mode == CapellaSensorMode.SM:
            def_pixel_size = 0.8
            def_res = 1.2
        else:
            raise InvalidProductError(f"Unknown sensor mode: {self.sensor_mode}")
        self.pixel_size = def_pixel_size
        self.resolution = def_res

    def _set_instrument(self) -> None:
        """
        Set instrument
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

        # Private attributes
        try:
            self.snap_filename = str(next(self.path.glob("*CAPELLA*.json")).name)
        except StopIteration as exc:
            raise FileNotFoundError(
                f"Non existing file *CAPELLA*.json in {self.path}"
            ) from exc

        # To be done in pre-init, but we don't have the product name here
        name = self._get_name()
        try:
            self._raw_band_regex = str(next(self.path.glob(f"{name}.tif")).name)
        except StopIteration:
            # For SICD and SIDD
            try:
                self._raw_band_regex = str(next(self.path.glob(f"{name}.ntf")).name)
            except StopIteration as exc:
                raise FileNotFoundError(
                    f"Non existing file {name}.tif or {name}.ntf in {self.path}"
                ) from exc

        # Pre init done by the super class
        super()._pre_init(**kwargs)

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
        if self._has_stac_mtd:
            try:
                mtd_file = next(self.path.glob(f"{self.name}.json"))
            except StopIteration as exc:
                raise FileNotFoundError(
                    f"Non existing file {self.name}.json in {self.path}"
                ) from exc
            extent = vectors.read(mtd_file)
        else:
            extent = None
            root, _ = self.read_mtd()

            # Get image size
            height = int(root.findtext(".//rows"))
            width = int(root.findtext(".//columns"))

            # Investigate image geometry
            img_geom = root.find(".//image_geometry")
            geom_type = img_geom.findtext("type")

            # Use given geotransform if existing
            if geom_type == "geotransform":
                tf = [
                    float(it.text)
                    for it in img_geom.find("geotransform").iterfind("item")
                ]
                # TODO: manage not WKT case
                crs = img_geom.find("coordinate_system").findtext("wkt")
                if crs:
                    # Convert to rasterio
                    west, south, east, north = transform.array_bounds(
                        height, width, transform=Affine.from_gdal(*tf)
                    )
                    extent = gpd.GeoDataFrame(
                        geometry=[box(minx=west, miny=north, maxx=east, maxy=south)],
                        crs=CRS.from_string(crs),
                    )

            # Use center pixel
            if extent is None:
                # Get center pixel point in UTM
                center_pixel = root.find(".//center_pixel")
                target_position = [
                    float(it.text)
                    for it in center_pixel.find("target_position").iterfind("item")
                ]
                center_pix = gpd.GeoDataFrame(
                    geometry=[Point(target_position)],
                    crs={"proj": "geocent", "ellps": "WGS84", "datum": "WGS84"},
                ).to_crs(WGS84)
                center_pix.to_crs(center_pix.extent_wgs84.estimate_utm_crs())

                # Get pixel spacing in meters
                pixel_spacing_h = float(root.findtext(".//pixel_spacing_row"))
                pixel_spacing_w = float(root.findtext(".//pixel_spacing_column"))

                # Compute offset from center of image
                offset_h = pixel_spacing_h * height / 2
                offset_w = pixel_spacing_w * width / 2

                tl_corner = center_pix.translate(xoff=-offset_w, yoff=-offset_h)
                br_corner = center_pix.translate(xoff=offset_w, yoff=offset_h)

                extent = gpd.GeoDataFrame(
                    geometry=[
                        box(
                            minx=tl_corner.x.iat[0],
                            miny=tl_corner.y.iat[0],
                            maxx=br_corner.x.iat[0],
                            maxy=br_corner.y.iat[0],
                        )
                    ],
                    crs=CRS.from_string(self.crs()),
                )

        return extent.to_crs(WGS84)

    def _set_product_type(self) -> None:
        """Set products type"""
        # Open identifier
        prod_type = self.split_name[3]
        self.product_type = getattr(CapellaProductType, prod_type)

        # WARNING: Capella don't seem to have Ground Range products...

        if self.product_type == CapellaProductType.GEO:
            self.sar_prod_type = SarProductType.ORTHO
        elif self.product_type == CapellaProductType.GEC:
            self.sar_prod_type = SarProductType.GEOCODED
        elif self.product_type == CapellaProductType.SLC:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not handled by EOReader"
            )

    def _set_sensor_mode(self) -> None:
        """Get sensor mode"""
        sensor_mode = self.split_name[2]
        self.sensor_mode = getattr(CapellaSensorMode, sensor_mode)

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
            root, _ = self.read_mtd()

            # Open identifier
            if self._has_stac_mtd:
                acq_date = root.findtext(".//datetime")
            else:
                acq_date = root.findtext(".//start_timestamp")
            if not acq_date:
                raise InvalidProductError(
                    "datetime or start_timestamp not found in metadata!"
                )

            # Convert to datetime (too many microseconds)
            date = datetime.strptime(acq_date.split(".")[0], "%Y-%m-%dT%H:%M:%S")
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
        name = None
        for file in self.path.glob("*.tif"):
            if "preview" not in file.name:
                name = path.get_filename(file)

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read GeoJSON metadata and outputs its as a metadata XML root and its namespaces as an empty dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """

        # MTD are JSON
        try:
            try:
                mtd_file = next(self.path.glob(f"{self.name}.json"))
                self._has_stac_mtd = True
            except StopIteration:
                try:
                    LOGGER.warning(
                        f"Non available STAC metadata for the product {self.name}. Opening Extended Metadata instead."
                    )
                    mtd_file = next(self.path.glob(f"{self.name}*.json"))
                    self._has_stac_mtd = False
                except StopIteration as ex:
                    raise InvalidProductError(
                        f"Metadata file not found in {self.path}"
                    ) from ex

            data = files.read_json(mtd_file, print_file=False)
            root = etree.fromstring(dicttoxml(data))
        except etree.XMLSyntaxError as exc:
            raise InvalidProductError(
                f"Cannot convert metadata to XML for {self.path}!"
            ) from exc

        return root, {}

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the existing path of the VV band (as they come with the archived products).
        Capella product only contains a VV band !

        Args:
            **kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        band_paths = {}
        try:
            # To be used before post-init (name doesn't exist here)
            if self.split_name is None:
                split_name = utils.get_split_name(self._get_name())
            else:
                split_name = self.split_name

            pol = sab.from_value(split_name[4])
            band_paths[pol] = path.get_file_in_dir(
                self._band_folder, self._raw_band_regex, exact_name=True, get_list=False
            )
        except FileNotFoundError as exc:
            raise InvalidProductError(
                f"An {self.constellation.name} product should at least contain one band !"
            ) from exc

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

    # @cache
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
        ob = None
        if self._has_stac_mtd:
            root, _ = self.read_mtd()

            ob = root.findtext(".//key[@name='sat:orbit_state']")
            ob = OrbitDirection.from_value(ob.upper())

        if ob is None:
            ob = super().get_orbit_direction()

        return ob
