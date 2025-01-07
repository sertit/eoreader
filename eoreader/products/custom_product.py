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
"""Class for custom products"""

import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from lxml.builder import E
from rasterio import crs
from rasterio.enums import Resampling
from sertit import logs, misc, path, rasters, types
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    BandNames,
    SarBand,
    SarBandMap,
    SpectralBand,
    SpectralBandMap,
    is_sat_band,
    to_band,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.product import OrbitDirection, Product, SensorType
from eoreader.reader import Constellation
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CustomFields(ListEnum):
    """
    Custom fields, self-explanatory
    """

    NAME = "name"
    SENSOR_TYPE = "sensor_type"
    DATETIME = "datetime"
    BAND_MAP = "band_map"
    CONSTELLATION = "constellation"
    INSTRUMENT = "instrument"
    RES = "resolution"
    PIX_SIZE = "pixel_size"
    PROD_TYPE = "product_type"
    SUN_AZ = "sun_azimuth"
    SUN_ZEN = "sun_zenith"
    ORBIT_DIR = "orbit_direction"
    CC = "cloud_cover"


# -- CUSTOM
CUSTOM = "CUSTOM"


class CustomProduct(Product):
    """Custom products"""

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.kwargs = kwargs
        """Custom kwargs"""

        # Initialization from the super class
        # (Custom products are managing constellation on their own)
        super_kwargs = kwargs.copy()
        super_kwargs.pop("constellation", None)
        super().__init__(
            product_path, archive_path, output_path, remove_tmp, **super_kwargs
        )

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """

        # Custom products are stacked
        self.is_stacked = True

        self.needs_extraction = False

        # -- Parse the kwargs
        misc.check_mandatory_keys(
            kwargs, [CustomFields.BAND_MAP.value, CustomFields.SENSOR_TYPE.value]
        )

        # Process kwargs
        for key in self.kwargs:
            try:
                CustomFields.from_value(key)  # noqa
            except ValueError:
                LOGGER.warning(
                    f"{key} is not taken into account as it doesn't belong to the handled keys: {CustomFields.list_values()}"
                )

        # Sensor type
        self.sensor_type = SensorType.convert_from(
            kwargs.pop(CustomFields.SENSOR_TYPE.value)
        )[0]

    def _map_bands(self):
        """
        Map bands
        """
        if self.sensor_type == SensorType.OPTICAL:
            band_map = SpectralBandMap()
            band = SpectralBand
        else:
            band_map = SarBandMap()
            band = SarBand

        self.bands = band_map

        # Band map
        band_names = self.kwargs.pop(CustomFields.BAND_MAP.value)  # Shouldn't be empty
        assert isinstance(band_names, dict)

        band_map = {}
        for key, val in band_names.items():
            band_name = to_band(key)[0]
            assert is_sat_band(
                band_name
            ), f"{band_name}: Custom bands should be satellite band"
            band_map[band_name] = band(
                eoreader_name=band_name, name=band_name.value, id=val
            )

        self.bands.map_bands(band_map)

        # Test on the product
        with rasterio.open(str(self.get_default_band_path())) as ds:
            assert (
                len(band_names) == ds.count
            ), f"You should specify {ds.count} bands in band_map, not {len(band_names)} !"

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        # Check CRS
        try:
            crs = self.crs()  # noqa
        except InvalidProductError as msg:
            LOGGER.warning(msg)

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        name = self.kwargs.get(CustomFields.NAME.value)
        if name is None:
            name = path.get_filename(self.path)
        return name

    def get_datetime(self, as_datetime: bool = False) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """

        # Datetime
        dt = self.kwargs.get(CustomFields.DATETIME.value)
        if dt is None:
            dt = datetime.now()
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                dt = datetime.strptime(dt, "%Y%m%dT%H%M%S")
        assert isinstance(dt, datetime)

        return dt if as_datetime else dt.strftime(DATETIME_FMT)

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation"""
        const = self.kwargs.get(CustomFields.CONSTELLATION.value)
        if const is None:
            const = CUSTOM
        return Constellation.convert_from(const)[0]

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        pixel_size = self.kwargs.get(CustomFields.PIX_SIZE.value)
        if pixel_size is None and CustomFields.RES.value in self.kwargs:
            logs.deprecation_warning(
                "`resolution` is deprecated in favor of `pixel_size` to avoid confusion."
            )
            pixel_size = self.kwargs.pop(CustomFields.RES.value)

        if pixel_size is None:
            with rasterio.open(str(self.get_default_band_path())) as ds:
                self.pixel_size = np.round(ds.res[0], 2)
        else:
            self.pixel_size = pixel_size

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        self.instrument = self.kwargs.get(CustomFields.INSTRUMENT.value)
        if self.instrument is None:
            self.instrument = CUSTOM

    def _set_product_type(self) -> None:
        """Set products type"""

        self.product_type = self.kwargs.get(CustomFields.PROD_TYPE.value)
        if self.product_type is None:
            self.product_type = CUSTOM

    def get_default_band(self) -> BandNames:
        """
        Get default band: the first one of the stack

        Returns:
            str: Default band
        """
        return list(self.get_existing_bands())[0]

    def get_default_band_path(self, **kwargs) -> AnyPathType:
        """
        Get default band path: the stack path.

        Args:
            kwargs: Additional arguments
        Returns:
            AnyPathType: Default band path
        """
        return self.path

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of stack.

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get extent
        return rasters.get_extent(self.get_default_band_path()).to_crs(self.crs())

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
        arr = rasters.read(self.get_default_band_path(), indexes=[1])
        return rasters.get_footprint(arr).to_crs(self.crs())

    @cache
    def crs(self) -> crs.CRS:
        """
        Get UTM projection of stack.

        Returns:
            crs.CRS: CRS object
        """
        with rasterio.open(str(self.path)) as ds:
            def_crs = ds.crs

        if def_crs.is_projected:
            pass
        else:
            extent_wgs84 = rasters.get_extent(self.get_default_band_path())

            # Get upper-left corner and deduce UTM proj from it
            raise InvalidProductError(
                "Only stacks with projected CRS can be processed! "
                f"Please reproject it to the corresponding UTM projection ({extent_wgs84.estimate_utm_crs()})!"
            )

        return def_crs

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        Get the stack path for each asked band

        Args:
            band_list (list): List of the wanted bands
            pixel_size (float): Band pixel size
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            band_paths[band] = self.path
        return band_paths

    def get_existing_band_paths(self) -> dict:
        """
        Get the stack path.

        Returns:
            dict: Dictionary containing the path of every orthorectified bands
        """
        existing_bands = self.get_existing_bands()
        return self.get_band_paths(band_list=existing_bands)

    def get_existing_bands(self) -> list:
        """
        Get the bands of the stack.

        Returns:
            list: List of existing bands in the products
        """
        return [name for name, nb in self.bands.items() if nb]

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
    def _read_band(
        self,
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            pixel_size (Union[tuple, list, float]): Size of the pixels of the wanted band, in dataset unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        return utils.read(
            band_path,
            pixel_size=pixel_size,
            size=size,
            resampling=Resampling.bilinear,
            indexes=[self.bands[band].id],
            as_type=np.float32,
            **kwargs,
        )

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        bands = types.make_iterable(bands)

        if pixel_size is None and size is not None:
            pixel_size = self._pixel_size_from_img_size(size)

        band_paths = self.get_band_paths(bands, pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band_name, band_path in band_paths.items():
            band_arrays[band_name] = self._read_band(
                band_path, band=band_name, pixel_size=pixel_size, size=size, **kwargs
            )

        return band_arrays

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (149.148155074489, 32.6627897525474)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Sun angles
        sun_az = self.kwargs.get(CustomFields.SUN_AZ.value)
        sun_zen = self.kwargs.get(CustomFields.SUN_ZEN.value)

        return sun_az, sun_zen

    def _compute_hillshade(
        self,
        dem_path: str = "",
        pixel_size: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
    ) -> AnyPathType:
        """
        Compute Hillshade mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            pixel_size (Union[float, tuple]): Pixel size in meters. If not specified, use the product pixel size.
            resampling (Resampling): Resampling method
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
        Returns:
            AnyPathType: Hillshade mask path
        """
        sun_az, sun_zen = self.get_mean_sun_angles()
        if sun_az is not None and sun_zen is not None:
            # Warp DEM
            warped_dem_path = self._warp_dem(dem_path, pixel_size, size, resampling)

            # Get Hillshade path
            hillshade_name = (
                f"{self.condensed_name}_HILLSHADE_{path.get_filename(dem_path)}.tif"
            )

            hillshade_path, hillshade_exists = self._get_out_path(hillshade_name)
            if hillshade_exists:
                LOGGER.debug(
                    "Already existing hillshade DEM for %s. Skipping process.",
                    self.name,
                )
            else:
                LOGGER.debug("Computing hillshade DEM for %s", self.name)

                # Compute hillshade
                hillshade = rasters.hillshade(warped_dem_path, sun_az, sun_zen)
                utils.write(hillshade, hillshade_path)

        else:
            raise InvalidProductError(
                f"You should provide {CustomFields.SUN_AZ.value} and {CustomFields.SUN_ZEN.value} data to compute hillshade!"
            )

        return hillshade_path

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        """
        # TODO ?
        return False

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_{constellation}_{product_type}).

        Returns:
            str: Condensed name
        """
        const = (
            self.constellation
            if isinstance(self.constellation, str)
            else self.constellation.name
        )
        return f"{self.get_datetime()}_{const}_{self.product_type}"

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        # Parsing global attributes
        global_attr_names = CustomFields.list_values()

        # Create XML attributes
        global_attr = []
        for attr in global_attr_names:
            if attr == CustomFields.BAND_MAP.value:
                str_attr = str(
                    {
                        key.name: val.id
                        for key, val in self.bands.items()
                        if val is not None
                    }
                )
            elif hasattr(self, attr):
                # Get it formatted
                val = getattr(self, attr)
                if isinstance(val, ListEnum):
                    str_attr = val.value
                elif isinstance(val, datetime):
                    str_attr = val.isoformat()
                else:
                    str_attr = str(val)
            else:
                str_attr = str(self.kwargs.get(attr))

            global_attr.append(E(attr, str_attr))

        mtd = E.custom_metadata(*global_attr)
        mtd_el = etree.fromstring(
            etree.tostring(
                mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
        )

        return mtd_el, {}

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
        od = self.kwargs.get(CustomFields.ORBIT_DIR.value)
        if od is not None:
            od = OrbitDirection.from_value(od)

        return od

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
        return xarr

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        return []
