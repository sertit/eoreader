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
""" Product, superclass of all EOReader satellites products """
# pylint: disable=W0107
from __future__ import annotations

import datetime as dt
import functools
import gc
import logging
import os
import platform
import tempfile
from abc import abstractmethod
from enum import unique
from io import BytesIO
from pathlib import Path
from typing import Callable, Union
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import rasterio
import validators
import xarray as xr
from affine import Affine
from cloudpathlib import AnyPath, CloudPath
from lxml import etree, html
from rasterio import transform, warp
from rasterio.crs import CRS
from rasterio.enums import Resampling
from sertit import files, rasters, strings
from sertit.misc import ListEnum
from sertit.snap import MAX_CORES

from eoreader import cache, utils
from eoreader.bands import (
    DEM,
    HILLSHADE,
    SLOPE,
    BandNames,
    indices,
    is_clouds,
    is_dem,
    is_index,
    is_sat_band,
    to_band,
    to_str,
)
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER, DEM_PATH
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.keywords import DEM_KW, HILLSHADE_KW, SLOPE_KW
from eoreader.reader import Constellation, Reader
from eoreader.stac import StacItem
from eoreader.utils import EOREADER_NAME, simplify

LOGGER = logging.getLogger(EOREADER_NAME)
PRODUCT_FACTORY = Reader()


@unique
class SensorType(ListEnum):
    """
    Sensor type of the products, optical or SAR
    """

    OPTICAL = "Optical"
    """For optical data"""

    SAR = "SAR"
    """For SAR data"""


@unique
class OrbitDirection(ListEnum):
    """
    Orbit Direction
    """

    ASCENDING = "ASCENDING"
    """Ascending sensing orbit direction"""

    DESCENDING = "DESCENDING"
    """Descending sensing orbit direction"""


class Product:
    """Super class of EOReader Products"""

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.needs_extraction = True
        """Does this products needs to be extracted to be processed ? (:code:`True` by default)."""

        self.path = AnyPath(product_path)
        """Usable path to the product, either extracted or archived path, according to the satellite."""

        self.filename = files.get_filename(self.path)
        """Product filename"""

        self._use_filename = False
        self.name = None
        """Product true name (as specified in the metadata)"""

        self.split_name = None
        """
        Split name, to retrieve every information from its true name (dates, tile, product type...).
        """

        self.archive_path = AnyPath(archive_path) if archive_path else self.path
        """Archive path, same as the product path if not specified.
        Useful when you want to know where both the extracted and archived version of your product are stored."""

        self.is_archived = self.path.is_file()
        """ Is the archived product is processed
        (a products is considered as archived if its products path is a directory)."""

        # The output will be given later
        self._tmp_output = None
        self._output = None
        self._remove_tmp_process = remove_tmp

        # Get the products date and datetime
        self.date = None
        """Acquisition date."""

        self.datetime = None
        """Acquisition datetime."""

        self.tile_name = None
        """Tile if possible (for data that can be piled, for example S2 and Landsats)."""

        self.sensor_type = None
        """Sensor type, SAR or optical."""

        self.product_type = None
        """Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."""

        self.instrument = None
        """Product instrument, such as MSI for Sentinel-2 data."""

        self.bands = None
        """
        Band mapping between band wrapping names such as
        :code:`GREEN` and band real number such as :code:`03` for Sentinel-2.
        """

        self.is_reference = False
        """If the product is a reference, used for algorithms that need pre and post data, such as fire detection."""

        self.corresponding_ref = []
        """The corresponding reference products to the current one
         (if the product is not a reference but has a reference data corresponding to it).
         A list because of multiple ref in case of non-stackable products (S3, S1...)"""

        self.nodata = -9999
        """ Product nodata, set to -9999 by default """

        # Mask values
        self._mask_true = 1
        self._mask_false = 0
        self._mask_nodata = 255

        self.constellation = kwargs.get("constellation")
        """Product constellation, such as Sentinel-2"""

        # Set the resolution, needs to be done when knowing the product type
        self.resolution = None
        """
        Default resolution in meters of the current product.
        For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles.
        """

        self.condensed_name = None
        """
        Condensed name, the filename with only useful data to keep the name unique
        (ie. :code:`20191215T110441_S2_30TXP_L2A_122756`).
        Used to shorten names and paths.
        """

        self.constellation_id = None
        """Constellation ID, i.e. :code:`S2` for :code:`Sentinel-2`"""

        self.is_ortho = True
        """True if the images are orthorectified and the footprint is retrieved easily."""

        self._stac = None

        # Manage output
        if output_path:
            self._tmp_output = None
            self._output = AnyPath(output_path)
        else:
            self._tmp_output = tempfile.TemporaryDirectory()
            self._output = AnyPath(self._tmp_output.name)

        # Pre initialization
        self._pre_init(**kwargs)

        # Only compute data if OK (for now OK is extracted if needed)
        if self.is_archived and self.needs_extraction:
            LOGGER.warning(f"{self.filename} needs to be extracted to be used !")
        else:
            # Get the product real name
            self.name = self._get_name()
            self.split_name = self._get_split_name()

            # Get the products date and datetime
            self.datetime = self.get_datetime(as_datetime=True)
            self.date = self.get_date(as_date=True)

            # Constellation and satellite ID
            if not self.constellation:
                self.constellation = self._get_constellation()
            self.constellation_id = (
                self.constellation
                if isinstance(self.constellation, str)
                else self.constellation.name
            )
            self._set_instrument()

            # Post initialization
            self._post_init(**kwargs)

            # Set product type, needs to be done after the post-initialization
            self._set_product_type()

            # Set the resolution, needs to be done when knowing the product type
            self.resolution = self._get_resolution()

            self._map_bands()

            # Condensed name
            self.condensed_name = self._get_condensed_name()

            # Temporary files path (private)
            self._tmp_process = self._output.joinpath(f"tmp_{self.condensed_name}")
            os.makedirs(self._tmp_process, exist_ok=True)

    def __del__(self):
        """Cleaning up _tmp directory"""
        self.clear()

        # -- Remove temp folders
        if self._tmp_output:
            self._tmp_output.cleanup()

        elif self._remove_tmp_process:
            files.remove(self._tmp_process)

    @abstractmethod
    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        raise NotImplementedError

    @abstractmethod
    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        raise NotImplementedError

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
        raise NotImplementedError

    @cache
    @abstractmethod
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
        raise NotImplementedError

    @cache
    @abstractmethod
    def crs(self) -> CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_crs()
            CRS.from_epsg(32630)

        Returns:
            crs.CRS: CRS object
        """
        raise NotImplementedError

    @abstractmethod
    def _map_bands(self):
        """
        Map bands
        """
        raise NotImplementedError

    def _get_band_folder(self, writable: bool = False) -> Union[CloudPath, Path]:
        """
        Manage the case of CI SNAP Bands

        Returns:
            Union[CloudPath, Path]: Band folder
        """
        band_folder = self._tmp_process

        # Manage CI bands (when we do not write anything, read only)
        if not writable:
            ci_band_folder = os.environ.get(CI_EOREADER_BAND_FOLDER)
            if ci_band_folder:
                ci_band_folder = AnyPath(ci_band_folder)
                if ci_band_folder.is_dir():
                    # If we need a writable directory, check it
                    band_folder = ci_band_folder

        return band_folder

    @abstractmethod
    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        raise NotImplementedError

    @abstractmethod
    def _set_product_type(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError

    @abstractmethod
    def _set_instrument(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError

    @classmethod
    def _get_constellation(cls) -> Constellation:
        class_module = cls.__module__.split(".")[-1]
        constellation_id = class_module.replace("_product", "").upper()
        return getattr(Constellation, constellation_id)

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        if (
            self._use_filename
            and self.constellation
            and Reader().valid_name(self.path, self.constellation)
        ):
            name = self.filename
        else:
            name = self._get_name_constellation_specific()

        return name

    @abstractmethod
    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        raise NotImplementedError

    @abstractmethod
    def _get_condensed_name(self) -> str:
        """
        Set product condensed name.

        Returns:
            str: Condensed name
        """
        raise NotImplementedError

    def _get_split_name(self) -> list:
        """
        Get split name (erasing empty strings in it by precaution, especially for S1 and S3 data)

        Returns:
            list: Split products name
        """
        return utils.get_split_name(self.name)

    @abstractmethod
    def get_datetime(self, as_datetime: bool = False) -> Union[str, dt.datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 8, 24, 11, 6, 31)
            >>> prod.get_datetime(as_datetime=False)
            '20200824T110631'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        raise NotImplementedError

    def get_date(self, as_date: bool = False) -> Union[str, dt.date]:
        """
        Get the product's acquisition date.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_date(as_date=True)
            datetime.datetime(2020, 8, 24, 0, 0)
            >>> prod.get_date(as_date=False)
            '20200824'

        Args:
            as_date (bool): Return the date as a datetime.date. If false, returns a string.

        Returns:
            str: Its acquisition date
        """
        date = self.get_datetime().split("T")[0]

        if as_date:
            date = strings.str_to_date(date, date_format="%Y%m%d")

        return date

    @abstractmethod
    def get_default_band_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get default band path (among the existing ones).

        Usually :code:`GREEN` band for optical data and the first existing one between :code:`VV` and :code:`HH` for SAR data.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band_path()
            'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'

        Args:
            kwargs: Additional arguments

        Returns:
            Union[CloudPath, Path]: Default band path
        """
        raise NotImplementedError

    @abstractmethod
    def get_default_band(self) -> BandNames:
        """
        Get default band:
        Usually :code:`GREEN` band for optical data and the first existing one between :code:`VV` and :code:`HH` for SAR data.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band()
            <SpectralBandNames.GREEN: 'GREEN'>


        Returns:
            str: Default band
        """
        raise NotImplementedError

    @abstractmethod
    def get_existing_bands(self) -> list:
        """
        Return the existing bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_existing_bands()
            [<SpectralBandNames.CA: 'COASTAL_AEROSOL'>,
            <SpectralBandNames.BLUE: 'BLUE'>,
            <SpectralBandNames.GREEN: 'GREEN'>,
            <SpectralBandNames.RED: 'RED'>,
            <SpectralBandNames.VRE_1: 'VEGETATION_RED_EDGE_1'>,
            <SpectralBandNames.VRE_2: 'VEGETATION_RED_EDGE_2'>,
            <SpectralBandNames.VRE_3: 'VEGETATION_RED_EDGE_3'>,
            <SpectralBandNames.NIR: 'NIR'>,
            <SpectralBandNames.NNIR: 'NARROW_NIR'>,
            <SpectralBandNames.WV: 'WATER_VAPOUR'>,
            <SpectralBandNames.CIRRUS: 'CIRRUS'>,
            <SpectralBandNames.SWIR_1: 'SWIR_1'>,
            <SpectralBandNames.SWIR_2: 'SWIR_2'>]

        Returns:
            list: List of existing bands in the products
        """
        raise NotImplementedError

    @abstractmethod
    def get_existing_band_paths(self) -> dict:
        """
        Return the existing band paths (orthorectified if needed).

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_existing_band_paths()
            {
                <SpectralBandNames.CA: 'COASTAL_AEROSOL'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',
                ...,
                <SpectralBandNames.SWIR_2: 'SWIR_2'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2'
            }

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the raw band paths.

        Args:
            kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        return self.get_existing_band_paths()

    @abstractmethod
    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',
                <SpectralBandNames.RED: 'RED'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError

    @abstractmethod
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        raise NotImplementedError

    def _read_mtd_xml(
        self, mtd_from_path: str, mtd_archived: str = None
    ) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dicts as a dict

        Args:
            mtd_from_path (str): Metadata regex (glob style) to find from extracted product
            mtd_archived (str): Metadata regex (re style) to find from archived product

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces

        """
        try:
            if self.is_archived:
                root = files.read_archived_xml(self.path, f".*{mtd_archived}")
            else:
                try:
                    try:
                        mtd_file = next(self.path.glob(f"**/*{mtd_from_path}"))
                    except ValueError:
                        mtd_file = next(self.path.glob(f"*{mtd_from_path}"))

                    if isinstance(mtd_file, CloudPath):
                        try:
                            # Try using read_text (faster)
                            root = etree.fromstring(mtd_file.read_text())
                        except ValueError:
                            # Try using read_bytes
                            # Slower but works with:
                            # {ValueError}Unicode strings with encoding declaration are not supported.
                            # Please use bytes input or XML fragments without declaration.
                            root = etree.fromstring(mtd_file.read_bytes())
                    else:
                        # pylint: disable=I1101:
                        # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                        xml_tree = etree.parse(str(mtd_file))
                        root = xml_tree.getroot()
                except StopIteration as ex:
                    raise InvalidProductError(
                        f"Metadata file ({mtd_from_path}) not found in {self.path}"
                    ) from ex
        except etree.XMLSyntaxError:
            raise InvalidProductError(f"Invalid metadata XML for {self.path}!")

        # Get namespaces map (only useful ones)
        nsmap = {key: f"{{{ns}}}" for key, ns in root.nsmap.items()}
        pop_list = ["xsi", "xs", "xlink"]
        for ns in pop_list:
            if ns in nsmap.keys():
                nsmap.pop(ns)

        return root, nsmap

    def _read_mtd_html(
        self, mtd_from_path: str, mtd_archived: str = None
    ) -> html.HtmlElement:
        """
        Read metadata and outputs the metadata HTML root

        Args:
            mtd_from_path (str): Metadata regex (glob style) to find from extracted product
            mtd_archived (str): Metadata regex (re style) to find from archived product

        Returns:
            (html.HtmlElement, dict): Metadata HTML root and its namespaces

        """
        if self.is_archived:
            root = files.read_archived_html(self.path, f".*{mtd_archived}")
        else:
            try:
                mtd_file = next(self.path.glob(f"**/*{mtd_from_path}"))
                if isinstance(mtd_file, CloudPath):
                    try:
                        # Try using read_text (faster)
                        root = html.fromstring(mtd_file.read_text())
                    except ValueError:
                        # Try using read_bytes
                        # Slower but works with:
                        # {ValueError}Unicode strings with encoding declaration are not supported.
                        # Please use bytes input or XML fragments without declaration.
                        root = html.fromstring(mtd_file.read_bytes())
                else:
                    # pylint: disable=I1101:
                    # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                    html_tree = html.parse(str(mtd_file))
                    root = html_tree.getroot()
            except StopIteration as ex:
                raise InvalidProductError(
                    f"Metadata file ({mtd_from_path}) not found in {self.path}"
                ) from ex

        return root

    def read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element product at 0x1832895d788>, '')

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        return self._read_mtd()

    # pylint: disable=W0613
    @abstractmethod
    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            For optical data, invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        raise NotImplementedError

    @abstractmethod
    def _load_bands(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

    def _load_dem(
        self,
        band_list: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            band_list (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        dem_bands = {}
        if band_list:
            dem_path = os.environ.get(DEM_PATH)  # We already checked if it exists
            for band in band_list:
                assert is_dem(band)
                if band == DEM:
                    path = self._warp_dem(
                        kwargs.get(DEM_KW, dem_path),
                        resolution=resolution,
                        size=size,
                        **kwargs,
                    )
                elif band == SLOPE:
                    path = self._compute_slope(
                        kwargs.get(SLOPE_KW, dem_path),
                        resolution=resolution,
                        size=size,
                    )
                elif band == HILLSHADE:
                    path = self._compute_hillshade(
                        kwargs.get(HILLSHADE_KW, dem_path),
                        resolution=resolution,
                        size=size,
                    )
                else:
                    raise InvalidTypeError(f"Unknown DEM band: {band}")

                dem_bands[band] = utils.read(
                    path, resolution=resolution, size=size
                ).astype(np.float32)

        return dem_bands

    def load(
        self,
        bands: Union[list, BandNames, Callable],
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Open the bands and compute the wanted index.

        - For Optical data:
            The bands will be purged of nodata and invalid pixels (if specified with the CLEAN_OPTICAL keyword),
            the nodata will be set to -9999 and the bands will be DataArrays in float32.

        - For SAR data:
            The bands will be purged of nodata (not over the sea),
            the nodata will be set to 0 to respect SNAP's behavior and the bands will be DataArray in float32.

        Bands that come out this function at the same time are collocated and therefore have the same shapes.
        This can be broken if you load data separately. Its is best to always load DEM data with some real bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> bands = prod.load([GREEN, NDVI], resolution=20)

        Args:
            bands (Union[list, BandNames, Callable]): Band list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            dict: {band_name, band xarray}
        """

        # Check if all bands are valid
        bands = to_band(bands)

        for band in bands:
            try:
                band_name = band.value
            except AttributeError:
                band_name = band
            assert self.has_band(band), f"{self.name} has not a {band_name} band."

        if not resolution and not size:
            resolution = self.resolution

        # Load bands (only once ! and convert the bands to be loaded to correct format)
        unique_bands = list(set(to_band(bands)))
        band_dict = self._load(unique_bands, resolution, size, **kwargs)

        # Manage the case of arrays of different size -> collocate arrays if needed
        band_dict = self._collocate_bands(band_dict)

        # Convert to xarray dataset when all the bands have the same size
        # TODO: cannot convert as we have non-string index
        # xds = xr.Dataset(band_dict)

        # Sort bands to the asked order
        # xds.reindex({"band": bands})

        # Rename all bands and add attributes
        for key, val in band_dict.items():
            band_dict[key] = self._update_attrs(val, key, **kwargs)

        return band_dict

    @abstractmethod
    def _load(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Core function loading data bands

        Args:
            bands (list): Band list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

    def has_band(self, band: Union[BandNames, Callable]) -> bool:
        """
        Does this products has the specified band ?

        By band, we mean:

        - satellite band
        - index
        - DEM band
        - cloud band

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_band(GREEN)
            True
            >>> prod.has_band(TIR_2)
            False
            >>> prod.has_band(NDVI)
            True
            >>> prod.has_band(SHADOWS)
            False
            >>> prod.has_band(HILLSHADE)
            True

        Args:
            band (Union[BandNames, Callable]): EOReader band (optical, SAR, clouds, DEM)

        Returns:
            bool: True if the products has the specified band
        """
        if is_dem(band):
            if self.sensor_type == SensorType.SAR and band == HILLSHADE:
                has_band = False
            else:
                has_band = True
        elif is_clouds(band):
            has_band = self._has_cloud_band(band)
        elif is_index(band):
            has_band = self._has_index(band)
        else:
            has_band = band in self.get_existing_bands()

        return has_band

    def has_bands(self, bands: Union[list, BandNames, Callable]) -> bool:
        """
        Does this products has the specified bands ?

        By band, we mean:

        - satellite band
        - index
        - DEM band
        - cloud band

        See :code:`has_bands` for a code example.

        Args:
            bands (Union[list, BandNames, Callable]): EOReader bands (optical, SAR, clouds, DEM)

        Returns:
            bool: True if the products has the specified band
        """
        if not isinstance(bands, list):
            bands = [bands]

        return all([self.has_band(band) for band in set(bands)])

    @abstractmethod
    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_cloud_band(CLOUDS)
            True
        """
        raise NotImplementedError

    def _has_index(self, idx: Callable) -> bool:
        """
        Cen the specified index be computed from this products ?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_index(NDVI)
            True

        Args:
            idx (Callable): Index

        Returns:
            bool: True if the specified index can be computed with this product's bands
        """
        index_bands = indices.get_needed_bands(idx)
        return all(np.isin(index_bands, self.get_existing_bands()))

    def __gt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired after the other

        """
        return self.date > other.date

    def __ge__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired after or in the same time than the other

        """
        return self.date >= other.date

    def __eq__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired in the same time than the other

        """
        return self.date == other.date

    def __ne__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired not in the same time than the other

        """
        return self.date != other.date

    def __le__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired before or in the same time than the other

        """
        return self.date <= other.date

    def __lt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired before the other

        """
        return self.date < other.date

    def __hash__(self):
        return hash(self.condensed_name)

    @property
    def output(self) -> Union[CloudPath, Path]:
        """Output directory of the product, to write orthorectified data for example."""
        return self._output

    @output.setter
    def output(self, value: str):
        """Output directory of the product, to write orthorectified data for example."""
        # Remove old output if existing
        if self._tmp_output:
            self._tmp_output.cleanup()
            self._tmp_output = None

        if self._output.exists() and self._remove_tmp_process:
            files.remove(self._tmp_process)

        # Set the new output
        self._output = AnyPath(value)
        if not isinstance(self._output, CloudPath):
            self._output = self._output.resolve()

        self._tmp_process = self._output.joinpath(f"tmp_{self.condensed_name}")
        os.makedirs(self._tmp_process, exist_ok=True)

    @property
    def stac(self) -> StacItem:
        if not self._stac:
            self._stac = StacItem(self)

        return self._stac

    def _warp_dem(
        self,
        dem_path: str = "",
        resolution: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
        **kwargs,
    ) -> str:
        """
        Get this products DEM, warped to this products footprint and CRS.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.warp_dem(resolution=20)  # In meters
            '/path/to/20200824T110631_S2_T30TTK_L1C_150432_DEM.tif'

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters. If not specified, use the product resolution.
            resampling (Resampling): Resampling method
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            str: DEM path (as a VRT)
        """
        dem_name = f"{self.condensed_name}_DEM_{files.get_filename(dem_path)}.tif"
        warped_dem_path = self._get_band_folder().joinpath(dem_name)
        if warped_dem_path.is_file():
            LOGGER.debug(
                "Already existing DEM for %s. Skipping process.", self.condensed_name
            )
        else:
            warped_dem_path = self._get_band_folder(writable=True).joinpath(dem_name)
            LOGGER.debug("Warping DEM for %s", self.condensed_name)

            # Allow S3 HTTP Urls only on Linux because rasterio bugs on Windows
            if validators.url(dem_path) and platform.system() == "Windows":
                raise OSError(
                    f"URLs to DEM like {dem_path} are not supported on Windows! Use Docker or Linux instead"
                )

            # Check existence (SRTM)
            if not validators.url(dem_path):
                dem_path = AnyPath(dem_path)
                if not dem_path.is_file():
                    raise FileNotFoundError(f"DEM file does not exist here: {dem_path}")

            # Reproject DEM into products CRS
            LOGGER.debug("Using DEM: %s", dem_path)
            def_tr, def_w, def_h, def_crs = self.default_transform(**kwargs)
            with rasterio.open(str(dem_path)) as dem_ds:
                # Get adjusted transform and shape (with new resolution)
                if size is not None and resolution is None:
                    try:

                        # Get destination transform
                        out_h = size[1]
                        out_w = size[0]

                        # Get destination transform
                        coeff_x = def_w / out_w
                        coeff_y = def_h / out_h
                        dst_tr = def_tr
                        dst_tr *= dst_tr.scale(coeff_x, coeff_y)

                    except (TypeError, KeyError):
                        raise ValueError(
                            f"Size should exist (as resolution is None)"
                            f" and castable to a list: {size}"
                        )

                else:
                    # Refine resolution
                    if resolution is None:
                        resolution = self.resolution

                    bounds = transform.array_bounds(def_h, def_w, def_tr)
                    dst_tr, out_w, out_h = warp.calculate_default_transform(
                        def_crs,
                        self.crs(),
                        def_w,
                        def_h,
                        *bounds,
                        resolution=resolution,
                    )

                # Get empty output
                reprojected_array = np.zeros(
                    (dem_ds.count, out_h, out_w), dtype=np.float32
                )

                # Write reprojected DEM: here do not use utils.write()
                out_meta = {
                    "driver": "GTiff",
                    "dtype": reprojected_array.dtype,
                    "nodata": self.nodata,
                    "width": out_w,
                    "height": out_h,
                    "count": dem_ds.count,
                    "crs": self.crs(),
                    "transform": dst_tr,
                }
                with rasterio.open(str(warped_dem_path), "w", **out_meta) as out_dst:
                    out_dst.write(reprojected_array)

                    # Reproject
                    warp.reproject(
                        source=rasterio.band(dem_ds, range(1, dem_ds.count + 1)),
                        destination=rasterio.band(out_dst, range(1, out_dst.count + 1)),
                        resampling=resampling,
                        num_threads=MAX_CORES,
                        dst_transform=dst_tr,
                        dst_crs=self.crs(),
                        src_crs=dem_ds.crs,
                        src_transform=dem_ds.transform,
                    )

        return warped_dem_path

    @abstractmethod
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
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            resampling (Resampling): Resampling method

        Returns:
            str: Hillshade mask path

        """
        raise NotImplementedError

    def _compute_slope(
        self,
        dem_path: str = "",
        resolution: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
    ) -> str:
        """
        Compute slope mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters. If not specified, use the product resolution.
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            resampling (Resampling): Resampling method

        Returns:
            str: Slope mask path

        """
        # Warp DEM
        warped_dem_path = self._warp_dem(dem_path, resolution, size, resampling)

        # Get slope path
        slope_name = f"{self.condensed_name}_SLOPE_{files.get_filename(dem_path)}.tif"
        slope_path = self._get_band_folder().joinpath(slope_name)
        if slope_path.is_file():
            LOGGER.debug(
                "Already existing slope DEM for %s. Skipping process.",
                self.condensed_name,
            )
        else:
            slope_path = self._get_band_folder(writable=True).joinpath(slope_name)
            LOGGER.debug("Computing slope for %s", self.condensed_name)

            # Compute slope
            slope = rasters.slope(warped_dem_path)
            utils.write(slope, slope_path)

        return slope_path

    @staticmethod
    def _collocate_bands(bands: dict, master_xds: xr.DataArray = None) -> dict:
        """
        Collocate all bands from a dict if needed (if a raster shape is different)

        Args:
            bands (dict): Dict of bands to collocate if needed
            master_xds (xr.DataArray): Master array

        Returns:
            dict: Collocated bands
        """
        for band_id, band in bands.items():
            if master_xds is None:
                master_xds = band  # Master array is the first one in this case

            if band.shape != master_xds.shape:
                bands[band_id] = rasters.collocate(
                    master_xds=master_xds, slave_xds=band
                )

            bands[band_id] = bands[band_id].assign_coords(
                {
                    "x": master_xds.x,
                    "y": master_xds.y,
                }
            )  # Bug for now, tiny difference in coords

        return bands

    # pylint: disable=R0913
    # Too many arguments (6/5)
    def stack(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        stack_path: Union[str, CloudPath, Path] = None,
        save_as_int: bool = False,
        **kwargs,
    ) -> xr.DataArray:
        """
        Stack bands and index of a products.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  # In meters

        Args:
            bands (list): Bands and index combination
            resolution (float): Stack resolution. . If not specified, use the product resolution.
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            stack_path (Union[str, CloudPath, Path]): Stack path
            save_as_int (bool): Convert stack to uint16 to save disk space (and therefore multiply the values by 10.000)
            **kwargs: Other arguments passed to :code:`load` or :code:`rioxarray.to_raster()` (such as :code:`compress`)

        Returns:
            xr.DataArray: Stack as a DataArray
        """
        if not isinstance(bands, list):
            bands = [bands]

        # Ensure the bands are not in strings (otherwise will bug in Dataset conversion)
        bands = to_band(bands)

        if not resolution and not size:
            resolution = self.resolution

        # Create the analysis stack
        band_dict = self.load(bands, resolution=resolution, size=size, **kwargs)

        # Convert into dataset with str as names
        LOGGER.debug("Creating dataset")
        data_vars = {}
        coords = band_dict[bands[0]].coords
        for key in bands:
            data_vars[to_str(key)[0]] = (
                band_dict[key].coords.dims,
                band_dict[key].data,
            )

            # Set memory free (for big stacks)
            band_dict[key].close()
            band_dict[key] = None

        # Create dataset
        stack = xr.Dataset(
            data_vars=data_vars,
            coords=coords,
        )

        # Force nodata
        LOGGER.debug("Stacking")
        stack = stack.to_stacked_array(new_dim="z", sample_dims=("x", "y"))
        stack = stack.transpose("z", "y", "x")

        # Save as integer
        dtype = np.float32
        if save_as_int:
            if np.min(stack) < 0:
                LOGGER.warning(
                    "Cannot convert the stack to uint16 as it has negative values. Keeping it in float32."
                )
            else:
                # SCALING
                # NOT ALL bands need to be scaled, only:
                # - Satellite bands
                # - index
                for b_id, band in enumerate(bands):
                    if is_sat_band(band) or is_index(band):
                        stack[b_id, ...] = stack[b_id, ...] * 10000

                # CONVERSION
                dtype = np.uint16
                nodata = kwargs.get("nodata", 65535)  # Can be 0
                stack = stack.fillna(nodata).astype(
                    dtype
                )  # Scale to uint16, fill nan and convert to uint16

        if dtype == np.float32:
            # Convert dtype if needed
            if stack.dtype != dtype:
                stack = stack.astype(dtype)

            # Set nodata if needed
            if stack.rio.encoded_nodata != self.nodata:
                stack = stack.rio.write_nodata(
                    self.nodata, encoded=True, inplace=True
                )  # NaN values are already set

        # Update stack's attributes
        stack = self._update_attrs(stack, bands, **kwargs)

        # Write on disk
        LOGGER.debug("Saving stack")
        if stack_path:
            stack_path = AnyPath(stack_path)
            if not stack_path.parent.exists():
                os.makedirs(str(stack_path.parent), exist_ok=True)
            utils.write(stack, stack_path, dtype=dtype, **kwargs)

        return stack

    @abstractmethod
    def _update_attrs_constellation_specific(
        self, xarr: xr.DataArray, bands: list, **kwargs
    ) -> xr.DataArray:
        """
        Update attributes of the given array (constellation specific)

        Args:
            xarr (xr.DataArray): Array whose attributes need an update
            bands (list): Array name (as a str or a list)
        """
        raise NotImplementedError

    def _update_attrs(self, xarr: xr.DataArray, bands: list, **kwargs) -> xr.DataArray:
        """
        Update attributes of the given array
        Args:
            xarr (xr.DataArray): Array whose attributes need an update
            bands (list): Bands
        Returns:
            xr.DataArray: Updated array
        """
        if not isinstance(bands, list):
            bands = [bands]
        long_name = to_str(bands)
        xr_name = "_".join(long_name)
        attr_name = " ".join(long_name)

        renamed_xarr = xarr.rename(xr_name)
        renamed_xarr.attrs["long_name"] = attr_name
        renamed_xarr.attrs["constellation"] = (
            self.constellation
            if isinstance(self.constellation, str)
            else self.constellation.value
        )
        renamed_xarr.attrs["constellation_id"] = self.constellation_id
        renamed_xarr.attrs["product_path"] = str(self.path)  # Convert to string
        renamed_xarr.attrs["product_name"] = self.name
        renamed_xarr.attrs["product_filename"] = self.filename
        renamed_xarr.attrs["instrument"] = (
            self.instrument
            if isinstance(self.instrument, str)
            else self.instrument.value
        )
        renamed_xarr.attrs["product_type"] = (
            self.product_type
            if isinstance(self.product_type, str)
            else self.product_type.value
        )
        renamed_xarr.attrs["acquisition_date"] = self.get_datetime(as_datetime=False)
        renamed_xarr.attrs["condensed_name"] = self.condensed_name
        od = self.get_orbit_direction()
        renamed_xarr.attrs["orbit_direction"] = od.value if od is not None else str(od)

        # kwargs attrs
        renamed_xarr = self._update_attrs_constellation_specific(
            renamed_xarr, bands, **kwargs
        )

        return renamed_xarr

    @staticmethod
    def _check_dem_path(bands: list, **kwargs) -> None:
        """
        Check if DEM is set and exists if DEM bands are asked.

        Args:
            bands (list): List of the wanted bands
            kwargs: Other arguments used to load bands
        """
        if DEM_PATH not in os.environ:
            if (
                (DEM in bands and DEM_KW not in kwargs)
                or (SLOPE in bands and SLOPE_KW not in kwargs)
                or (HILLSHADE in bands and HILLSHADE_KW not in kwargs)
            ):

                raise ValueError(
                    f"DEM path not set, unable to compute DEM bands! "
                    f"Please set the environment variable {DEM_PATH} or a DEM keyword."
                )
        else:
            dem_path = os.environ.get(DEM_PATH)
            # URLs and file paths are required
            if not validators.url(dem_path):
                dem_path = AnyPath(dem_path)
                if not dem_path.is_file():
                    raise FileNotFoundError(
                        f"{dem_path} is not a file! "
                        f"Please set the environment variable {DEM_PATH} to an existing file."
                    )

    @cache
    def default_transform(self, **kwargs) -> (Affine, int, int, CRS):
        """
        Returns default transform data of the default band (UTM),
        as the :code:`rasterio.warp.calculate_default_transform` does:
        - transform
        - width
        - height
        - crs

        Args:
            kwargs: Additional arguments
        Returns:
            Affine, int, int: transform, width, height

        """
        with rasterio.open(str(self.get_default_band_path(**kwargs))) as dst:
            return dst.transform, dst.width, dst.height, dst.crs

    def _resolution_from_size(self, size: Union[list, tuple] = None) -> tuple:
        """
        Compute the corresponding resolution to a given size (positive resolution)

        Args:
            size (Union[list, tuple]): Size

        Returns:
            tuple: Resolution as a tuple (x, y)
        """
        def_tr, def_w, def_h, def_crs = self.default_transform()
        bounds = transform.array_bounds(def_h, def_w, def_tr)

        # Manage WGS84 case
        if not def_crs.is_projected:
            utm_tr, utm_w, utm_h = warp.calculate_default_transform(
                def_crs,
                self.crs(),
                def_w,
                def_h,
                *bounds,
                resolution=self.resolution,
            )
            res_x = abs(utm_tr.a * utm_w / size[0])
            res_y = abs(utm_tr.e * utm_h / size[1])
        # Manage UTM case
        else:
            res_x = abs(def_tr.a * def_w / size[0])
            res_y = abs(def_tr.e * def_h / size[1])

        # Round resolution to the closest meter (under 1 meter, allow centimetric resolution)
        if res_x < 1.0:
            res_x = np.round(res_x, 1)
        else:
            res_x = np.round(res_x, 0)
        if res_y < 1.0:
            res_y = np.round(res_y, 1)
        else:
            res_y = np.round(res_y, 0)

        return res_x, res_y

    def clean_tmp(self):
        """
        Clean the temporary directory of the current product
        """
        if self._tmp_process.exists():
            for tmp_file in self._tmp_process.glob("*"):
                files.remove(tmp_file)

    def clear(self):
        """
        Clear this product's cache
        """
        # -- Delete all cached properties and functions
        gc.collect()

        # All objects collected
        objects = []
        for obj in gc.get_objects():
            try:
                if isinstance(obj, functools._lru_cache_wrapper):
                    objects.append(obj)
            except ReferenceError:
                pass

        # All objects cleared
        for obj in objects:
            obj.cache_clear()

    def _resolution_to_str(self, resolution: Union[float, tuple, list] = None):
        """
        Convert a resolution to a normalized string

        Args:
            resolution (Union[float, tuple, list]): Resolution

        Returns:
            str: Resolution as a string
        """

        def _res_to_str(res):
            return f"{abs(res):.2f}m".replace(".", "-")

        if resolution:
            if isinstance(resolution, (tuple, list)):
                res_x = _res_to_str(resolution[0])
                res_y = _res_to_str(resolution[1])
                if res_x == res_y:
                    res_str = res_x
                else:
                    res_str = f"{res_x}_{res_y}"
            else:
                res_str = _res_to_str(resolution)
        else:
            res_str = _res_to_str(self.resolution)

        return res_str

    def _to_repr(self) -> list:
        """
        Returns a representation of the product as a list

        Returns:
            list: Representation of the product
        """
        band_repr = "\n".join(
            [
                f"\t\t{band.value}: {val.id}"
                for band, val in self.bands.items()
                if val is not None
            ]
        )
        repr = [
            f"eoreader.{self.__class__.__name__} '{self.name}'",
            "Attributes:",
            f"\tcondensed_name: {self.condensed_name}",
            f"\tpath: {self.path}",
            f"\tconstellation: {self.constellation if isinstance(self.constellation, str) else self.constellation.value}",
            f"\tsensor type: {self.sensor_type if isinstance(self.sensor_type, str) else self.sensor_type.value}",
            f"\tproduct type: {self.product_type if isinstance(self.product_type, str) else self.product_type.value}",
            f"\tdefault resolution: {self.resolution}",
            f"\tacquisition datetime: {self.get_datetime(as_datetime=True).isoformat()}",
            f"\tband mapping:\n{band_repr}",
            f"\tneeds extraction: {self.needs_extraction}",
        ]

        return repr + self._to_repr_constellation_specific()

    @abstractmethod
    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        raise NotImplementedError

    def __repr__(self):
        return "\n".join(self._to_repr())

    def get_quicklook_path(self) -> Union[None, str]:
        """
        Get quicklook path if existing (no such thing for Sentinel-2)

        Returns:
            str: Quicklook path
        """
        LOGGER.debug(f"No quicklook available for {self.constellation.value} data!")
        return None

    def plot(self) -> None:
        """
        Plot the quicklook if existing
        """
        try:
            import matplotlib.pyplot as plt
            from PIL import Image
        except ModuleNotFoundError:
            LOGGER.warning("You need to install matplotlib to plot the product.")
        else:
            quicklook_path = self.get_quicklook_path()

            if quicklook_path is not None:
                if quicklook_path[:4].lower() in [".png", ".jpg"]:
                    plt.figure(figsize=(6, 6))
                    if quicklook_path.startswith("zip::"):
                        str_path = quicklook_path.replace("zip::", "")
                        zip_path, zip_name = str_path.split("!")
                        with ZipFile(zip_path, "r") as zip_ds:
                            with BytesIO(zip_ds.read(zip_name)) as bf:
                                plt.imshow(Image.open(bf))
                else:
                    qck = rasters.read(quicklook_path)
                    if qck.rio.count == 3:
                        plt.figure(figsize=(6, 6))
                        qck.plot.imshow(robust=True)
                    elif qck.rio.count == 1:
                        plt.figure(figsize=(7, 6))
                        qck.plot(cmap="GnBu_r", robust=True)
                    else:
                        pass

                plt.title(f"{self.condensed_name}")

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
        raise NotImplementedError
