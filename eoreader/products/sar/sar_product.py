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
""" Super class for SAR products """
import logging
import os
import re
import tempfile
import zipfile
from abc import abstractmethod
from enum import unique
from pathlib import Path
from string import Formatter
from typing import Union

import geopandas as gpd
import numpy as np
import rioxarray
from cloudpathlib import AnyPath, CloudPath
from rasterio import crs
from rasterio.enums import Resampling

from eoreader import utils
from eoreader.bands.alias import (
    is_clouds,
    is_dem,
    is_index,
    is_optical_band,
    is_sar_band,
)
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import SarBandNames as sbn
from eoreader.bands.bands import SarBands
from eoreader.env_vars import DEM_PATH, DSPK_GRAPH, PP_GRAPH, SAR_DEF_RES, SNAP_DEM_NAME
from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError
from eoreader.products.product import Product, SensorType
from eoreader.reader import Platform
from eoreader.utils import EOREADER_NAME
from sertit import files, misc, rasters, snap, strings, vectors
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class SnapDems(ListEnum):
    """
    DEM available in SNAP for the Terrain Correction module
    """

    ACE2_5Min = "ACE2_5Min"
    """
    ACE2_5Min, Altimeter Corrected Elevations, Version 2
    """

    ACE30 = "ACE30"
    """
    ACE30:  Altimeter Corrected Elevations
    """

    ASTER = "ASTER 1sec GDEM"
    """
    ASTER 1sec GDEM: Advanced Spaceborne Thermal Emission and Reflection Radiometer

    """

    GLO_30 = "Copernicus 30m Global DEM"
    """
    Copernicus 30m Global DEM
    """

    GLO_90 = "Copernicus 90m Global DEM"
    """
    Copernicus 90m Global DEM
    """

    GETASSE30 = "GETASSE30"
    """
    GETASSE30: Global Earth Topography And Sea Surface Elevation at 30 arc second resolution
    """

    SRTM_1SEC = "SRTM 1Sec HGT"
    """
    SRTM 1Sec HGT: Shuttle Radar Topography Mission
    """

    SRTM_3SEC = "SRTM 3Sec"
    """
    SRTM 3Sec: Shuttle Radar Topography Mission
    """

    EXT_DEM = "External DEM"
    f"""
    External DEM, needs `{DEM_PATH}` to be correctly positioned
    """


@unique
class SarProductType(ListEnum):
    """
    Generic products types, used to chose a SNAP graph.
    """

    CPLX = "COMPLEX"
    """Single Look Complex"""

    GDRG = "GROUND"
    """Ground Range"""

    OTHER = "OTHER"
    """Other products types, no used in EOReader"""
    # Add ortho products ?


class _ExtendedFormatter(Formatter):
    """An extended format string formatter

    Formatter with extended conversion symbol
    """

    def convert_field(self, value, conversion):
        """Extend conversion symbol
        Following additional symbol has been added
        * l: convert to string and low case
        * u: convert to string and up case

        default are:
        * s: convert with str()
        * r: convert with repr()
        * a: convert with ascii()
        """

        if conversion == "u":
            cv_field = str(value).upper()
        elif conversion == "l":
            cv_field = str(value).lower()
        else:
            cv_field = super().convert_field(value, conversion)

        return cv_field


class SarProduct(Product):
    """Super class for SAR Products"""

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        self.sar_prod_type = None
        """SAR product type, either Single Look Complex or Ground Range"""

        self.sensor_mode = None
        """Sensor Mode of the current product"""

        self.pol_channels = None
        """Polarization Channels stored in the current product"""

        # Private attributes
        self._band_folder = None
        self._snap_path = None
        self._raw_band_regex = None
        self._snap_no_data = 0

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp)

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self.tile_name = None
        self.sensor_type = SensorType.SAR
        self.band_names = SarBands()
        self._set_sensor_mode()
        self.pol_channels = self._get_raw_bands()

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
        return rasters.get_footprint(
            self.get_default_band_path()
        )  # Processed by SNAP: the nodata is set

    def get_default_band(self) -> BandNames:
        """
        Get default band:
        The first existing one between `VV` and `HH` for SAR data.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band()
            <SarBandNames.VV: 'VV'>

        Returns:
            str: Default band
        """
        existing_bands = self._get_raw_bands()
        if not existing_bands:
            raise InvalidProductError(f"No band exists for products: {self.name}")

        # The order matters, as we almost always prefer VV and HH
        if sbn.VV in existing_bands:
            default_band = sbn.VV
        elif sbn.HH in existing_bands:
            default_band = sbn.HH
        elif sbn.VH in existing_bands:
            default_band = sbn.VH
        elif sbn.HV in existing_bands:
            default_band = sbn.HV
        else:
            raise InvalidTypeError(f"Invalid bands for products: {existing_bands}")

        return default_band

    # Parameters differ from overridden 'get_default_band_path' method (arguments-differ)
    # pylint: disable=W0221
    def get_default_band_path(self) -> str:
        """
        Get default band path (the first existing one between `VV` and `HH` for SAR data), ready to use (orthorectified)

        .. WARNING:: This functions orthorectifies SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band_path()
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'

        Returns:
            str: Default band path
        """
        default_band = self.get_default_band()
        band_path = self.get_band_paths([default_band])

        return band_path[default_band]

    @abstractmethod
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                   Name  ...                                           geometry
            0  Sentinel-1 Image Overlay  ...  POLYGON ((0.85336 42.24660, -2.32032 42.65493,...
            [1 rows x 12 columns]

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        raise NotImplementedError("This method should be implemented by a child class")

    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                   Name  ...                                           geometry
            0  Sentinel-1 Image Overlay  ...  POLYGON ((817914.501 4684349.823, 555708.624 4...
            [1 rows x 12 columns]

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        utm = vectors.corresponding_utm_projection(
            extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
        )
        extent = extent_wgs84.to_crs(utm)

        return extent

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
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        crs_str = vectors.corresponding_utm_projection(
            extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
        )

        return crs.CRS.from_string(crs_str)

    def _get_sar_product_type(
        self,
        prod_type_pos: int,
        gdrg_types: Union[ListEnum, list],
        cplx_types: Union[ListEnum, list],
    ) -> None:
        """
        Get products type, special function for SAR satellites.

        Args:
            prod_type_pos (int): Position of the products type in the file name
            gdrg_types (Union[ListEnum, list]): Ground Range products types
            cplx_types (Union[ListEnum, list]): Complex products types
        """
        # Get and check products type class
        if not isinstance(gdrg_types, list):
            gdrg_types = [gdrg_types]
        if not isinstance(cplx_types, list):
            cplx_types = [cplx_types]

        all_types = gdrg_types + cplx_types
        prod_type_class = all_types[0].__class__
        assert all(isinstance(prod_type, prod_type_class) for prod_type in all_types)

        # Get products type
        try:
            # All products types can be found in the filename and are 3 characters long
            self.product_type = prod_type_class.from_value(
                self.split_name[prod_type_pos][:3]
            )
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid products type for {self.name}") from ex

        # Link to SAR generic products types
        if self.product_type in gdrg_types:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type in cplx_types:
            self.sar_prod_type = SarProductType.CPLX
        else:
            self.sar_prod_type = SarProductType.OTHER

        # Discard invalid products types
        if self.sar_prod_type == SarProductType.OTHER:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available ({self.name})"
            )

    @abstractmethod
    def _set_sensor_mode(self) -> None:
        """
        Set SAR sensor mode
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: This functions orthorectifies and despeckles SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([VV, HH])
            {
                <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'
            }
            >>> # HH doesn't exist

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            bname = self.band_names[band]
            if bname is None:
                raise InvalidProductError(
                    f"Non existing band ({band.name}) for {self.name}"
                )
            try:
                # Try to load orthorectified bands
                band_paths[band] = files.get_file_in_dir(
                    self._get_band_folder(),
                    f"*{self.condensed_name}_{bname}.tif",
                    exact_name=True,
                )
            except FileNotFoundError:
                speckle_band = sbn.corresponding_speckle(band)
                if speckle_band in self.pol_channels:
                    if sbn.is_despeckle(band):
                        # Despeckle the noisy band
                        band_paths[band] = self._despeckle_sar(speckle_band)
                    else:
                        all_band_paths = self._pre_process_sar(resolution)
                        band_paths = {
                            band: path
                            for band, path in all_band_paths.items()
                            if band in band_list
                        }

        return band_paths

    def _get_raw_band_paths(self) -> dict:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        extended_fmt = _ExtendedFormatter()
        band_paths = {}
        for band, band_name in self.band_names.items():
            band_regex = extended_fmt.format(self._raw_band_regex, band_name)

            if self.is_archived:
                if self.path.suffix == ".zip":
                    # Open the zip file
                    with zipfile.ZipFile(self.path, "r") as zip_ds:
                        # Get the correct band path
                        regex = re.compile(band_regex.replace("*", ".*"))
                        try:
                            band_paths[band] = list(
                                filter(
                                    regex.match, [f.filename for f in zip_ds.filelist]
                                )
                            )[0]
                        except IndexError:
                            continue
                else:
                    raise InvalidProductError(
                        f"Only zipped products can be processed without extraction: {self.path}"
                    )
            else:
                try:
                    band_paths[band] = files.get_file_in_dir(
                        self._band_folder, band_regex, exact_name=True, get_list=True
                    )
                except FileNotFoundError:
                    continue

        return band_paths

    def _get_raw_bands(self) -> list:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            list: List of existing bands in the raw products (vv, hh, vh, hv)
        """
        band_paths = self._get_raw_band_paths()
        return list(band_paths.keys())

    def get_existing_band_paths(self) -> dict:
        """
        Return the existing orthorectified band paths (including despeckle bands).

        .. WARNING:: This functions orthorectifies SAR bands if not existing !

        .. WARNING:: This functions despeckles SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_existing_band_paths()
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            {
                <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',
                <SarBandNames.VH: 'VH'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',
                <SarBandNames.VV_DSPK: 'VV_DSPK'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',
                <SarBandNames.VH_DSPK: 'VH_DSPK'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif'
            }

        Returns:
            dict: Dictionary containing the path of every orthorectified bands
        """
        return self.get_band_paths(self.get_existing_bands())

    def get_existing_bands(self) -> list:
        """
        Return the existing orthorectified bands (including despeckle bands).

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_existing_bands()
            [<SarBandNames.VV: 'VV'>,
            <SarBandNames.VH: 'VH'>,
            <SarBandNames.VV_DSPK: 'VV_DSPK'>,
            <SarBandNames.VH_DSPK: 'VH_DSPK'>]

        Returns:
            list: List of existing bands in the products
        """
        # Get raw bands (maximum number of bands)
        raw_bands = self._get_raw_bands()
        existing_bands = raw_bands + [
            sbn.corresponding_despeckle(band) for band in raw_bands
        ]

        return existing_bands

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
    def _read_band(
        self,
        path: str,
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (str): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            XDS_TYPE: Band xarray

        """
        return rasters.read(
            path, resolution=resolution, size=size, resampling=Resampling.bilinear
        ).astype(np.float32)

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if not isinstance(bands, list):
            bands = [bands]
        band_paths = self.get_band_paths(bands, resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band_name, band_path in band_paths.items():
            # Read CSK band
            band_arrays[band_name] = self._read_band(
                band_path, resolution=resolution, size=size
            )

        return band_arrays

    def _load(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Core function loading SAR data bands

        Args:
            bands (list): Band list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

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
            elif is_optical_band(band):
                raise TypeError(
                    f"You should ask for SAR bands as {self.name} is a SAR product."
                )
            elif is_sar_band(band):
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
                    f"Clouds cannot be retrieved from SAR data ({self.condensed_name})."
                )
            else:
                raise InvalidTypeError(f"{band} is neither a band nor an index !")

        # Check if DEM is set and exists
        if dem_list:
            self._check_dem_path()

        # Load bands
        bands = self._load_bands(band_list, resolution=resolution, size=size)

        # Add DEM
        bands.update(self._load_dem(dem_list, resolution=resolution, size=size))

        return bands

    def _pre_process_sar(self, resolution: float = None) -> dict:
        """
        Pre-process SAR data (geocoding...)

        Args:
            resolution (float): Resolution

        Returns:
            dict: Dictionary containing {band: path}
        """
        out = {}

        # Create target dir (tmp dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Use dimap for speed and security (ie. GeoTiff's broken georef)
            pp_target = os.path.join(tmp_dir, f"{self.condensed_name}")
            pp_dim = pp_target + ".dim"

            # Pre-process graph
            if PP_GRAPH not in os.environ:
                sat = "s1" if self.sat_id == Platform.S1.name else "sar"
                spt = "grd" if self.sar_prod_type == SarProductType.GDRG else "cplx"
                pp_graph = utils.get_data_dir().joinpath(
                    f"{spt}_{sat}_preprocess_default.xml"
                )
            else:
                pp_graph = AnyPath(os.environ[PP_GRAPH])
                if not pp_graph.is_file() or not pp_graph.suffix == ".xml":
                    FileNotFoundError(f"{pp_graph} cannot be found.")

            # Command line
            if not os.path.isfile(pp_dim):
                def_res = float(os.environ.get(SAR_DEF_RES, self.resolution))
                res_m = resolution if resolution else def_res
                res_deg = (
                    res_m / 10.0 * 8.983152841195215e-5
                )  # Approx, shouldn't be used

                # Manage DEM name
                try:
                    dem_name = SnapDems.from_value(
                        os.environ.get(SNAP_DEM_NAME, SnapDems.GETASSE30)
                    )
                except AttributeError as ex:
                    raise ValueError(
                        f"{SNAP_DEM_NAME} should be chosen among {SnapDems.list_values()}"
                    ) from ex

                # Manage DEM path
                if dem_name == SnapDems.EXT_DEM:
                    dem_path = os.environ.get(DEM_PATH)
                    if not dem_path:
                        raise ValueError(
                            f"You specified '{dem_name.value}' but you didn't give any DEM path. "
                            f"Please set the environment variable {DEM_PATH} "
                            f"or change {SNAP_DEM_NAME} to an acceptable SNAP DEM."
                        )
                elif dem_name in [SnapDems.GLO_30, SnapDems.GLO_90]:
                    LOGGER.warning(
                        "For now, SNAP cannot use Copernicus DEM "
                        "(see https://forum.step.esa.int/t/terrain-correction-with-copernicus-dem/29025/11). "
                        "Using GETASSE30 instead."
                    )
                    dem_name = SnapDems.GETASSE30
                else:
                    dem_path = ""

                # Download cloud path to cache
                if isinstance(self.path, CloudPath):
                    LOGGER.debug(
                        f"Caching {self.path} to {os.path.join(tmp_dir, self.path.name)}"
                    )
                    if self.path.is_dir():
                        prod_path = os.path.join(
                            tmp_dir, self.path.name, self._snap_path
                        )
                        self.path.download_to(os.path.join(tmp_dir, self.path.name))
                    else:
                        prod_path = self.path.fspath
                else:
                    prod_path = self.path.joinpath(self._snap_path)

                # Create SNAP CLI
                cmd_list = snap.get_gpt_cli(
                    pp_graph,
                    [
                        f"-Pfile={strings.to_cmd_string(prod_path)}",
                        f"-Pdem_name={strings.to_cmd_string(dem_name.value)}",
                        f"-Pdem_path={strings.to_cmd_string(dem_path)}",
                        f"-Pcrs={self.crs()}",
                        f"-Pres_m={res_m}",
                        f"-Pres_deg={res_deg}",
                        f"-Pout={strings.to_cmd_string(pp_dim)}",
                    ],
                    display_snap_opt=LOGGER.level == logging.DEBUG,
                )

                # Pre-process SAR images according to the given graph
                LOGGER.debug("Pre-process SAR image")
                try:
                    misc.run_cli(cmd_list)
                except RuntimeError as ex:
                    raise RuntimeError("Something went wrong with SNAP!") from ex

            # Convert DIMAP images to GeoTiff
            try:
                for pol in self.pol_channels:
                    # Speckle image
                    out[sbn.from_value(pol)] = self._write_sar(pp_dim, pol.value)
            except AssertionError:
                if isinstance(self.path, CloudPath):
                    raise InvalidProductError(
                        "For now, TerraSAR-X data cannot be processed while being stored in the cloud."
                        "A bug when caching directories prevents that, see here: "
                        "https://github.com/drivendataorg/cloudpathlib/issues/148"
                    )
        return out

    def _despeckle_sar(self, band: sbn) -> str:
        """
        Pre-process SAR data (geocode...)

        Args:
            band (sbn): Band to despeckle

        Returns:
            str: Despeckled path
        """
        # Create target dir (tmp dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Out files
            target_file = os.path.join(tmp_dir, f"{self.condensed_name}")
            dspk_dim = target_file + ".dim"

            # Despeckle graph
            if DSPK_GRAPH not in os.environ:
                dspk_graph = utils.get_data_dir().joinpath("sar_despeckle_default.xml")
            else:
                dspk_graph = AnyPath(os.environ[DSPK_GRAPH])
                if not dspk_graph.is_file() or not dspk_graph.suffix == ".xml":
                    FileNotFoundError(f"{dspk_graph} cannot be found.")

            # Create command line and run it
            if not os.path.isfile(dspk_dim):
                path = self.get_band_paths([band])[band]
                cmd_list = snap.get_gpt_cli(
                    dspk_graph,
                    [f"-Pfile={path}", f"-Pout={dspk_dim}"],
                    display_snap_opt=False,
                )

                # Pre-process SAR images according to the given graph
                LOGGER.debug(f"Despeckling {band.name}")
                try:
                    misc.run_cli(cmd_list)
                except RuntimeError as ex:
                    raise RuntimeError("Something went wrong with SNAP!") from ex

            # Convert DIMAP images to GeoTiff
            out = self._write_sar(dspk_dim, band.value, dspk=True)

        return out

    def _write_sar(self, dim_path: str, pol_up: str, dspk=False):
        """
        Write SAR image on disk.

        Args:
            dim_path (str): DIMAP path
            pol_up (str): Polarization name
        """
        pol_up = pol_up.upper()  # To be sure

        # Get .img file path (readable by rasterio)
        try:
            img = rasters.get_dim_img_path(dim_path, pol_up)
        except FileNotFoundError:
            img = rasters.get_dim_img_path(dim_path)  # Maybe not the good name

        # Open SAR image
        with rioxarray.open_rasterio(str(img)) as arr:
            arr = arr.where(arr != self._snap_no_data, np.nan)

            # Save the file as the terrain-corrected image
            file_path = os.path.join(
                self._tmp_process,
                f"{files.get_filename(dim_path)}_{pol_up}{'_DSPK' if dspk else ''}.tif",
            )
            # WARNING: Set nodata to 0 here as it is the value wanted by SNAP !
            rasters.write(arr, file_path, dtype=np.float32, nodata=0)

        return file_path

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
        raise InvalidProductError("Impossible to compute hillshade mask for SAR data.")

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_cloud_band(CLOUDS)
            False
        """
        return False

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.sensor_mode.name}_{self.product_type.value}"
