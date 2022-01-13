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
""" Class for custom products """
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
from cloudpathlib import CloudPath
from lxml import etree
from lxml.builder import E
from rasterio import crs
from rasterio.enums import Resampling
from sertit import files, misc, rasters, vectors
from sertit.rasters import XDS_TYPE

from eoreader import cache, cached_property, utils
from eoreader.bands import (
    BandNames,
    OpticalBands,
    SarBands,
    is_clouds,
    is_dem,
    is_index,
    is_sat_band,
    to_band,
)
from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError
from eoreader.products.product import Product, SensorType
from eoreader.reader import Platform
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# -- CUSTOM FIELDS --
NAME = "name"
SENSOR_TYPE = "sensor_type"
ACQ_DATETIME = "acquisition_datetime"
BAND_MAP = "band_map"
PLATFORM = "platform"
DEF_RES = "default_resolution"
PROD_TYPE = "product_type"
SUN_AZ = "sun_azimuth"
SUN_ZEN = "sun_zenith"

# -- CUSTOM
CUSTOM = "CUSTOM"


class CustomProduct(Product):
    """Custom products"""

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.sun_az = None
        """Sun mean angles (azimuth)"""

        self.sun_zen = None
        """Sun mean angles (zenith)"""

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # -- Parse the kwargs
        misc.check_mandatory_keys(kwargs, [BAND_MAP, SENSOR_TYPE])

        # Sensor type
        self.sensor_type = SensorType.convert_from(kwargs[SENSOR_TYPE])[0]
        self.band_names = (
            OpticalBands() if self.sensor_type == SensorType.OPTICAL else SarBands()
        )

        # Band map
        band_names = kwargs[BAND_MAP]  # Shouldn't be empty
        assert isinstance(band_names, dict)
        band_names = {to_band(key)[0]: val for key, val in band_names.items()}
        assert [is_sat_band(band) for band in band_names.keys()]
        self.band_names.map_bands(band_names)

        # Test on the product
        with rasterio.open(str(self.get_default_band_path())) as ds:
            assert (
                len(band_names) == ds.count
            ), f"You should specify {ds.count} bands in band_map, not {len(band_names)} !"

        # Datetime
        self.datetime = kwargs.get(ACQ_DATETIME, datetime.now())
        if isinstance(self.datetime, str):
            try:
                self.datetime = datetime.fromisoformat(self.datetime)
            except ValueError:
                self.datetime = datetime.strptime(self.datetime, "%Y%m%dT%H%M%S")
        assert isinstance(self.datetime, datetime)

        # Sun angles
        self.sun_az = kwargs.get(SUN_AZ, None)
        self.sun_zen = kwargs.get(SUN_ZEN, None)

        # Others
        self.name = kwargs.get(NAME, files.get_filename(self.path))
        self.platform = Platform.convert_from(kwargs.get(PLATFORM, CUSTOM))[0]
        self.resolution = kwargs.get(DEF_RES, None)
        self.product_type = kwargs.get(PROD_TYPE, CUSTOM)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        pass

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        return self.name

    def get_datetime(self, as_datetime: bool = False) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        if as_datetime:
            date = self.datetime
        else:
            date = self.datetime.strftime(DATETIME_FMT)

        return date

    def _get_platform(self) -> Platform:
        return self.platform

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        if self.resolution is None:
            with rasterio.open(str(self.get_default_band_path())) as ds:
                return ds.res[0]

    def _set_product_type(self) -> None:
        """Set products type"""
        pass

    def get_default_band(self) -> BandNames:
        """
        Get default band: the first one of the stack

        Returns:
            str: Default band
        """
        return list(self.band_names.keys())[0]

    def get_default_band_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get default band path: the stack path.

        Args:
            kwargs: Additional arguments
        Returns:
            Union[CloudPath, Path]: Default band path
        """
        return self.path

    @cached_property
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of stack.

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # Get extent
        return rasters.get_extent(self.get_default_band_path()).to_crs(self.crs)

    @cached_property
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return rasters.get_footprint(
            self.get_default_band_path()
        )  # Processed by SNAP: the nodata is set

    @cached_property
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
            crs_str = vectors.corresponding_utm_projection(
                extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
            )
            raise InvalidProductError(
                "Only stacks with projected CRS can be processed! "
                f"Please reproject it to the corresponding UTM projection ({crs_str})!"
            )

        return def_crs

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Get the stack path for each asked band

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
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
        return self.path

    def get_existing_bands(self) -> list:
        """
        Get the bands of the stack.

        Returns:
            list: List of existing bands in the products
        """
        return [name for name, nb in self.band_names.items() if nb]

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
            Invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            XDS_TYPE: Band xarray

        """
        return utils.read(
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
            indexes=[self.band_names[band]],
            **kwargs,
        ).astype(np.float32)

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if not isinstance(bands, list):
            bands = [bands]

        if resolution is None and size is not None:
            resolution = self._resolution_from_size(size)

        band_paths = self.get_band_paths(bands, resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band_name, band_path in band_paths.items():
            band_arrays[band_name] = self._read_band(
                band_path, band=band_name, resolution=resolution, size=size, **kwargs
            )

        return band_arrays

    def _load(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Core function loading bands

        Args:
            bands (list): Band list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            Dictionary {band_name, band_xarray}
        """
        band_list = []
        dem_list = []
        for band in bands:
            if is_index(band):
                raise NotImplementedError(
                    "For now, no index is implemented for SAR data."
                )
            elif is_sat_band(band):
                if not self.has_band(band):
                    raise InvalidBandError(
                        f"{band} cannot be retrieved from {self.condensed_name}"
                    )
                else:
                    band_list.append(band)
            elif is_dem(band):
                dem_list.append(band)
            elif is_clouds(band):
                raise NotImplementedError(
                    f"Clouds cannot be retrieved from custom data ({self.condensed_name})."
                )
            else:
                raise InvalidTypeError(f"{band} is neither a band nor an index !")

        # Check if DEM is set and exists
        if dem_list:
            self._check_dem_path()

        # Load bands
        bands = self._load_bands(band_list, resolution=resolution, size=size, **kwargs)

        # Add DEM
        bands.update(
            self._load_dem(dem_list, resolution=resolution, size=size, **kwargs)
        )

        return bands

    def _compute_hillshade(
        self,
        dem_path: str = "",
        resolution: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
    ) -> str:
        """
        Compute Hillshade mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters. If not specified, use the product resolution.
            resampling (Resampling): Resampling method
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            str: Hillshade mask path
        """
        if self.sun_az is not None and self.sun_zen is not None:
            # Warp DEM
            warped_dem_path = self._warp_dem(dem_path, resolution, size, resampling)

            # Get Hillshade path
            hillshade_name = f"{self.condensed_name}_HILLSHADE.tif"
            hillshade_path = self._get_band_folder().joinpath(hillshade_name)
            if hillshade_path.is_file():
                LOGGER.debug(
                    "Already existing hillshade DEM for %s. Skipping process.",
                    self.name,
                )
            else:
                hillshade_path = self._get_band_folder(writable=True).joinpath(
                    hillshade_name
                )
                LOGGER.debug("Computing hillshade DEM for %s", self.name)

                # Compute hillshade
                hillshade = rasters.hillshade(
                    warped_dem_path, self.sun_az, self.sun_zen
                )
                utils.write(hillshade, hillshade_path)

        else:
            raise InvalidProductError(
                f"You should provide {SUN_AZ} and {SUN_ZEN} data to compute hillshade!"
            )

        return hillshade_path

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        # TODO ?
        return False

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_{platform}_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.product_type}"

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        # Parsing global attributes
        global_attr_names = [
            "name",
            "datetime",
            "sensor_type",
            "platform",
            "resolution",
            "product_type",
            "band_names",
            "sun_az",
            "sun_zen",
        ]

        # Create XML attributes
        global_attr = []
        for attr in global_attr_names:
            if hasattr(self, attr):
                if attr == "band_names":
                    str_attr = str(
                        {
                            key.name: val
                            for key, val in self.band_names.items()
                            if isinstance(val, int)
                        }
                    )
                else:
                    str_attr = str(getattr(self, attr))

                global_attr.append(E(attr, str_attr))

        mtd = E.custom_metadata(*global_attr)
        mtd_el = etree.fromstring(
            etree.tostring(
                mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
        )

        return mtd_el, {}
