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
SkySat products.
See
`Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
and `Planet documentation <https://developers.planet.com/docs/data/skysat/>`_
for more information.
"""

import logging
from collections import defaultdict
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from sertit import path, rasters, vectors, xml
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.bands import (
    BLUE,
    GREEN,
    NIR,
    PAN,
    RED,
    BandNames,
    SpectralBand,
    is_spectral_band,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.optical_product import RawUnits
from eoreader.products.optical.planet_product import PlanetProduct
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class SkyInstrument(ListEnum):
    """Skysat instrument
    See `OSCAR instrument <https://space.oscar.wmo.int/instruments/view/skysat>`__
    for more information.
    """

    SKY = "SkySat"
    """
    5-channel VIS/NIR radiometer with one panchromatic channel and 4 multi-spectral. Capability of video-clips.
    """


@unique
class SkyItemType(ListEnum):
    """
    Skysat item types (processing levels)

    Only SkySat Collect items are managed for now: https://developers.planet.com/docs/data/skysat/
    """

    SCENE = "SkySat Scene Product"
    """
    A SkySat Scene Product is an individual framed scene within a strip,
    captured by the satellite in its line-scan of the Earth.
    SkySat Satellites have three cameras per satellite, which capture three overlapping strips.
    Each of these strips contain overlapping scenes, not organized to any particular tiling grid system.
    SkySat Scene products are approximately 1 x 2.5 square kilometers in size. They are represented in the Planet Platform as the SkySatScene item type.

    Not handled by EOReader for now.
    """

    COLLECT = "SkySat Collect Product"
    """
    A SkySat Collect Product is created by composing roughly 60 SkySat Scenes along an imaging strip into an orthorectified segment,
    approximately 20 x 5.9 square kilometers in size. They are represented in the Planet Platform as the SkySatCollect item type.
    This product may be easier to handle, if you're looking at larger areas of interest with SkySat imagery.
    Due to the image rectification process involved in creating this product, Collect is generally recommended over the Scene product when the AOI spans multiple scenes,
    particularly if a mosaic or composite image of the individual scenes is required. Collect performs necessary rectification steps automatically.
    This is especially useful for users who don't feel comfortable doing orthorectification manually.
    """

    VIDEO = "SkySat Video "
    """
    A SkySat Video Product is a full motion video are collected between 30 and 120 seconds by a single camera from any of the SkySats.
    Its size is comparable to a SkySat Scene, about 1 x 2.5 square kilometers.
    They are represented in the Planet Platform as the SkySatVideo item type.

    Not handled by EOReader.
    """


@unique
class SkyProductType(ListEnum):
    """
    Skysat product types (processing levels)

    Only SkySat Collect items are managed for now: https://developers.planet.com/docs/data/skysatcollect/
    """

    L1A = "l1a_panchromatic"
    """
    Basic L1A Panchromatic (basic_l1a_panchromatic_dn) assets are non-orthorectified, uncalibrated, panchromatic-only imagery products with native sensor resolution (0.72-0.81m),
    that have been made available roughly two hours before all other SkySat asset types are available in the catalog.
    These products are designed for time-sensitive, low-latency monitoring applications,
    and can be geometrically corrected with associated rational polynomial coefficients (RPCs) assets (derived from satellite telemetry).

    Not handled by EOReader.
    """

    ORTHO_PAN = "panchromatic"
    """
    Ortho Panchromatic (ortho_panchromatic) assets are orthorectified, calibrated, super-resolved (0.50m),
    panchromatic-only imagery products that have been transformed to Top of Atmosphere (at-sensor) radiance.
    These products are designed for data science and analytic applications which require a wider spectral range (Pan: 450 - 900 nm),
    highest available resolution, and accurate geolocation and cartographic projection.
    """

    ORTHO_ANA = "analytic"
    """
    Ortho Analytic (ortho_analytic) assets are orthorectified, calibrated, multispectral imagery products with native sensor resolution (0.72-0.81m),
    that have been transformed to Top of Atmosphere (at-sensor) radiance.
    These products are designed for data science and analytic applications which require imagery with accurate geolocation and cartographic projection.
    """

    ORTHO_VIS = "visual"
    """
    Ortho Visual (ortho_visual) assets are orthorectified, color-corrected, super-resolved (0.50m), RGB imagery products that are optimized for the human eye,
    providing images as they would look if viewed from the perspective of the satellite. Lower resolution multispectral bands are sharpened by the super-resolved panchromatic band.
    These products are designed for simple and direct visual inspection, and can be used and ingested directly into a Geographic Information System or application.

    Not handled by EOReader.
    """

    ORTHO_PSH = "pansharpened"
    """
    Ortho Pansharpened (ortho_pansharpened) assets are orthorectified, uncalibrated, super-resolved (0.50m) multispectral imagery products.
    Lower resolution multispectral bands are sharpened to match the resolution of the super-resolved panchromatic band.
    These products are designed for multispectral applications which require highest available resolution and accurate geolocation and cartographic projection.
    """

    """
    Naming: <acquisition date>_<acquisition time>_<satellite_id>_<frame_id>_<bandProduct>.<extension>

    Asset Types:
    ortho_analytic 	            Radiometrically calibrated GeoTiff suitable for analytic applications
    ortho_analytic_sr 	        Orthorectified product, radiometrically calibrated and atmospherically corrected to surface reflectance
    ortho_analytic_dn 	        Non-radiometrically calibrated GeoTiff suitable for analytic applications.
    ortho_analytic_udm 	        Unusable Data Mask - Unusable data bit mask in GeoTIFF format for the analytic scene assets.
    ortho_analytic_udm2 	    Orthorectified usable data mask (Cloud 2.0)
    ortho_panchromatic 	        Orthorectified Radiometrically-calibrated panchromatic image stored as 16-bit scaled radiance
    ortho_panchromatic_dn 	    Basic sensor corrected panchromatic band GeoTiff. Scene based framing and not projected to a cartographic projection.
    ortho_panchromatic_udm 	    Unusable Data Mask - Unusable data bit mask in GeoTIFF format for the pansharpened DN scene assets.
    ortho_panchromatic_udm2 	Orthorectified usable data mask (Cloud 2.0)
    ortho_pansharpened 	        Color corrected and pansharpened GeoTiff for visual applications.
    ortho_pansharpened_udm 	    Unusable Data Mask - Unusable data bit mask in GeoTIFF format for the pansharpened scene assets.
    ortho_pansharpened_udm2 	Orthorectified usable data mask (Cloud 2.0)
    ortho_visual 	            Color corrected GeoTiff for visual applications.
    """


class SkyProduct(PlanetProduct):
    """
    Class of SkySat products.
    See `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`__
    for more information.

    Only SkySat Collect items are managed for now.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.constellation = self._get_constellation()
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self._has_cloud_cover = True

        # Post init done by the super class
        super()._post_init(**kwargs)

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
        arr = rasters.read(self.get_default_band_path(), indexes=[1])
        return rasters.get_valid_vector(arr, default_nodata=0)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Optical data: resolution = pixel_resolution (not gsd)
        root, _ = self.read_mtd()
        self.pixel_size = float(root.findtext(".//pixel_resolution"))

    def _set_instrument(self) -> None:
        """
        Set instrument

        SkySat: https://space.oscar.wmo.int/instruments/view/skysat
        """
        # Set correct constellation
        self.instrument = SkyInstrument.SKY

    def _map_bands(self):
        """
        Map bands
        """
        if self.product_type == SkyProductType.ORTHO_PAN:
            band_map = {
                PAN: SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self.pixel_size,
                        WV_MIN: 450,
                        WV_MAX: 900,
                    },
                )
            }
        else:
            band_map = {
                BLUE: SpectralBand(
                    eoreader_name=BLUE,
                    **{
                        NAME: "Blue",
                        ID: 1,
                        GSD: self.pixel_size,
                        WV_MIN: 450,
                        WV_MAX: 515,
                    },
                ),
                GREEN: SpectralBand(
                    eoreader_name=GREEN,
                    **{
                        NAME: "Green",
                        ID: 2,
                        GSD: self.pixel_size,
                        WV_MIN: 515,
                        WV_MAX: 595,
                    },
                ),
                RED: SpectralBand(
                    eoreader_name=RED,
                    **{
                        NAME: "Red",
                        ID: 3,
                        GSD: self.pixel_size,
                        WV_MIN: 605,
                        WV_MAX: 695,
                    },
                ),
                NIR: SpectralBand(
                    eoreader_name=NIR,
                    **{
                        NAME: "NIR",
                        ID: 4,
                        GSD: self.pixel_size,
                        WV_MIN: 740,
                        WV_MAX: 900,
                    },
                ),
            }

        # Set the band map
        self.bands.map_bands(band_map)

    def _set_product_type(self) -> None:
        """Set products type"""
        stack_path = self._get_path(
            filename=self.name, invalid_lookahead="_udm", extension="tif"
        )

        for prod_type in SkyProductType:
            if prod_type.value in stack_path:
                self.product_type = prod_type
                break

        if self.product_type is None:
            raise InvalidProductError(
                f"Unknown product type for stack named {path.get_filename(stack_path)}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms
            >>> prod.get_datetime(as_datetime=False)
            '20190625T105728'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()
            datetime_str = root.findtext(".//acquired")
            if not datetime_str:
                raise InvalidProductError("Cannot find acquired in the metadata file.")

            # Convert to datetime
            datetime_str = datetime.strptime(datetime_str, DATETIME_FMT)

        else:
            datetime_str = self.datetime

        if not as_datetime:
            datetime_str = datetime_str.strftime(DATETIME_FMT)

        return datetime_str

    def _get_stack_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet stack path(s)

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        if self._merged:
            stack_path, _ = self._get_out_path(f"{self.condensed_name}_analytic.vrt")
            if as_list:
                stack_path = [stack_path]
        else:
            stack_path = self._get_path(
                "ssc", "tif", invalid_lookahead="_udm", as_list=as_list
            )

        return stack_path

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        refl_coef = None
        # Only Ortho Analytic and Ortho Panchromatic are calibrated
        # https://developers.planet.com/docs/data/skysat/
        # (when managing SkySatScene, add Basic Panchromatic and Basic Analytic)
        if self.product_type in [SkyProductType.ORTHO_ANA, SkyProductType.ORTHO_PAN]:
            if self._raw_units != RawUnits.REFL:
                import json

                import rasterio

                try:
                    with rasterio.open(band_path) as ds:
                        tags = ds.tags()["TIFFTAG_IMAGEDESCRIPTION"]
                        prop = json.loads(tags)["properties"]

                    coeffs = prop.get("reflectance_coefficients")
                except (AttributeError, KeyError):
                    coeffs = None

                if coeffs:
                    # "reflectance_coefficients": [1: Blue, 2: Green, 3: Red, 4: Near-infrared]
                    # https://support.planet.com/hc/en-us/articles/4406644970513-What-is-the-order-of-reflectance-coefficients-in-the-GeoTIFF-Header-for-SkaySat-imagery-
                    refl_coef = coeffs[band.id - 1]
                else:
                    LOGGER.warning(
                        "No reflectance coefficients are found. Your product will be read as is."
                    )
        else:
            LOGGER.warning(
                f"Impossible to convert the data to reflectance ({self.product_type.value}). "
                f"Only {SkyProductType.ORTHO_ANA.value} and {SkyProductType.ORTHO_PAN.value} products can be."
                "See https://support.planet.com/hc/en-us/articles/4408818004497/comments/5291365958429 for more information."
            )

        if refl_coef is None:
            # https://support.planet.com/hc/en-us/articles/4408818004497/comments/5291365958429
            # Makes no sense to try to get reflectance data. Keep them as is.
            return band_arr
        else:
            return band_arr * refl_coef

    def _update_attrs_constellation_specific(
        self, xarr: xr.DataArray, bands: list, **kwargs
    ) -> xr.DataArray:
        """
        Update attributes of the given array (constellation specific)

        Args:
            xarr (xr.DataArray): Array whose attributes need an update
            bands (list): Array name (as a str or a list)

        Returns:
            xr.DataArray: Updated array/dataset
        """

        xarr = super()._update_attrs_constellation_specific(xarr, bands, **kwargs)

        # Do not add this if one non-spectral bands exists
        has_spectral_bands = [is_spectral_band(band) for band in bands]
        if all(has_spectral_bands):
            if self.product_type in [
                SkyProductType.ORTHO_ANA,
                SkyProductType.ORTHO_PAN,
            ]:
                xarr.attrs["radiometry"] = "reflectance"
            else:
                xarr.attrs["radiometry"] = "as is"

        return xarr

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read GeoJSON metadata and outputs its as a metadata XML root and its namespaces as an empty dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "**/*metadata*.json"
        mtd_archived = r".*metadata.*\.json"

        # MTD are geojson -> open as gpd.GeoDataFrame
        try:
            if self.is_archived:
                data = self._read_archived_vector(archive_regex=mtd_archived)

            else:
                try:
                    mtd_file = next(self.path.glob(mtd_from_path))
                    data = vectors.read(mtd_file)
                except StopIteration as ex:
                    raise InvalidProductError(
                        f"Metadata file ({mtd_from_path}) not found in {self.path}"
                    ) from ex
        except etree.XMLSyntaxError as exc:
            raise InvalidProductError(f"Invalid metadata XML for {self.path}!") from exc

        # Format datetime
        data["acquired"] = data["acquired"].dt.strftime(DATETIME_FMT)

        root = xml.df_to_xml(data)

        return root, {}

    def _get_condensed_name(self) -> str:
        """
        Get SkySat products condensed name ({date}_{constellation}_{product_type}_{unique_id}).

        Returns:
            str: Condensed name
        """
        unique_id = self.split_name[-1]
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{unique_id}"

    def _merge_subdatasets_mtd(self):
        """
        Merge subdataset, when several Planet products avec been ordered together (for SkySat Scenes)
        Will create a reflectance (if possible) VRT, a UDM/UDM2 VRT and a merged metadata XML file.
        """
        # Merge datasets
        analytic_vrt_path, analytic_vrt_exists = self._merge_subdatasets()

        # Get all attributes to mean
        mtd_file, mtd_exists = self._get_out_path(
            f"{self.condensed_name}_metadata.json"
        )
        if not mtd_exists:
            attrs_to_mean = [
                "clear_confidence_percent",
                "clear_percent",
                "cloud_cover",
                "cloud_percent",
                "heavy_haze_percent",
                "light_haze_percent",
                "satellite_azimuth",
                "shadow_percent",
                "snow_ice_percent",
                "sun_azimuth",
                "sun_elevation",
                "view_angle",
                "visible_confidence_percent",
                "visible_percent",
            ]
            attrs = defaultdict(list)
            geometry = None
            default_mtd = None

            for mtd_file in self._get_path("metadata", "json", as_list=True):
                mtd = vectors.read(mtd_file)

                for attr in attrs_to_mean:
                    attrs[attr].append(getattr(mtd, attr))

                if geometry is None:
                    default_mtd = mtd
                    geometry = mtd.geometry
                else:
                    geometry = geometry.union(mtd.geometry)

            # Update mtd
            default_mtd.geometry = geometry

            for attr in attrs_to_mean:
                setattr(default_mtd, attr, np.mean(attrs[attr]))

            default_mtd.to_file(mtd_file, driver="GeoJSON")
