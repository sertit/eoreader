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
"""Product, superclass of all EOReader satellites products"""

# pylint: disable=W0107
from __future__ import annotations

import contextlib
import datetime as dt
import functools
import gc
import logging
import os
import platform
import shutil
import tempfile
from abc import abstractmethod
from enum import unique
from io import BytesIO
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import validators
import xarray as xr
from affine import Affine
from lxml import etree, html
from rasterio import shutil as rio_shutil
from rasterio import transform, warp
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sertit import (
    AnyPath,
    files,
    logs,
    misc,
    path,
    rasters,
    strings,
    types,
    vectors,
    xml,
)
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    DEM,
    GREEN1,
    HILLSHADE,
    NEEDED_BANDS,
    SLOPE,
    BandNames,
    compute_index,
    indices,
    is_clouds,
    is_dem,
    is_index,
    is_sar_band,
    is_spectral_band,
    to_band,
    to_str,
)
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER, DEM_PATH
from eoreader.exceptions import (
    InvalidBandError,
    InvalidIndexError,
    InvalidProductError,
    InvalidTypeError,
    UnhandledArchiveError,
)
from eoreader.keywords import DEM_KW, HILLSHADE_KW, SLOPE_KW
from eoreader.reader import Constellation, Reader
from eoreader.stac import StacItem
from eoreader.utils import UINT16_NODATA, simplify

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

    UNKNOWN = "UNKNOWN"
    """Unknown orbit direction"""


class Product:
    """Super class of EOReader Products"""

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.needs_extraction = True
        """Does this product needs to be extracted to be processed ? (:code:`True` by default)."""

        self.path = AnyPath(product_path)
        """Usable path to the product, either extracted or archived path, according to the satellite."""

        self.filename = path.get_filename(self.path)
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

        self.constellation = kwargs.get(
            "constellation", self._get_constellation_dummy()
        )
        """Product constellation, such as Sentinel-2"""

        # Set the resolution, needs to be done when knowing the product type
        self.resolution = None
        """
        Default resolution in meters of the current product.
        For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles.
        """

        self.pixel_size = None
        """
        For SAR data, it is important to distinguish (square) pixel spacing from actual resolution.
        (see `this <https://natural-resources.canada.ca/maps-tools-and-publications/satellite-imagery-and-air-photos/tutorial-fundamentals-remote-sensing/satellites-and-sensors/spatial-resolution-pixel-size-and-scale/9407>` for more information).
        For optical data, those two terms have usually the same meaning (for a fully zoomed raster).
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

        self.is_stacked = False
        """True if the bands are stacked (like for VHR data)."""

        self._stac = None

        # Manage output
        if output_path:
            self._tmp_output = None
            self._output = AnyPath(output_path)
        else:
            self._tmp_output = tempfile.TemporaryDirectory()
            self._output = AnyPath(self._tmp_output.name)

        # Temporary file path (private)
        self._tmp_process = self._output.joinpath(f"tmp_{self.condensed_name}")
        os.makedirs(self._tmp_process, exist_ok=True)

        # Pre initialization
        self._pre_init(**kwargs)

        # Only compute data if OK (for now OK is extracted if needed)
        if self.is_archived and self.needs_extraction:
            raise UnhandledArchiveError(
                f"{self.filename} needs to be extracted to be used!"
            )
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
                if self.constellation is None:
                    raise InvalidProductError(
                        f"Impossible to set a constellation to the given product! {self.name}"
                    )

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

            # Set the pixel size, needs to be done when knowing the product type
            self._set_pixel_size()

            self._map_bands()

            # Condensed name
            self.condensed_name = self._get_condensed_name()

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

    def _get_band_folder(self, writable: bool = False) -> AnyPathType:
        """
        Manage the case of CI SNAP Bands

        Returns:
            AnyPathType: Band folder
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
    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
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
        return cls._get_constellation_dummy(raise_ex=True)

    @classmethod
    def _get_constellation_dummy(cls, raise_ex: bool = False) -> Constellation:
        try:
            class_module = cls.__module__.split(".")[-1]
            constellation_id = class_module.replace("_product", "").upper()
            const = getattr(Constellation, constellation_id)
        except AttributeError as ex:
            if raise_ex:
                raise ex
            else:
                const = None

        # In Dummy, don't set generic constellations!
        if const not in Constellation.get_real_constellations():
            const = None

        return const

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

    def _construct_band_path(
        self,
        band: BandNames,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        writable: bool = False,
        **kwargs,
    ) -> AnyPathType:
        """
        Get cloud band path.

        Args:
            band (BandNames): Wanted band
            pixel_size (float): Band pixel size in meters
            writable (bool): True if we want the band folder to be writeable
            kwargs: Additional arguments

        Returns:
            AnyPathType: Clean band path
        """
        # Manage pixel size
        if pixel_size is None:
            if size is not None:
                pixel_size = self._pixel_size_from_img_size(size)
            else:
                pixel_size = self.pixel_size

        # Convert to str
        res_str = self._pixel_size_to_str(pixel_size)

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{to_str(band)[0]}_{res_str.replace('.', '-')}.tif",
        )

    @abstractmethod
    def get_default_band_path(self, **kwargs) -> AnyPathType:
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
            AnyPathType: Default band path
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
        self, band_list: list, pixel_size: float = None, **kwargs
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
            pixel_size (float): Band pixel size (in meters)
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
                root = self._read_archived_xml(regex=f".*{mtd_archived}")
            else:
                try:
                    try:
                        mtd_file = next(self.path.glob(f"**/*{mtd_from_path}"))
                    except ValueError:
                        mtd_file = next(self.path.glob(f"*{mtd_from_path}"))

                    try:
                        root = xml.read(mtd_file)
                    except ValueError as ex:
                        raise InvalidProductError from ex
                except StopIteration as ex:
                    raise InvalidProductError(
                        f"Metadata file ({mtd_from_path}) not found in {self.path}"
                    ) from ex
        except etree.XMLSyntaxError as exc:
            raise InvalidProductError(f"Invalid metadata XML for {self.path}!") from exc

        # Get namespaces map (only useful ones)
        nsmap = {key: f"{{{ns}}}" for key, ns in root.nsmap.items()}
        pop_list = ["xsi", "xs", "xlink"]
        for ns in pop_list:
            if ns in nsmap:
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
            root = self._read_archived_html(f".*{mtd_archived}")
        else:
            try:
                mtd_file = next(self.path.glob(f"**/*{mtd_from_path}"))
                if path.is_cloud_path(mtd_file):
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

    @cache
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
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            For optical data, invalid pixels are not managed here

        Args:
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            pixel_size (Union[tuple, list, float]): Size of the pixels of the wanted band, in dataset unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        raise NotImplementedError

    def load(
        self,
        bands: Union[list, BandNames, str],
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.Dataset:
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
            >>> bands = prod.load([GREEN, NDVI], pixel_size=20)

        Args:
            bands (Union[list, BandNames, str]): Band list
            pixel_size (float): Pixel size of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands

        Returns:
            xr.Dataset: Dataset with a variable per band
        """
        if not pixel_size and "resolution" in kwargs:
            logs.deprecation_warning(
                "`resolution` is deprecated in favor of `pixel_size` to avoid confusion. `resolution` will be removed in a future release."
            )
            pixel_size = kwargs.pop("resolution")

        if (types.is_iterable(bands) and ("GREEN1" in bands or GREEN1 in bands)) or (
            bands == "GREEN1" or bands == GREEN1
        ):
            logs.deprecation_warning(
                "`GREEN1` is deprecated in favor of `GREEN_1`. `GREEN1` will be removed in a future release."
            )

        # Check if all bands are valid
        bands = self.to_band(bands)

        for band in bands:
            assert self.has_band(band), f"{self.name} has not a {to_str(band)[0]} band."

        # Load bands (only once ! and convert the bands to be loaded to correct format)
        unique_bands = misc.unique(bands)
        band_xds = self._load(unique_bands, pixel_size, size, **kwargs)

        # Rename all bands and add attributes
        for key, val in band_xds.items():
            band_xds[key] = self._update_attrs(val, key, **kwargs)

        # Update stack's attributes
        if len(band_xds) > 0:
            band_xds = self._update_attrs(band_xds, bands, **kwargs)

        return band_xds

    def _load(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.Dataset:
        """
        Core function loading optical data bands

        Args:
            bands (list): Band list
            pixel_size (float): Pixel size of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands

        Returns:
            xr.Dataset: Dataset with a variable per band
        """
        band_list = []
        index_list = []
        dem_list = []
        clouds_list = []

        # Check if everything is valid
        for band in bands:
            if is_index(band):
                if self._has_index(band):
                    if band in indices.DEPRECATED_SPECTRAL_INDICES:
                        logs.deprecation_warning(
                            "Aliases of Awesome Spectral Indices won't be available in future versions of EOReader. "
                            f"Please use {indices.DEPRECATED_SPECTRAL_INDICES[band]} instead of {band}"
                        )
                    index_list.append(band)
                else:
                    raise InvalidIndexError(
                        f"{band} cannot be computed from {self.condensed_name}."
                    )
            elif is_sar_band(band):
                if self.sensor_type == SensorType.SAR:
                    if not self.has_band(band):
                        raise InvalidBandError(
                            f"{band} cannot be retrieved from {self.condensed_name}"
                        )
                    else:
                        band_list.append(band)
                else:
                    raise TypeError(
                        f"You should ask for Optical bands as {self.name} is an optical product."
                    )
            elif is_spectral_band(band):
                if self.sensor_type == SensorType.OPTICAL:
                    if self.has_band(band):
                        band_list.append(band)
                    else:
                        raise InvalidBandError(
                            f"{band} cannot be retrieved from {self.condensed_name}."
                        )
                else:
                    raise TypeError(
                        f"You should ask for SAR bands as {self.name} is a SAR product."
                    )
            elif is_dem(band):
                dem_list.append(band)
            elif is_clouds(band):
                if self.sensor_type == SensorType.OPTICAL:
                    clouds_list.append(band)
                else:
                    raise TypeError(
                        f"You cannot ask for cloud bands as {self.name} is a SAR product."
                    )

        # Check if DEM is set and exists
        if dem_list:
            self._check_dem_path(bands, **kwargs)

        # Get all bands to be open
        bands_to_load = band_list.copy()
        for idx in index_list:
            bands_to_load += NEEDED_BANDS[idx]

        # Load band arrays (only keep unique bands: open them only one time !)
        unique_bands = misc.unique(bands_to_load)
        bands_dict = {}
        if unique_bands:
            LOGGER.debug(f"Loading bands {to_str(unique_bands)}")
            loaded_bands = self._load_bands(
                unique_bands, pixel_size=pixel_size, size=size, **kwargs
            )

            # Compute index (they conserve the nodata)
            if index_list:
                # Collocate bands before indices to ensure the same size to perform operations between bands
                loaded_bands = self._collocate_bands(loaded_bands)

                LOGGER.debug(f"Loading indices {to_str(index_list)}")
                bands_dict.update(
                    self._load_spectral_indices(
                        index_list,
                        loaded_bands,
                        pixel_size=pixel_size,
                        size=size,
                        **kwargs,
                    )
                )

            # Add bands
            bands_dict.update({band: loaded_bands[band] for band in band_list})

        # Add DEM
        if dem_list:
            LOGGER.debug(f"Loading DEM bands {to_str(dem_list)}")
            bands_dict.update(
                self._load_dem(dem_list, pixel_size=pixel_size, size=size, **kwargs)
            )

        # Add Clouds
        if clouds_list:
            LOGGER.debug(f"Loading Cloud bands {to_str(clouds_list)}")
            bands_dict.update(
                self._load_clouds(
                    clouds_list, pixel_size=pixel_size, size=size, **kwargs
                )
            )

        # Manage the case of arrays of different size -> collocate arrays if needed
        bands_dict = self._collocate_bands(bands_dict)

        # Create a dataset (only after collocation)
        coords = None
        if bands_dict:
            coords = bands_dict[bands[0]].coords

        # Make sure the dataset has the bands in the right order -> re-order the input dict
        return xr.Dataset({key: bands_dict[key] for key in bands}, coords=coords)

    def _load_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

    @abstractmethod
    def _load_bands(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

    def _load_spectral_indices(
        self,
        index_list: list,
        loaded_bands: dict,
        pixel_size: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}
        for idx in index_list:
            idx_path = self._construct_band_path(
                idx, pixel_size, size, writable=False, **kwargs
            )
            if idx_path.is_file():
                band_dict[idx] = utils.read(idx_path)
            else:
                idx_arr = compute_index(index=idx, bands=loaded_bands, **kwargs).rename(
                    idx
                )
                idx_arr.attrs["long_name"] = idx

                # Write on disk
                idx_path = self._construct_band_path(
                    idx, pixel_size, size, writable=True, **kwargs
                )
                utils.write(idx_arr, idx_path)
                band_dict[idx] = idx_arr

        return band_dict

    def _load_dem(
        self,
        band_list: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            band_list (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
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
                    dem_path = self._warp_dem(
                        kwargs.get(DEM_KW, dem_path),
                        pixel_size=pixel_size,
                        size=size,
                        **kwargs,
                    )
                elif band == SLOPE:
                    dem_path = self._compute_slope(
                        kwargs.get(SLOPE_KW, dem_path),
                        pixel_size=pixel_size,
                        size=size,
                    )
                elif band == HILLSHADE:
                    dem_path = self._compute_hillshade(
                        kwargs.get(HILLSHADE_KW, dem_path),
                        pixel_size=pixel_size,
                        size=size,
                    )
                else:
                    raise InvalidTypeError(f"Unknown DEM band: {band}")

                dem_name = to_str(band)[0]
                dem_arr = utils.read(
                    dem_path, pixel_size=pixel_size, size=size, as_type=np.float32
                ).rename(dem_name)
                dem_arr.attrs["long_name"] = dem_name
                dem_bands[band] = dem_arr

        return dem_bands

    def has_band(self, band: Union[BandNames, str]) -> bool:
        """
        Does this product has the specified band ?

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
            band (Union[BandNames, str]): EOReader band (optical, SAR, clouds, DEM)

        Returns:
            bool: True if the products has the specified band
        """
        band = self.to_band(band)[0]

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

    def has_bands(self, bands: Union[list, BandNames, str]) -> bool:
        """
        Does this product has the specified bands ?

        By band, we mean:

        - satellite band
        - index
        - DEM band
        - cloud band

        See :code:`has_band` for a code example.

        Args:
            bands (Union[list, BandNames, str]): EOReader bands (optical, SAR, clouds, DEM)

        Returns:
            bool: True if the products has the specified band
        """
        bands = types.make_iterable(bands)
        return all([self.has_band(band) for band in set(bands)])

    @abstractmethod
    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_cloud_band(CLOUDS)
            True
        """
        raise NotImplementedError

    def _has_index(self, idx: str) -> bool:
        """
        Cen the specified index be computed from this product ?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_index(NDVI)
            True

        Args:
            idx (str): Index

        Returns:
            bool: True if the specified index can be computed with this product's bands
        """
        index_bands = to_band(indices.get_needed_bands(idx))
        return all(np.isin(index_bands, self.get_existing_bands()))

    def __gt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired after the other

        """
        return self.date > other.date

    def __ge__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired after or in the same time as the other

        """
        return self.date >= other.date

    def __eq__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired in the same time as the other

        """
        return self.date == other.date

    def __ne__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired not in the same time as the other

        """
        return self.date != other.date

    def __le__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired before or in the same time as the other

        """
        return self.date <= other.date

    def __lt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired before the other

        """
        return self.date < other.date

    def __hash__(self):
        return hash(self.condensed_name)

    def _get_out_path(self, filename: str) -> tuple[AnyPathType, bool]:
        """
        Returns the output path of a file to be written, depending on if it already exists or not (manages CI folders)

        Args:
            filename (str): Filename

        Returns:
            tuple[AnyPathType, bool]: Output path and if the file already exists or not
        """
        out = self._get_band_folder() / filename
        exists = True
        if not out.exists():
            exists = False
            out = self._get_band_folder(writable=True) / filename

        return out, exists

    @property
    def output(self) -> AnyPathType:
        """Output directory of the product, to write orthorectified data for example."""
        return self._output

    @output.setter
    def output(self, value: str):
        """Output directory of the product, to write orthorectified data for example."""
        # Set the new output
        self._output = AnyPath(value)
        if not path.is_cloud_path(self._output):
            self._output = self._output.resolve()

        # Create temporary process folder
        old_tmp_process = self._tmp_process
        self._tmp_process = self._output.joinpath(f"tmp_{self.condensed_name}")
        os.makedirs(self._tmp_process, exist_ok=True)

        # Move all files from old process folder into the new one
        for file in path.listdir_abspath(old_tmp_process):
            with contextlib.suppress(shutil.Error):
                shutil.move(str(file), self._tmp_process)

        # Remove old output if existing into the new output
        if self._tmp_output:
            self._tmp_output.cleanup()
            self._tmp_output = None

    @property
    def stac(self) -> StacItem:
        if not self._stac:
            self._stac = StacItem(self)

        return self._stac

    def _warp_dem(
        self,
        dem_path: str = "",
        pixel_size: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
        **kwargs,
    ) -> AnyPathType:
        """
        Get this product DEM, warped to this product footprint and CRS.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.warp_dem(pixel_size=20)  # In meters
            '/path/to/20200824T110631_S2_T30TTK_L1C_150432_DEM.tif'

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            pixel_size (Union[float, tuple]): Pixel size in meters. If not specified, use the product pixel size.
            resampling (Resampling): Resampling method
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands

        Returns:
            AnyPathType: DEM path (as a VRT)
        """
        dem_name = f"{self.condensed_name}_DEM_{path.get_filename(dem_path)}.vrt"

        warped_dem_path, warped_dem_exists = self._get_out_path(dem_name)
        if warped_dem_exists:
            LOGGER.debug(
                "Already existing DEM for %s. Skipping process.", self.condensed_name
            )
        else:
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
                # Get adjusted transform and shape (with new pixel_size)
                if size is not None and pixel_size is None:
                    try:
                        # Get destination transform
                        out_h = size[1]
                        out_w = size[0]

                        # Get destination transform
                        coeff_x = def_w / out_w
                        coeff_y = def_h / out_h
                        dst_tr = def_tr
                        dst_tr *= dst_tr.scale(coeff_x, coeff_y)

                    except (TypeError, KeyError) as exc:
                        raise ValueError(
                            f"Size should exist (as pixel_size is None)"
                            f" and castable to a list: {size}"
                        ) from exc

                else:
                    # Refine pixel_size
                    if pixel_size is None:
                        pixel_size = self.pixel_size

                    bounds = transform.array_bounds(def_h, def_w, def_tr)
                    dst_tr, out_w, out_h = warp.calculate_default_transform(
                        def_crs,
                        self.crs(),
                        def_w,
                        def_h,
                        *bounds,
                        resolution=pixel_size,
                    )

                vrt_options = {
                    "resampling": resampling,
                    "crs": self.crs(),
                    "transform": dst_tr,
                    "height": out_h,
                    "width": out_w,
                    "nodata": self.nodata,
                    "dtype": "float32",
                }

                with WarpedVRT(dem_ds, **vrt_options) as vrt:
                    # At this point 'vrt' is a full dataset with dimensions,
                    # CRS, and spatial extent matching 'vrt_options'.
                    rio_shutil.copy(vrt, warped_dem_path, driver="vrt")

        return warped_dem_path

    @abstractmethod
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
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            resampling (Resampling): Resampling method

        Returns:
            AnyPathType: Hillshade mask path

        """
        raise NotImplementedError

    def _compute_slope(
        self,
        dem_path: str = "",
        pixel_size: Union[float, tuple] = None,
        size: Union[list, tuple] = None,
        resampling: Resampling = Resampling.bilinear,
    ) -> AnyPathType:
        """
        Compute slope mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            pixel_size (Union[float, tuple]): Pixel size in meters. If not specified, use the product pixel size.
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            resampling (Resampling): Resampling method

        Returns:
            AnyPathType: Slope mask path

        """
        # Warp DEM
        warped_dem_path = self._warp_dem(dem_path, pixel_size, size, resampling)

        # Get slope path
        slope_name = f"{self.condensed_name}_SLOPE_{path.get_filename(dem_path)}.tif"

        slope_path, slope_exists = self._get_out_path(slope_name)
        if slope_exists:
            LOGGER.debug(
                "Already existing slope DEM for %s. Skipping process.",
                self.condensed_name,
            )
        else:
            LOGGER.debug("Computing slope for %s", self.condensed_name)

            # Compute slope
            slope = rasters.slope(warped_dem_path)
            utils.write(slope, slope_path)

        return slope_path

    @staticmethod
    def _collocate_bands(bands: dict, reference: xr.DataArray = None) -> dict:
        """
        Collocate all bands from a dict if needed (if a raster shape is different)

        Args:
            bands (dict): Dict of bands to collocate if needed
            reference (xr.DataArray): Reference array

        Returns:
            dict: Collocated bands
        """
        for band_id, band_arr in bands.items():
            if reference is None:
                # If reference is not passed, use the first array
                # Don't collocate if same array
                reference = band_arr
            else:
                # To be sure, always collocate arrays, even if the size is the same
                # Indeed, a small difference in the coordinates will lead to empty arrays
                # So the bands MUST BE exactly aligned
                bands[band_id] = rasters.collocate(reference, band_arr)

        return bands

    # pylint: disable=R0913
    # Too many arguments (6/5)
    def stack(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        stack_path: AnyPathStrType = None,
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
            >>> stack = prod.stack([NDVI, MNDWI, GREEN], pixel_size=20)  # In meters

        Args:
            bands (list): Bands and index combination
            pixel_size (float): Stack pixel size. . If not specified, use the product pixel size.
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            stack_path (AnyPathStrType): Stack path
            save_as_int (bool): Convert stack to uint16 to save disk space (and therefore multiply the values by 10.000)
            **kwargs: Other arguments passed to :code:`load` or :code:`rioxarray.to_raster()` (such as :code:`compress`)

        Returns:
            xr.DataArray: Stack as a DataArray
        """
        # Manage already existing stack on disk
        if stack_path:
            stack_path = AnyPath(stack_path)
            if stack_path.is_file():
                return utils.read(stack_path, resolution=pixel_size, size=size)
            else:
                os.makedirs(str(stack_path.parent), exist_ok=True)

        bands = self.to_band(bands)

        # Create the analysis stack
        band_xds = self.load(bands, pixel_size=pixel_size, size=size, **kwargs)

        # Stack bands
        if save_as_int:
            nodata = kwargs.pop("nodata", UINT16_NODATA)
        else:
            nodata = kwargs.pop("nodata", self.nodata)
        stack, dtype = utils.stack(band_xds, save_as_int, nodata, **kwargs)

        # Update stack's attributes
        stack = self._update_attrs(stack, bands, **kwargs)

        # Write on disk
        if stack_path:
            LOGGER.debug("Saving stack")
            utils.write(stack, stack_path, dtype=dtype, nodata=nodata, **kwargs)

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

        Returns:
            xr.DataArray: Updated array/dataset
        """
        raise NotImplementedError

    def _update_attrs(
        self, xarr: Union[xr.DataArray, xr.Dataset], bands: list, **kwargs
    ) -> xr.DataArray:
        """
        Update attributes of the given array
        Args:
            xarr (Union[xr.DataArray, xr.Dataset]): Array whose attributes need an update
            bands (list): Bands
        Returns:
            xr.DataArray: Updated array
        """
        # Clean attributes, we don't want to pollute our attributes by default ones (not deterministic)
        # Are we sure of that ?
        xarr.attrs = {}

        bands = types.make_iterable(bands)
        long_name = to_str(bands)
        xr_name = "_".join(long_name)
        attr_name = " ".join(long_name)

        if isinstance(xarr, xr.DataArray):
            xarr = xarr.rename(xr_name)
        xarr.attrs["long_name"] = attr_name
        xarr.attrs["constellation"] = (
            self.constellation
            if isinstance(self.constellation, str)
            else self.constellation.value
        )
        xarr.attrs["constellation_id"] = self.constellation_id
        xarr.attrs["product_path"] = str(self.path)  # Convert to string
        xarr.attrs["product_name"] = self.name
        xarr.attrs["product_filename"] = self.filename
        xarr.attrs["instrument"] = (
            self.instrument
            if isinstance(self.instrument, str)
            else self.instrument.value
        )
        xarr.attrs["product_type"] = (
            self.product_type
            if isinstance(self.product_type, str)
            else self.product_type.value
        )
        xarr.attrs["acquisition_date"] = self.get_datetime(as_datetime=False)
        xarr.attrs["condensed_name"] = self.condensed_name
        od = self.get_orbit_direction()
        xarr.attrs["orbit_direction"] = od.value if od is not None else str(od)

        # kwargs attrs
        xarr = self._update_attrs_constellation_specific(xarr, bands, **kwargs)

        return xarr

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
            Affine, int, int, CRS: transform, width, height, CRS

        """
        with rasterio.open(str(self.get_default_band_path(**kwargs))) as dst:
            return dst.transform, dst.width, dst.height, dst.crs

    def _pixel_size_from_img_size(self, size: Union[list, tuple] = None) -> tuple:
        """
        Compute the corresponding pixel size to a given image size (positive resolution)

        Args:
            size (Union[list, tuple]): Size

        Returns:
            tuple: Pixel size as a tuple (x, y)
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
                resolution=self.pixel_size,
            )
            res_x = abs(utm_tr.a * utm_w / size[0])
            res_y = abs(utm_tr.e * utm_h / size[1])
        # Manage UTM case
        else:
            res_x = abs(def_tr.a * def_w / size[0])
            res_y = abs(def_tr.e * def_h / size[1])

        # Round pixel_size to the closest meter (under 1 meter, allow centimetric pixel_size)
        res_x = np.round(res_x, 1) if res_x < 1.0 else np.round(res_x, 0)
        res_y = np.round(res_y, 1) if res_y < 1.0 else np.round(res_y, 0)

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
            except (ReferenceError, ValueError):
                pass

        # All objects cleared
        for obj in objects:
            obj.cache_clear()

    def _pixel_size_to_str(self, pixel_size: Union[float, tuple, list] = None):
        """
        Convert a pixel_size to a normalized string

        Args:
            pixel_size (Union[float, tuple, list]): Pixel size

        Returns:
            str: Pixel size as a string
        """

        def _res_to_str(res):
            return f"{abs(res):.2f}m".replace(".", "-")

        if pixel_size:
            if types.is_iterable(pixel_size):
                res_x = _res_to_str(pixel_size[0])
                res_y = _res_to_str(pixel_size[1])
                res_str = res_x if res_x == res_y else f"{res_x}_{res_y}"
            else:
                res_str = _res_to_str(pixel_size)
        else:
            res_str = _res_to_str(self.pixel_size)

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
        repr_str = [
            f"eoreader.{self.__class__.__name__} '{self.name}'",
            "Attributes:",
            f"\tcondensed_name: {self.condensed_name}",
            f"\tpath: {self.path}",
            f"\tconstellation: {self.constellation if isinstance(self.constellation, str) else self.constellation.value}",
            f"\tsensor type: {self.sensor_type if isinstance(self.sensor_type, str) else self.sensor_type.value}",
            f"\tproduct type: {self.product_type if isinstance(self.product_type, str) else self.product_type.value}",
            f"\tdefault pixel size: {self.pixel_size}",
            f"\tdefault resolution: {self.resolution}",
            f"\tacquisition datetime: {self.get_datetime(as_datetime=True).isoformat()}",
            f"\tband mapping:\n{band_repr}",
            f"\tneeds extraction: {self.needs_extraction}",
        ]

        return repr_str + self._to_repr_constellation_specific()

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
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "You need to install 'matplotlib' to plot the product."
            ) from exc
        else:
            quicklook_path = self.get_quicklook_path()

            if quicklook_path is not None:
                plt.figure(figsize=(6, 6))
                if path.get_ext(quicklook_path).lower() in ["png", "jpg", "jpeg"]:
                    try:
                        from PIL import Image
                    except ModuleNotFoundError as exc:
                        raise ModuleNotFoundError(
                            "You need to install 'pillow' to plot the product."
                        ) from exc

                    if self.is_archived:
                        qlk = BytesIO(
                            self._read_archived_file(
                                f".*{os.path.basename(quicklook_path)}"
                            )
                        )
                    else:
                        if path.is_cloud_path(quicklook_path):
                            quicklook_path = AnyPath(quicklook_path).fspath

                        qlk = quicklook_path
                    plt.imshow(Image.open(qlk))
                else:
                    qck = rasters.read(quicklook_path)
                    if qck.rio.count == 3:
                        qck.plot.imshow(robust=True)
                    elif qck.rio.count == 1:
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

    def to_band(self, raw_bands: Union[list, BandNames, str, int]) -> list:
        """
        Convert any raw band identifier to a usable band.

        Bands can be called with their name, ID or mapped name.
        For example, for Sentinel-3 OLCI you can use `7`, `Oa07` or `YELLOW`. For Landsat-8, you can use `BLUE` or `2`.

        Args:
            raw_bands (Union[list, BandNames, str, int]): Raw bands

        Returns:
            list: Mapped bands
        """
        raw_bands = types.make_iterable(raw_bands)

        bands = []
        for raw_band in raw_bands:
            try:
                bands += to_band(raw_band)
            except InvalidTypeError as exc:
                found = False
                for band_name, band in self.bands.items():
                    if band is not None and str(raw_band) in [
                        str(band.id),
                        band.name,
                        band.common_name,
                        band.eoreader_name,
                    ]:
                        bands.append(band_name)
                        found = True
                        break

                if not found:
                    raise InvalidTypeError(
                        f"Couldn't find any band in {self.condensed_name} that corresponds to {raw_band}."
                    ) from exc

        return bands

    def _get_archived_file_list(self, archive_path=None):
        """
        Overload of utils.read_archived_file to use the product's path as archive.
        Return a tuple to make it hashable and therfore digestable by lru_cache.
        See https://stackoverflow.com/questions/49210801/python3-pass-lists-to-function-with-functools-lru-cache
        '"""

        if archive_path is None:
            archive_path = self.path

        return tuple(utils.get_archived_file_list(archive_path))

    def _read_archived_file(self, regex, archive_path=None):
        """Overload of utils.read_archived_file to handle the cached 'get_archived_file_list'"""

        if archive_path is None:
            archive_path = self.path

        return utils.read_archived_file(
            archive_path,
            regex=regex,
            file_list=self._get_archived_file_list(archive_path),
        )

    def _read_archived_xml(self, regex, archive_path=None):
        """Overload of utils.read_archived_xml to handle the cached 'get_archived_file_list'"""

        if archive_path is None:
            archive_path = self.path

        return utils.read_archived_xml(
            archive_path,
            regex=regex,
            file_list=self._get_archived_file_list(archive_path),
        )

    def _read_archived_html(self, regex, archive_path=None):
        """Overload of utils.read_archived_html to handle the cached 'get_archived_file_list'"""

        if archive_path is None:
            archive_path = self.path

        return utils.read_archived_html(
            archive_path,
            regex=regex,
            file_list=self._get_archived_file_list(archive_path),
        )

    def _get_archived_path(
        self, regex, as_list=False, case_sensitive=False, archive_path=None
    ):
        """Overload of utils.get_archived_path to handle the cached 'get_archived_file_list'"""

        if archive_path is None:
            archive_path = self.path

        return utils.get_archived_path(
            archive_path=archive_path,
            regex=regex,
            as_list=as_list,
            case_sensitive=case_sensitive,
            file_list=self._get_archived_file_list(archive_path),
        )

    def _get_archived_rio_path(self, regex, as_list=False, archive_path=None):
        """Overload of utils.get_archived_rio_path to handle the cached 'get_archived_file_list'"""

        if archive_path is None:
            archive_path = self.path

        return utils.get_archived_rio_path(
            archive_path=archive_path,
            regex=regex,
            as_list=as_list,
            file_list=self._get_archived_file_list(archive_path),
        )

    def _read_archived_vector(
        self,
        archive_path: AnyPathStrType = None,
        crs=None,
        archive_regex: str = None,
        window=None,
        **kwargs,
    ):
        """Overload of sertit.vectors.read to handle the cached 'get_archived_file_list'"""
        if archive_path is None:
            archive_path = self.path

        return vectors.read(
            vector_path=archive_path,
            crs=crs,
            archive_regex=archive_regex,
            window=window,
            file_list=self._get_archived_file_list(archive_path),
            **kwargs,
        )

    def get_bands_names(self) -> list:
        """
        Get the name of the bands composing the product, ordered by ID.
        For example, for SPOT7: ['RED', 'GREEN', 'BLUE', 'NIR']

        Returns:
            list: Ordered bands names
        """
        stack_bands = {
            band.id: band.name for band in self.bands.values() if band is not None
        }
        return [id_name[1] for id_name in sorted(stack_bands.items())]
