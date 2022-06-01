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
""" Super class for SAR products """
import logging
import os
import tempfile
from abc import abstractmethod
from enum import unique
from pathlib import Path
from string import Formatter
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from cloudpathlib import AnyPath, CloudPath
from rasterio import crs
from rasterio.enums import Resampling
from sertit import files, misc, rasters, snap, strings, vectors
from sertit.misc import ListEnum

from eoreader import cache, utils
from eoreader.bands import BandNames, SarBand, SarBandMap
from eoreader.bands import SarBandNames as sab
from eoreader.bands import is_clouds, is_dem, is_index, is_sar_band, is_spectral_band
from eoreader.env_vars import DEM_PATH, DSPK_GRAPH, PP_GRAPH, SAR_DEF_RES, SNAP_DEM_NAME
from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError
from eoreader.keywords import SAR_INTERP_NA
from eoreader.products.product import Product, SensorType
from eoreader.reader import Constellation
from eoreader.stac import INTENSITY
from eoreader.utils import EOREADER_NAME, simplify

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
        **kwargs,
    ) -> None:
        self.sar_prod_type = None
        """SAR product type, either Single Look Complex or Ground Range"""

        self.sensor_mode = None
        """Sensor Mode of the current product"""

        self.pol_channels = None
        """Polarization Channels stored in the current product"""

        self.snap_filename = None
        """Path used by SNAP to process this product"""

        # Private attributes
        self._band_folder = None
        self._raw_band_regex = None
        self._snap_no_data = 0
        self._raw_no_data = 0

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _map_bands(self) -> None:
        """
        Map bands
        """
        self.bands.map_bands(
            {
                band_name: SarBand(
                    eoreader_name=band_name,
                    name=band_name.name,
                    gsd=self.resolution,
                    id=band_name.value,
                    asset_role=INTENSITY,
                )
                for band_name in self.get_existing_bands()
            }
        )

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.tile_name = None
        self.sensor_type = SensorType.SAR
        self.bands = SarBandMap()
        self.is_ortho = False

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self._set_sensor_mode()
        self.pol_channels = self._get_raw_bands()

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # Processed by SNAP: the nodata is set -> use get_footprint instead of vectorize
        return rasters.get_footprint(self.get_default_band_path())

    def get_default_band(self) -> BandNames:
        """
        Get default band:
        The first existing one between :code:`VV` and :code:`HH` for SAR data.

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
        if sab.VV in existing_bands:
            default_band = sab.VV
        elif sab.HH in existing_bands:
            default_band = sab.HH
        elif sab.VH in existing_bands:
            default_band = sab.VH
        elif sab.HV in existing_bands:
            default_band = sab.HV
        else:
            raise InvalidTypeError(f"Invalid bands for products: {existing_bands}")

        return default_band

    def get_default_band_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get default band path (the first existing one between :code:`VV` and :code:`HH` for SAR data), ready to use (orthorectified)

        .. WARNING:: This functions orthorectifies SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band_path()
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VV.tif'

        Args:
            kwargs: Additional arguments
        Returns:
            Union[CloudPath, Path]: Default band path
        """
        default_band = self.get_default_band()
        band_path = self.get_band_paths([default_band], **kwargs)

        return band_path[default_band]

    @cache
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
        raise NotImplementedError

    @cache
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
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        utm = vectors.corresponding_utm_projection(
            extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
        )
        extent = extent_wgs84.to_crs(utm)

        return extent

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
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        crs_str = vectors.corresponding_utm_projection(
            extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
        )

        return crs.CRS.from_string(crs_str)

    @abstractmethod
    def _set_sensor_mode(self) -> None:
        """
        Set SAR sensor mode
        """
        raise NotImplementedError

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: This functions orthorectifies and despeckles SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([VV, HH])
            {
                <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VV.tif'
            }
            >>> # HH doesn't exist

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            if self.bands[band] is None:
                raise InvalidProductError(
                    f"Non existing band ({band.name}) for {self.name}"
                )
            try:
                # Try to load orthorectified bands
                band_id = self.bands[band].id
                band_paths[band] = files.get_file_in_dir(
                    self._get_band_folder(),
                    f"*{self.condensed_name}_{band_id}.tif",
                    exact_name=True,
                )
            except FileNotFoundError:
                speckle_band = sab.corresponding_speckle(band)
                if speckle_band in self.pol_channels:
                    if sab.is_despeckle(band):
                        # Check if existing speckle ortho band
                        try:
                            files.get_file_in_dir(
                                self._get_band_folder(),
                                f"*{self.condensed_name}_{self.bands[speckle_band].id}.tif",
                                exact_name=True,
                            )
                        except FileNotFoundError:
                            self._pre_process_sar(speckle_band, resolution, **kwargs)

                        # Despeckle the noisy band
                        band_paths[band] = self._despeckle_sar(speckle_band, **kwargs)
                    else:
                        band_paths[band] = self._pre_process_sar(
                            band, resolution, **kwargs
                        )

        return band_paths

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the existing band paths (as they come with the archived products).

        Args:
            **kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        extended_fmt = _ExtendedFormatter()
        band_paths = {}
        for band in sab.speckle_list():
            band_regex = extended_fmt.format(self._raw_band_regex, band.value)

            if self.is_archived:
                if self.path.suffix == ".zip":
                    try:
                        band_paths[band] = files.get_archived_rio_path(
                            self.path, band_regex.replace("*", ".*"), as_list=True
                        )[0]
                        # Get as a list but keep only the first item (S1-SLC with 3 swaths)
                    except FileNotFoundError:
                        continue
                else:
                    raise InvalidProductError(
                        f"Only zipped products can be processed without extraction: {self.path}"
                    )
            else:
                try:
                    band_paths[band] = files.get_file_in_dir(
                        self._band_folder, band_regex, exact_name=True, get_list=True
                    )[0]
                    # Get as a list but keep only the first item (S1-SLC with 3 swaths)
                except FileNotFoundError:
                    continue

        return band_paths

    def _get_raw_bands(self) -> list:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            list: List of existing bands in the raw products (vv, hh, vh, hv)
        """
        band_paths = self.get_raw_band_paths()
        return list(band_paths.keys())

    def get_existing_band_paths(self) -> dict:
        """
        Return the existing orthorectified band paths (including despeckle bands).

        .. WARNING:: This functions orthorectifies SAR bands if not existing !

        .. WARNING:: This functions despeckles SAR bands if not existing !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_existing_band_paths()
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            Executing processing graph
            ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
            {
                <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VV.tif',
                <SarBandNames.VH: 'VH'>: '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VH.tif',
                <SarBandNames.VV_DSPK: 'VV_DSPK'>: '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VV_DSPK.tif',
                <SarBandNames.VH_DSPK: 'VH_DSPK'>: '20191215T060906_S1_IW_GRD/20191215T060906_S1_IW_GRD_VH_DSPK.tif'
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
            >>> from eoreader.bands import *
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
            sab.corresponding_despeckle(band) for band in raw_bands
        ]

        return existing_bands

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
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
            Invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        return utils.read(
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
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
        band_paths = self.get_band_paths(bands, resolution, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band_name, band_path in band_paths.items():
            # Read CSK band
            band_arrays[band_name] = self._read_band(
                band_path, resolution=resolution, size=size, **kwargs
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
        Core function loading SAR data bands

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
            elif is_spectral_band(band):
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
            self._check_dem_path(bands, **kwargs)

        # Load bands
        bands = self._load_bands(band_list, resolution=resolution, size=size, **kwargs)

        # Add DEM
        bands.update(
            self._load_dem(dem_list, resolution=resolution, size=size, **kwargs)
        )

        return bands

    def _pre_process_sar(self, band: sab, resolution: float = None, **kwargs) -> str:
        """
        Pre-process SAR data (geocoding...)

        Args:
            band (sbn): Band to preprocess
            resolution (float): Resolution
            kwargs: Additional arguments

        Returns:
            str: Band path
        """
        raw_band_path = str(self.get_raw_band_paths(**kwargs)[band])
        with rasterio.open(raw_band_path) as ds:
            raw_crs = ds.crs

        if raw_crs and raw_crs.is_projected:
            # Set the nodata and write the image where they belong
            with rioxarray.open_rasterio(raw_band_path) as arr:
                arr = arr.where(arr != self._raw_no_data, np.nan)

                file_path = os.path.join(
                    self._get_band_folder(writable=True),
                    f"{self.condensed_name}_{band.name}.tif",
                )
                utils.write(arr, file_path, dtype=np.float32, nodata=self._snap_no_data)
            return file_path
        else:
            # Create target dir (tmp dir)
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Use dimap for speed and security (ie. GeoTiff's broken georef)
                pp_target = os.path.join(tmp_dir, f"{self.condensed_name}")
                pp_dim = pp_target + ".dim"

                # Pre-process graph
                if PP_GRAPH not in os.environ:
                    sat = (
                        "s1"
                        if self.constellation_id == Constellation.S1.name
                        else "sar"
                    )
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
                    # Resolution
                    def_res = float(os.environ.get(SAR_DEF_RES, self.resolution))
                    res_m = resolution if resolution else def_res
                    res_deg = (
                        res_m / 10.0 * 8.983152841195215e-5
                    )  # Approx, shouldn't be used

                    # Manage DEM name
                    try:
                        dem_name = SnapDems.from_value(
                            os.environ.get(SNAP_DEM_NAME, SnapDems.GLO_30)
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
                    else:
                        dem_path = ""

                    # Download cloud path to cache
                    if isinstance(self.path, CloudPath):
                        LOGGER.debug(
                            f"Caching {self.path} to {os.path.join(tmp_dir, self.path.name)}"
                        )
                        if self.path.is_dir():
                            prod_path = os.path.join(
                                tmp_dir, self.path.name, self.snap_filename
                            )
                            self.path.download_to(os.path.join(tmp_dir, self.path.name))
                        else:
                            prod_path = (
                                self.path.fspath
                            )  # In tmp file, no need to download_to
                    else:
                        prod_path = self.path.joinpath(self.snap_filename)

                    # Create SNAP CLI
                    cmd_list = snap.get_gpt_cli(
                        pp_graph,
                        [
                            f"-Pfile={strings.to_cmd_string(prod_path)}",
                            f"-Pcalib_pola={strings.to_cmd_string(band.name)}",
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
                LOGGER.debug("Converting DIMAP to GeoTiff")
                return self._write_sar(pp_dim, band.value, **kwargs)

    def _despeckle_sar(self, band: sab, **kwargs) -> str:
        """
        Pre-process SAR data (geocode...)

        Args:
            band (sbn): Band to despeckle
            kwargs: Additional arguments

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
                path = self.get_band_paths([band], **kwargs)[band]
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
            out = self._write_sar(dspk_dim, band.value.upper(), dspk=True, **kwargs)

        return out

    def _write_sar(self, dim_path: str, pol: str, dspk=False, **kwargs) -> str:
        """
        Write SAR image on disk.

        Args:
            dim_path (str): DIMAP path
            pol (str): Polarization name
            kwargs: Additional arguments

        Returns:
            str: SAR path
        """

        def interp_na(arr, dim):
            try:
                arr = arr.interpolate_na(dim=dim, limit=10, keep_attrs=True)
            except ValueError:
                try:
                    # ValueError: Index 'y' must be monotonically increasing
                    dim_idx = getattr(arr, dim)
                    reversed_dim_idx = list(reversed(dim_idx))
                    arr = arr.reindex(**{dim: reversed_dim_idx})
                    arr = arr.interpolate_na(dim=dim, limit=10, keep_attrs=True)
                    arr = arr.reindex(**{dim: dim_idx})
                except ValueError:
                    pass

            return arr

        # Get .img file path (readable by rasterio)
        try:
            img = rasters.get_dim_img_path(dim_path, f"*{pol}*")
        except FileNotFoundError:
            img = rasters.get_dim_img_path(dim_path)  # Maybe not the good name

        # Open SAR image
        with rioxarray.open_rasterio(str(img)) as arr:
            arr = arr.where(arr != self._snap_no_data, np.nan)

            # Interpolate if needed (interpolate na works only 1D-like, sadly)
            # DSPK step in done on already interpolated data
            if not dspk and kwargs.get(SAR_INTERP_NA, False):
                arr = interp_na(arr, dim="y")
                arr = interp_na(arr, dim="x")

            # Save the file as the terrain-corrected image
            file_path = os.path.join(
                self._get_band_folder(writable=True),
                f"{files.get_filename(dim_path)}_{pol}{'_DSPK' if dspk else ''}.tif",
            )
            # WARNING: Set nodata to 0 here as it is the value wanted by SNAP !
            utils.write(arr, file_path, dtype=np.float32, nodata=self._snap_no_data)

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
            >>> from eoreader.bands import *
            >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_cloud_band(CLOUDS)
            False
        """
        return False

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_{constellation}_{polarization}_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed name
        """
        pol_chan = [pol.value for pol in self.pol_channels]
        return f"{self.get_datetime()}_{self.constellation.name}_{'_'.join(pol_chan)}_{self.sensor_mode.name}_{self.product_type.value}"

    def _update_attrs_constellation_specific(
        self, xarr: xr.DataArray, bands: list, **kwargs
    ) -> xr.DataArray:
        """
        Update attributes of the given array (constellation specific)

        Args:
            xarr (xr.DataArray): Array whose attributes need an update
            bands (list): Array name (as a str or a list)
        Returns:
            xr.DataArray: Updated array
        """

        return xarr

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        return [
            f"\torbit direction: {self.get_orbit_direction().value}",
        ]
