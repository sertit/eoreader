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
Umbra products.
Take a look
`here <https://help.umbra.space/product-guide/umbra-products>`_.
"""

import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
from dicttoxml import dicttoxml
from lxml import etree
from rasterio import crs
from sertit import files, path, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType
from sertit.vectors import WGS84
from shapely import Polygon, force_2d

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import SarBandNames as sab
from eoreader.exceptions import InvalidProductError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class UmbraProductType(ListEnum):
    """
    Umbra products types.
    Take a look
    `here <https://help.umbra.space/product-guide/umbra-products/umbra-product-specifications>`_.
    """

    SLC = "SLC"
    """
    Single Look Complex (SLC)

    - Contains both amplitude and phase of the radar signal
    - Range-compressed and focused SAR image in slant-range geometry
    - Georeferenced using orbit data and Range-Doppler projected
    """

    CSI = "CSI"
    """
    Color Sub-Aperture Image (CSI)
    
    Not used by EOReader.
    """

    GEC = "GEC"
    """
    Geo-Ellipsoid Corrected (GEC) GeoTIFF

    If RPC are present, can be orthorectified.
    """

    SIDD = "SIDD"
    """
    Sensor Independent Derived Data (SIDD)

    Not used by EOReader.
    """

    NITF = "NITF"
    """
    National Imagery Transmission Format (NITF)

    Not used by EOReader.
    """

    SICD = "SICD"
    """
    Sensor Independent Complex Data (SICD)

    Not used by EOReader.
    """

    CPHD = "CPHD"
    """
    Compensated Phase History Data (CPHD)

    Not used by EOReader.
    """


@unique
class UmbraSensorMode(ListEnum):
    """
    Umbra imaging mode.
    Take a look
    `here <https://help.umbra.space/product-guide/umbra-products>`_.
    """

    SP = "SPOTLIGHT"
    """Spotlight"""

    SM = "STRIPMAP"
    """
    StripMap
    
    Not available yet, but already visible in the `documentation <https://help.umbra.space/product-guide/umbra-products/future-imaging-modes`_.
    """


class UmbraProduct(SarProduct):
    """
    Class for Umbra Products
    Take a look
    `here <https://help.umbra.space/product-guide>`_.
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
        See
        `here <https://help.umbra.space/product-guide/umbra-products/umbra-product-specifications>`_
        """
        root, _ = self.read_mtd()
        if self._has_stac_mtd:
            res = float(root.findtext(".//resolution_range"))
        else:
            res = float(root.findtext(".//targetIpr"))
        if not res:
            raise InvalidProductError(
                "resolution_azimuth or targetIpr not found in metadata!"
            )

        self.resolution = np.round(res, 3)

        # Compare the retrieved resolution to the one given in the documentation
        doc_res = [0.15, 0.25, 0.35, 0.5, 1.0]
        if self.resolution not in doc_res:
            LOGGER.warning(
                f"Resolution retrieved from metadata ({self.resolution} m) is different from the ones given in the documentation: {doc_res}"
            )

        # For Umbra, resolution and pixel size seems to be the same...
        # Nothing mentions any GSD in the new mtd, and it's the case for the deprecated one
        self.pixel_size = self.resolution

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

        # To be done in pre-init, but we don't have the product name here
        name = self._get_name()
        try:
            self._raw_band_regex = str(next(self.path.glob(f"{name}_*.tif")).name)
        except StopIteration:
            # For SICD and SIDD
            try:
                self._raw_band_regex = str(next(self.path.glob(f"{name}_*.nitf")).name)
            except StopIteration as exc:
                raise FileNotFoundError(
                    f"Non existing file {name}.tif or {name}.nitf in {self.path}"
                ) from exc

        # Pre init done by the super class
        super()._pre_init(**kwargs)

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
        if self._has_stac_mtd:
            footprint = vectors.read(self._get_stac_mtd_path())
        else:
            # Easier with mtd in JSON here
            footprint_mtd = files.read_json(self._get_mtd_path())
            # TODO: modify this when mosaic will exist?
            footprint_mtd = footprint_mtd["collects"][0]["footprintPolygonLla"]
            type = footprint_mtd["type"]
            if type != "Polygon":
                raise NotImplementedError(
                    "Footprints that are not polygons are not yet supported for Umbra products. "
                    "Please write an issue on GitHub!"
                )
            coordinates = footprint_mtd["coordinates"][0]
            footprint = gpd.GeoDataFrame(
                geometry=[force_2d(Polygon(coordinates))], crs=WGS84
            )

        return footprint.to_crs(self.crs())

    def _get_raw_crs(self) -> crs.CRS:
        return WGS84

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
        # For now, it's only SPOTLIGHT, but be ready for any STRIPMAP appearance
        root, _ = self.read_mtd()
        if self._has_stac_mtd:
            # Estimate UTM from footprint
            crs = vectors.read(self._get_stac_mtd_path()).estimate_utm_crs()
        else:
            # Estimate UTM from center point
            center = root.findtext(".//sceneCenterPointLla")
            if not center:
                raise InvalidProductError("sceneCenterPointLla not found in metadata!")
            coordinates = center["coordinates"][0]
            crs = vectors.to_utm_crs(coordinates[0], coordinates[1])

        return crs

    def _get_stac_mtd_path(self):
        return next(self.path.glob(f"{self.name}.stac*.json"))

    def _get_mtd_path(self):
        # https://docs.canopy.umbra.space/docs/delivered-product-types
        # DEPRECATED
        return next(self.path.glob(f"{self.name}_METADATA.json"))

    def _get_gec_path(self):
        # GEC is mandatory (for now)
        try:
            return next(self.path.glob(f"{self.name}_GEC.tif"))
        except StopIteration as ex:
            raise FileNotFoundError(
                f"GEC file not found in {self.path}. "
                "GEC is the only Umbra product type handled by EOReader."
            ) from ex

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
        extent = self.footprint()
        extent.geometry = extent.envelope

        return extent.to_crs(WGS84)

    def _set_product_type(self) -> None:
        """Set products type"""
        # Only product type handled by EOReader
        self.product_type = UmbraProductType.GEC

        # WARNING: Umbra don't seem to have Ground Range products...
        # Use try/except here for the future (for GEO/GRD ?), because now it's ineffective ;-)
        if self.product_type == UmbraProductType.GEC:
            self.sar_prod_type = SarProductType.GEOCODED
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not handled by EOReader"
            )

    def _set_sensor_mode(self) -> None:
        """Get sensor mode"""
        # For now, it's only SPOTLIGHT, but be ready for any STRIPMAP appearance
        root, _ = self.read_mtd()
        if self._has_stac_mtd:
            mode = root.findtext(".//instrument_mode")
        else:
            mode = root.findtext(".//imagingMode")
        if not mode:
            raise InvalidProductError(
                "instrument_mode or imagingMode not found in metadata!"
            )

        self.sensor_mode = UmbraSensorMode(mode)

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

            # Open datetime
            if self._has_stac_mtd:
                acq_date = root.findtext(".//datetime").split(".")[0]
            else:
                acq_date = root.findtext(".//startAtUTC").split("+")[0]

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S")

            if not acq_date:
                raise InvalidProductError(
                    "datetime or startAtUTC not found in metadata!"
                )
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
        name = path.get_filename(self._get_gec_path()).replace("_GEC", "")

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read GeoJSON metadata and outputs it as a metadata XML root and its namespaces as an empty dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """

        # MTD are JSON
        try:
            try:
                mtd_file = self._get_stac_mtd_path()
                self._has_stac_mtd = True
            except StopIteration:
                # https://docs.canopy.umbra.space/docs/delivered-product-types
                # DEPRECATED
                try:
                    LOGGER.warning(
                        f"Non available STAC metadata for the product {self.name}. Opening Extended Metadata instead."
                    )
                    mtd_file = self._get_mtd_path()
                    self._has_stac_mtd = False
                except StopIteration as ex:
                    raise InvalidProductError(
                        f"Metadata file not found in {self.path}"
                    ) from ex

            data = files.read_json(mtd_file, print_file=False)

            # Sanitize STAC mtd (remove STAC prefixes with ':' that break XML keys)
            if self._has_stac_mtd:

                def __sanitize_recursive(d):
                    for key in d.copy():
                        k = key.split(":")[-1]
                        d[k] = d.pop(key)
                        if isinstance(d[k], dict):
                            __sanitize_recursive(d[k])

                data.pop("assets", None)
                __sanitize_recursive(data)
            root = etree.fromstring(dicttoxml(data, attr_type=False))
        except etree.XMLSyntaxError as exc:
            raise InvalidProductError(
                f"Cannot convert metadata to XML for {self.path}!"
            ) from exc

        return root, {}

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the existing path of the VV band (as they come with the archived products).
        Umbra product only contains a VV band !

        Args:
            **kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        band_paths = {}

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open polarizations
        # Same for the two MTD
        pol = root.find(".//polarizations").findtext("item")

        # Convert pol to an EOReader band
        pol = sab.from_value(pol)

        # Set the GEC path
        band_paths[pol] = self._get_gec_path()

        return band_paths

    def _pre_process_sar(self, band: sab, pixel_size: float = None, **kwargs) -> str:
        """
        Pre-process SAR data (geocoding...)

        Args:
            band (sbn): Band to preprocess
            pixel_size (float): Pixel size
            kwargs: Additional arguments

        Returns:
            str: Band path
        """
        raw_band_path = self._get_gec_path()

        ortho_path, ortho_exists = self._get_out_path(
            self.get_band_file_name(band, pixel_size, **kwargs)
        )
        if not ortho_exists:
            with rasterio.open(raw_band_path) as ds:
                # Orthorectify GEC if RPC are available
                if ds.rpcs is not None:
                    # Reproject and write on disk data
                    dem_path = self._get_dem_path(**kwargs)
                    LOGGER.info(
                        f"GEC file has RPCs: orthorectifying {band.name} band with {files.get_filename(dem_path)}"
                    )
                    arr = utils.read(self._get_gec_path())
                    self._reproject(
                        arr,
                        ds.rpcs,
                        dem_path=dem_path,
                        ortho_path=ortho_path,
                        long_name="Orthorectified GEC",
                    )
                    LOGGER.debug(f"{band.name} band orthorectified.")

                # Reproject to UTM if CRS is not projected
                elif not ds.crs.is_projected:
                    # Warp band if needed
                    LOGGER.info(
                        f"GEC file has no RPCs: reprojecting {band.name} band to UTM. Warning, the accuracy will be low in montaineous areas!"
                    )
                    self._warp_band(
                        raw_band_path,
                        reproj_path=ortho_path,
                        pixel_size=pixel_size,
                    )
                    LOGGER.debug(f"{band.name} band reprojected.")
                else:
                    ortho_path = raw_band_path
        return ortho_path

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

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open orbit direction
        if self._has_stac_mtd:
            ob = root.findtext(".//orbit_state")
        else:
            ob = root.findtext(".//satelliteTrack")
        ob = OrbitDirection.from_value(ob.upper())

        if ob is None:
            ob = super().get_orbit_direction()

        return ob
