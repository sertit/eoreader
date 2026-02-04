# Copyright 2026, SERTIT-ICube - France, https://sertit.unistra.fr/
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
"""Super class for SAR products"""

import logging
import os
import tempfile
import xml.etree.ElementTree as ET
from abc import abstractmethod
from enum import unique
from string import Formatter

import geopandas as gpd
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from affine import Affine
from rasterio import CRS, crs
from rasterio.enums import Resampling
from rasterio.windows import Window
from sertit import AnyPath, geometry, misc, path, rasters, snap, strings, types, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType
from sertit.vectors import WGS84
from shapely.geometry.polygon import Polygon

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import BandNames, SarBand, SarBandMap
from eoreader.bands import SarBandNames as sab
from eoreader.env_vars import (
    DEM_PATH,
    DSPK_GRAPH,
    PP_GRAPH,
    SAR_DEF_PIXEL_SIZE,
    SNAP_DEM_NAME,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.keywords import SAR_INTERP_NA, WRITE_LIA_KW
from eoreader.products.product import Product, SensorType
from eoreader.reader import Constellation
from eoreader.stac import INTENSITY
from eoreader.utils import simplify

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
    Generic products types, used to choose a SNAP graph.
    """

    CPLX = "COMPLEX"
    """Complex image (most likely Single Look Complex)"""

    GRD = "GROUND RANGE"
    """Ground Range image"""

    GEOCODED = "GEOCODED"
    """Already geocoded image: don't need SNAP. To orthorectify it, you may need to take GCP by hand..."""

    ORTHO = "ORTHO"
    """Already orthorecified image: don't need SNAP"""

    OTHER = "OTHER"
    """Other products types, not used in EOReader"""


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
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
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

        self.nof_swaths = None
        """Number of swaths of the current SAR product"""

        # Private attributes
        self._band_folder = None
        self._raw_band_regex = None
        self._snap_no_data = 0
        self._raw_no_data = 0

        self._need_snap = None

        # Calibrate or not
        self._calibrate = True

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

        self._need_snap = self._need_snap_to_pre_process()
        self.is_ortho = self.sar_prod_type == SarProductType.ORTHO

    def _map_bands(self) -> None:
        """
        Map bands
        """
        self.bands.map_bands(
            {
                band_name: SarBand(
                    eoreader_name=band_name,
                    name=band_name.name,
                    gsd=self.pixel_size,
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

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self._set_sensor_mode()
        self.pol_channels = self._get_raw_bands()

    @cache
    def get_snap_version(self):
        return snap.get_snap_version()

    @cache
    def _has_snap_x_or_higher(self, version: int) -> bool:
        """True if SNAP version is 10 or higher"""
        return misc.compare_version(self.get_snap_version(), f"{version}.0.0", ">=")

    def _get_predictor(self) -> int:
        """
        Set LZW predictor to 1 in order to SNAP to be able to read this GeoTiff (in despeckle operations mostly).
        Else set to 3.

        Caused by: javax.imageio.IIOException: Illegal value for Predictor in TIFF file

        This is related to JAVA imageio library, not SNAP directly, so be sure to have imageio up-to-date to set 3.
        For now, it is unknown to know if imageio handles predictor = 3, so live it to 1.

        """
        # If we could know if imageio handles Predictor=3:
        # # 3 for float if handled
        pred = 3 if self._has_snap_x_or_higher(13) else 1
        LOGGER.debug(f"SAR predictor: {pred} (SNAP version: {self.get_snap_version()})")
        return pred

    def _need_snap_to_pre_process(self):
        """This product needs SNAP for pre-process."""
        need_snap = self.sar_prod_type in [SarProductType.CPLX, SarProductType.GRD]
        return need_snap

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
        if self.is_ortho:
            default_band_path = self.get_raw_band_paths()[self.get_default_band()]
        else:
            default_band_path = self.get_default_band_path()

        # Processed by SNAP: the nodata is set -> use get_footprint instead of vectorize
        downsampled_band = utils.read(
            default_band_path,
            pixel_size=max(
                self.resolution * 10, float(os.environ.get(SAR_DEF_PIXEL_SIZE, 0))
            ),
        )
        return rasters.get_footprint(downsampled_band)

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
        if self.is_ortho:
            default_band_path = self.get_raw_band_paths(**kwargs)[
                self.get_default_band()
            ]
        else:
            default_band_path = self.get_default_band_path(**kwargs)

        with rasterio.open(str(default_band_path)) as dst:
            return dst.transform, dst.width, dst.height, dst.crs

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

    @cache
    def get_default_band_path(self, **kwargs) -> AnyPathType:
        """
        Get default band path (the first existing one between :code:`VV` and :code:`HH` for SAR data), ready to use (orthorectified)

        .. WARNING:: This functions orthorectifies SAR bands if not existing!

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
            AnyPathType: Default band path
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
        if self.is_ortho:
            return super().extent()
        else:
            # Get WGS84 extent
            extent_wgs84 = self.wgs84_extent()

            # Convert to UTM
            return extent_wgs84.to_crs(self.crs())

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
        if self.is_ortho:
            with rasterio.open(
                str(self.get_raw_band_paths()[self.get_default_band()])
            ) as ds:
                return ds.crs
        else:
            # Get WGS84 extent
            extent_wgs84 = self.wgs84_extent()

            # Estimate UTM from extent
            return extent_wgs84.estimate_utm_crs()

    @abstractmethod
    def _set_sensor_mode(self) -> None:
        """
        Set SAR sensor mode
        """
        raise NotImplementedError

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: This functions orthorectifies and despeckles SAR bands if not existing!

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
            pixel_size (float): Band pixel size
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        # Allow using the SNAP PIXEL SIZE if given (and not overridden by a pixel size)
        if pixel_size is None:
            pixel_size = float(os.environ.get(SAR_DEF_PIXEL_SIZE, self.pixel_size))

        band_paths = {}
        for band in band_list:
            if self.bands[band] is None:
                raise InvalidProductError(
                    f"Non existing band ({band.name}) for {self.name}"
                )

            ortho_band, ortho_exists = self._is_existing(
                self.get_band_file_name(band, pixel_size, **kwargs)
            )

            if ortho_exists:
                band_paths[band] = ortho_band
            else:
                # Two options here:
                # - Non-existing band is a speckle band -> only need to pre-process it
                # - Non-existing band is a despeckled band -> make sure the speckle band is pre-processed before trying to despeckle it
                speckle_band = sab.corresponding_speckle(band)
                if speckle_band in self.pol_channels:
                    # Non-existing band is a despeckled band -> make sure the speckle band is pre-processed before trying to despeckle it
                    if sab.is_despeckle(band):
                        # Check if existing speckle ortho band
                        speckle_ortho_band, speckle_ortho_exists = self._is_existing(
                            self.get_band_file_name(speckle_band, pixel_size, **kwargs)
                        )
                        if not speckle_ortho_exists:
                            self._pre_process_sar(
                                speckle_ortho_band, speckle_band, pixel_size, **kwargs
                            )

                        # Despeckle the noisy band
                        band_paths[band] = self._despeckle_sar(
                            ortho_band, speckle_band, pixel_size, **kwargs
                        )
                    # Non-existing band is a speckle band -> only need to pre-process it
                    else:
                        band_paths[band] = self._pre_process_sar(
                            ortho_band, band, pixel_size, **kwargs
                        )

        return band_paths

    @cache
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
                        band_paths[band] = self._get_archived_rio_path(
                            band_regex.replace("*", ".*") + "$", as_list=True
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
                    band_paths[band] = path.get_file_in_dir(
                        self._band_folder, band_regex, exact_name=True, get_list=True
                    )[0]
                    # Get as a list but keep only the first item (S1-SLC with 3 swaths)
                except FileNotFoundError:
                    continue

        return band_paths

    @cache
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

        .. WARNING:: This functions orthorectifies SAR bands if not existing!

        .. WARNING:: This functions despeckles SAR bands if not existing!

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

    def _read_band(
        self,
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: tuple | list | float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            pixel_size (tuple | list | float): Size of the pixels of the wanted band, in dataset unit (X, Y)
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        # TODO: check if that works
        # In case of data that doesn't have any known pixel_size
        if self.pixel_size < 0.0:
            with rasterio.open(str(band_path)) as ds:
                self.pixel_size = ds.res[0]

        try:
            if pixel_size < 0.0:
                pixel_size = self.pixel_size
        except TypeError:
            pass

        band_arr = utils.read(
            band_path,
            pixel_size=pixel_size,
            size=size,
            resampling=kwargs.pop("resampling", self.band_resampling),
            as_type=np.float32,
            **kwargs,
        )

        # Write file (in case the original file has a different resolution or window, etc.)
        file_path, exists = self._is_existing(
            self.get_band_file_name(band, pixel_size=pixel_size, size=size, **kwargs)
        )
        if not exists:
            band_arr = utils.write_path_in_attrs(band_arr, file_path)
            utils.write(
                band_arr,
                file_path,
                dtype=np.float32,
                nodata=self._snap_no_data,
                predictor=self._get_predictor(),
                driver="GTiff",  # SNAP doesn't handle COGs very well apparently
            )
        return band_arr

    def _load_bands(
        self,
        bands: list | BandNames,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            pixel_size (float): Band pixel size in meters
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band is specified
        if not bands:
            return {}

        # Get band paths
        bands = types.make_iterable(bands)

        band_paths = self.get_band_paths(bands, pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band_name, band_path in band_paths.items():
            # Read SAR band
            band_arrays[band_name] = self._read_band(
                band_path, band_name, pixel_size=pixel_size, size=size, **kwargs
            )

        return band_arrays

    def _pre_process_no_snap(
        self,
        pre_processed_path: AnyPathType,
        band: sab,
        pixel_size: float = None,
        **kwargs,
    ) -> AnyPathType:
        """
        Pre-process SAR data without SNAP -> no need of orthorectification

        Args:
            pre_processed_path (AnyPathType): Pre-processed path
            band (sbn): Band to preprocess
            pixel_size (float): Pixel size
            kwargs: Additional arguments

        Returns:
            AnyPathType: Band path
        """
        LOGGER.debug("Pre-processing file without SNAP")

        # Set the nodata and write the image where they belong
        raw_band_path = self.get_raw_band_paths(**kwargs)[band]
        arr = utils.read(
            raw_band_path,
            pixel_size=pixel_size if pixel_size != 0 else None,
            masked=False,
            **kwargs,
        )
        arr = arr.where(arr != self._raw_no_data, np.nan)

        arr = utils.write_path_in_attrs(arr, pre_processed_path)
        utils.write(
            arr,
            pre_processed_path,
            dtype=np.float32,
            nodata=self._snap_no_data,
            predictor=self._get_predictor(),
            driver="GTiff",  # SNAP doesn't handle COGs very well apparently
        )
        return pre_processed_path

    def _get_pp_graph(
        self,
        write_lia: bool = False,
        tmp_dir: str = None,
        fallback_no_calib: bool = False,
    ) -> str:
        """Get the pre-processing graph"""
        if PP_GRAPH not in os.environ:
            if self.constellation_id == Constellation.S1.name:
                sat = "s1"
                if self.sensor_mode.value == "SM":
                    sat += "_sm"
            elif fallback_no_calib or not self._calibrate:
                sat = "no_calib"
            else:
                sat = "sar"
            spt = "grd" if self.sar_prod_type == SarProductType.GRD else "cplx"

            # Remove LIA nodes from graph
            # This is buggy right now with SNAP 13, merge this once new version is released
            # if not write_lia:
            #     pp_graph = self._prepare_graph_no_lia(tmp_dir, pp_graph)

            if write_lia:
                pp_graph = (
                    utils.get_data_dir() / "lia" / f"{spt}_{sat}_preprocess_default.xml"
                )
            else:
                pp_graph = utils.get_data_dir() / f"{spt}_{sat}_preprocess_default.xml"

        else:
            pp_graph = AnyPath(os.environ[PP_GRAPH]).resolve()
            if not pp_graph.is_file() or pp_graph.suffix != ".xml":
                raise FileNotFoundError(f"{pp_graph} cannot be found.")

        return str(pp_graph)

    def _prepare_graph_no_lia(self, tmp_dir, graph_path: str) -> str:
        """
        Prepare a SNAP graph without Local Incidence Angle (LIA) processing.

        This removes the ``BandSelect_LIA`` and ``Write_LIA`` nodes and writes the
        modified graph to a temporary directory.

        Args:
            tmp_dir: Temp directory
            graph_path (str): Path to the original SNAP graph.

        Returns:
            str: Path to the modified graph saved in a temporary directory.
        """
        tree = ET.parse(graph_path)
        root = tree.getroot()

        # Node IDs to remove
        remove_ids = {"BandSelect_LIA", "Write_LIA"}

        # Remove matching nodes, ignoring if they don't exist
        for node in list(root.findall("node")):
            if node.get("id") in remove_ids:
                root.remove(node)

        # Write modified graph to temporary directory
        new_graph_path = os.path.join(
            tmp_dir, path.get_filename(graph_path) + "_no_lia.xml"
        )
        tree.write(new_graph_path, encoding="utf-8", xml_declaration=True)

        return new_graph_path

    def _get_dem(self) -> (str, str):
        """Get the DEM used by SNAP for orthorectification in Terrain Coprrection operator."""
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

        return dem_name, dem_path

    def _get_snap_path(
        self, tmp_dir: str, file_path: AnyPathStrType = None, **kwargs
    ) -> AnyPathType:
        """
        Get the SNAP-compatible product path.

        WARNING: this can trigger the download of the product if stored on the cloud!

        Args:
            tmp_dir (str): Temporary directory, where to download the product if stored on the cloud
            **kwargs: Other args

        Returns:
            AnyPathType: SNAP-compatible product path
        """
        # Download cloud path to cache
        prod_path = kwargs.get("prod_path")
        if prod_path is None:
            if path.is_cloud_path(self.path):
                cached_path = os.path.join(tmp_dir, self.path.name)
                if not os.path.exists(cached_path):
                    LOGGER.debug(f"Caching {self.path} to {cached_path}")
                    self.path.download_to(cached_path)

                prod_path = os.path.join(cached_path, self.snap_filename)
            else:
                prod_path = self.path.joinpath(self.snap_filename)

        return prod_path

    def _get_subset(self, **kwargs) -> (str, str):
        """Get the subset to be applied"""
        window = kwargs.get("window")
        window_to_crop = None

        # By default, use the whole product
        geo_region_gdf = ""
        region = ""  # The 'geoRegion' parameter has precedence over this parameter.

        if isinstance(window, Window):
            geo_region_gdf = None
            region = f"{window.col_off},{window.row_off},{window.width},{window.height}"
            window_to_crop = window
        elif path.is_path(window):
            geo_region_gdf = vectors.read(window)
            window_to_crop = geo_region_gdf
        else:
            geo_region_gdf = window
            window_to_crop = window

        if geo_region_gdf is None:
            geo_region = ""
        else:
            try:
                # Take a buffer to prevent border effects from terrain correction
                geo_region_gdf = geometry.buffer(
                    geo_region_gdf.to_crs(self.crs()), 1000, resolution=2
                )
                geo_region = geo_region_gdf.to_crs(WGS84).geometry.to_wkt().iat[0]
            except Exception as exc:
                raise NotImplementedError(
                    "Window should either be a GeoDataFrame, readable as a vector or set to None. Bounds, tuple, list and 'rasterio.Window' are not supported."
                ) from exc

        return geo_region, region, window_to_crop

    def _get_resolution(self, pixel_size: float) -> (float, float):
        # Compute resolution in degrees
        # See https://step.esa.int/main/doc/online-help/?helpid=RangeDopplerGeocodingOp&version=11.0.0
        equatorial_earth_radius = 6378137.0
        res_deg = pixel_size / equatorial_earth_radius * 180 / np.pi
        return pixel_size, res_deg

    def _already_processed_path(
        self, band: sab, pixel_size: float = None, **kwargs
    ) -> AnyPathType:
        """
        Check if an acceptable orthorectified file already exists on disk

        Args:
            band (sbn): Band to preprocess
            pixel_size (float): Pixel size
            kwargs: Additional arguments

        Returns:
            AnyPathType: Band path
        """
        already_ortho = None
        # Check if the image has been orthorectified without a window.
        # If so, don't redo the ortho with SNAP, only read the ortho image with the window
        # This makes a discrepancy between windowed read with pixels between subset and read, but is this bad?
        # Let's assume it's not
        no_window_ortho_path, no_window_ortho_exists = self._is_existing(
            self.get_band_file_name(
                band,
                pixel_size,
                **utils._prune_keywords(additional_keywords=["window"], **kwargs),
            )
        )

        if no_window_ortho_exists:
            already_ortho = no_window_ortho_path
        else:
            # Check if an ortho band with a better resolution exists (and for legacy purposes, without any resolution)
            # If so, use it instead of re-orthorectifying bands
            no_res_name = f"{self.condensed_name}_{self.bands[band].id}*"
            no_res_files = list(
                self._get_band_folder(writable=True).glob(no_res_name)
            ) + list(self._get_band_folder(writable=False).glob(no_res_name))

            if len(no_res_files) > 0:
                for no_res_file in no_res_files:
                    # Discard despeckled file
                    if (
                        sab.is_speckle(band)
                        and sab.corresponding_despeckle(band).name in no_res_file.name
                    ):
                        continue
                    filename = path.get_filename(no_res_file)
                    split_name = filename.split("_")
                    if pixel_size is not None and "m" in split_name[-1]:
                        # Check if resolution is better than the one asked
                        file_res = float(
                            split_name[-1].replace("m", "").replace("-", ".")
                        )
                        if file_res <= pixel_size:
                            LOGGER.debug(
                                f"Deriving {band.name} at {pixel_size} m from {filename}."
                            )
                            already_ortho = no_res_file
                            break
                    elif filename == no_res_name:
                        # No resolution, take it (for legacy purposes)
                        LOGGER.debug(
                            f"Deriving {band.name} at {pixel_size} m from {filename}."
                        )
                        already_ortho = no_res_file
                        break

        return already_ortho

    def _pre_process_snap(
        self,
        pre_processed_path: AnyPathType,
        band: sab,
        pixel_size: float = None,
        **kwargs,
    ) -> AnyPathType:
        """
        Pre-process SAR data with SNAP (needs orthorectification, calibration, etc.)

        Args:
            pre_processed_path (AnyPathType): Pre-processed path
            band (sbn): Band to preprocess
            pixel_size (float): Pixel size
            kwargs: Additional arguments

        Returns:
            AnyPathType: Band path
        """
        # Manage pixel size used for Terrain correction
        # This is not the pixel size used for reading the file!
        # It is possible to orthorectify the image at 20 m but read it at 10 m
        def_snap_pixel_size = float(os.environ.get(SAR_DEF_PIXEL_SIZE, 0))
        snap_pixel_size = (
            pixel_size
            if (pixel_size and pixel_size != self.pixel_size)
            else def_snap_pixel_size
        )
        already_ortho = self._already_processed_path(band, snap_pixel_size, **kwargs)
        if already_ortho is not None:
            return already_ortho
        else:
            # Create target dir (tmp dir)
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Use dimap for speed and security (i.e. GeoTiff's broken georef)
                pp_target = os.path.join(tmp_dir, f"{self.condensed_name}")
                pp_dim = pp_target + ".dim"

                write_lia = kwargs.get(WRITE_LIA_KW, False)

                # Pre-process graph
                pp_graph = self._get_pp_graph(write_lia, tmp_dir)

                # Get DEM for orthorectification
                dem_name, dem_path = self._get_dem()

                # Get the product path, compatible with SNAP
                # WARNING: this can trigger the download of the product if stored on the cloud!
                prod_path = self._get_snap_path(tmp_dir, **kwargs)

                # Manage subset
                geo_region, region, window_to_crop = self._get_subset(**kwargs)

                # Get resolution
                res_m, res_deg = self._get_resolution(snap_pixel_size)

                # Create SNAP CLI
                snap_args = [
                    f"-Pfile={strings.to_cmd_string(prod_path)}",
                    f"-Pgeo_region={strings.to_cmd_string(geo_region)}",
                    f"-Pregion={strings.to_cmd_string(region)}",
                    f"-Pcalib_pola={strings.to_cmd_string(band.name)}",
                    f"-Pdem_name={strings.to_cmd_string(dem_name.value)}",
                    f"-Pdem_path={strings.to_cmd_string(dem_path)}",
                    f"-Pcrs={self.crs()}",
                    f"-Pres_m={res_m}",
                    f"-Pres_deg={res_deg}",
                    f"-Pwrite_lia={write_lia}",
                    f"-Pout={strings.to_cmd_string(pp_dim)}",
                ]
                cmd_list = snap.get_gpt_cli(
                    pp_graph,
                    snap_args,
                    display_snap_opt=LOGGER.level == logging.DEBUG,
                )

                # Pre-process SAR images according to the given graph
                LOGGER.debug("Pre-process SAR image")
                try:
                    misc.run_cli(cmd_list)

                    # Check the BEAM-DIMAP output exists (if not, trigger CSK fallback)
                    assert AnyPath(pp_dim).suffix == ".dim", (
                        f"Assert {pp_dim} is written in BEAM-DIMAP"
                    )
                    assert AnyPath(pp_dim).is_dir(), f"Assert {pp_dim} is a directory"

                # With SNAP 13.0.0, there is an issue with CSK and calibration:
                # - no output is written for DGM
                # - GPT graph fails for SCS
                # Add this fallback for the moment
                except AssertionError as ex:
                    self._fallback_csk_snap_13(write_lia, tmp_dir, snap_args, ex)
                except RuntimeError as ex:
                    if self.constellation == Constellation.CSK:
                        self._fallback_csk_snap_13(write_lia, tmp_dir, snap_args, ex)
                    else:
                        raise RuntimeError("Something went wrong with SNAP!") from ex

                # Convert Local Incidence Angle files from DIMAP to GeoTiff
                if write_lia:
                    LOGGER.debug(
                        "Converting Local Incidence Angle files from DIMAP to GeoTiff"
                    )
                    self._write_lia(
                        pre_processed_path, pp_dim, crop=window_to_crop, **kwargs
                    )

                # Convert DIMAP images to GeoTiff
                LOGGER.debug("Converting DIMAP to GeoTiff")

                return self._write_sar(
                    pre_processed_path, pp_dim, band, crop=window_to_crop, **kwargs
                )

    def _fallback_csk_snap_13(self, write_lia: bool, tmp_dir, snap_args, ex):
        """
        With SNAP 13.0.0, there is an issue with CSK and calibration
        Apply this fallback until it's resolved
        """
        LOGGER.debug(ex)
        LOGGER.warning(
            "There is an issue with CSK and calibration with SNAP 13.0.0. "
            "This step is removed to make the computation work nevertheless. "
            "Please be aware that the result may be degraded."
        )
        pp_graph = self._get_pp_graph(write_lia, tmp_dir, fallback_no_calib=True)
        cmd_list = snap.get_gpt_cli(
            pp_graph,
            snap_args,
            display_snap_opt=LOGGER.level == logging.DEBUG,
        )
        try:
            misc.run_cli(cmd_list)
        except RuntimeError as ex:
            raise RuntimeError("Something went wrong with SNAP!") from ex

    def _pre_process_sar(
        self,
        pre_processed_path: AnyPathType,
        band: sab,
        pixel_size: float = None,
        **kwargs,
    ) -> AnyPathType:
        """
        Pre-process SAR data (geocoding...)

        Args:
            pre_processed_path (AnyPathType): Pre-processed path
            band (sbn): Band to preprocess
            pixel_size (float): Pixel size
            kwargs: Additional arguments

        Returns:
            AnyPathType: Band path
        """
        if not self._need_snap:
            pre_process_fct = self._pre_process_no_snap
        else:
            pre_process_fct = self._pre_process_snap

        return pre_process_fct(pre_processed_path, band, pixel_size, **kwargs)

    def _despeckle_sar(
        self, despeckled_path: AnyPathType, band: sab, pixel_size, **kwargs
    ) -> AnyPathType:
        """
        Pre-process SAR data (geocode...)

        Args:
            despeckled_path (AnyPathType): Pre-processed path
            band (sbn): Band to despeckle
            kwargs: Additional arguments

        Returns:
            AnyPathType: Despeckled path
        """
        already_dspk = self._already_processed_path(band, pixel_size, **kwargs)
        if already_dspk is not None:
            return already_dspk

        # Create target dir (tmp dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Out files
            target_file = os.path.join(tmp_dir, f"{self.condensed_name}")
            dspk_dim = target_file + ".dim"

            # Despeckle graph
            if DSPK_GRAPH not in os.environ:
                dspk_graph = utils.get_data_dir().joinpath("sar_despeckle_default.xml")
            else:
                dspk_graph = AnyPath(os.environ[DSPK_GRAPH]).resolve()
                if not dspk_graph.is_file() or dspk_graph.suffix != ".xml":
                    raise FileNotFoundError(f"{dspk_graph} cannot be found.")

            # Create command line and run it
            if not os.path.isfile(dspk_dim):
                spk_path = self.get_band_path(band, writable=True, **kwargs)

                cmd_list = snap.get_gpt_cli(
                    str(dspk_graph),
                    [f"-Pfile={spk_path}", f"-Pout={dspk_dim}"],
                    display_snap_opt=False,
                )

                # Pre-process SAR images according to the given graph
                LOGGER.debug(f"Despeckling {band.name}")
                try:
                    misc.run_cli(cmd_list)
                except RuntimeError as ex:
                    raise RuntimeError("Something went wrong with SNAP!") from ex

            # Convert DIMAP images to GeoTiff
            out = self._write_sar(
                despeckled_path, dspk_dim, sab.corresponding_despeckle(band), **kwargs
            )

        return out

    def _find_beam_dimaps(self, dim_path, pol) -> list:
        try:
            imgs = utils.get_dim_img_path(dim_path, f"*{pol}*")
            LOGGER.debug(f"Found {imgs} sub-images (for {pol}).")
        except FileNotFoundError:
            LOGGER.debug(f"No {pol} image found in {dim_path}")
            imgs = utils.get_dim_img_path(dim_path)  # Maybe not a good name
            LOGGER.debug(f"Using {imgs} instead")

        return imgs

    def _write_sar(
        self, out_path: AnyPathType, dim_path: str, band: sab, **kwargs
    ) -> AnyPathType:
        """
        Write SAR image on disk.

        Args:
            out_path (AnyPathType): Out path
            dim_path (str): DIMAP path
            band (sab): Band
            kwargs: Additional arguments

        Returns:
            AnyPathType: SAR path
        """
        LOGGER.debug("Write SAR")
        # Save the file as the terrain-corrected image
        # input data
        band_id = self.bands[band].id
        dspk_suffix = "_DSPK"
        dspk = dspk_suffix in band_id
        pol = band_id.replace(dspk_suffix, "")

        def interp_na(array, dim):
            try:
                array = array.interpolate_na(dim=dim, limit=10, keep_attrs=True)
            except ValueError:
                try:
                    # ValueError: Index 'y' must be monotonically increasing
                    dim_idx = getattr(array, dim)
                    reversed_dim_idx = list(reversed(dim_idx))
                    array = array.reindex(**{dim: reversed_dim_idx})
                    array = array.interpolate_na(dim=dim, limit=10, keep_attrs=True)
                    array = array.reindex(**{dim: dim_idx})
                except ValueError:
                    pass

            return array

        # Get the .img path(s)
        imgs = self._find_beam_dimaps(dim_path, pol)

        # Manage cases where multiple swaths are ortho independently
        if len(imgs) > 1:
            mos_path, exists = self._get_out_path(
                path.get_filename(dim_path) + f"_mos_{pol}.vrt"
            )
            if not exists:
                # Get .img file path (readable by rasterio)

                # Useful for PAZ SC data (multiswath)
                rasters.merge_vrt(imgs, mos_path)
        else:
            mos_path = imgs[0]

        # Open SAR image and convert it to a clean geotiff
        with rioxarray.open_rasterio(mos_path) as arr:
            arr = arr.where(arr != self._snap_no_data, np.nan)

            # Interpolate if needed (interpolate na works only 1D-like, sadly)
            # DSPK step in done on already interpolated data
            if not dspk and kwargs.get(SAR_INTERP_NA, False):
                arr = interp_na(arr, dim="y")
                arr = interp_na(arr, dim="x")

            crop_window = kwargs.get("crop")
            if crop_window is not None:
                if isinstance(crop_window, Window):
                    arr = arr.rio.isel_window(crop_window)
                else:
                    arr = rasters.crop(arr, crop_window)

            # WARNING: Set nodata to 0 here as it is the value wanted by SNAP!
            arr = utils.write_path_in_attrs(arr, out_path)
            utils.write(
                arr,
                out_path,
                dtype=np.float32,
                nodata=self._snap_no_data,
                predictor=self._get_predictor(),
                driver="GTiff",  # SNAP doesn't handle COGs very well apparently
            )

        return out_path

    def _write_lia(self, out_path: AnyPathType, dim_path: str, **kwargs) -> AnyPathType:
        """
        Write Local Incidence Angle images on disk.

        Args:
            out_path (AnyPathType): Out path
            dim_path (str): DIMAP path
            kwargs: Additional arguments

        Returns:
            AnyPathType: SAR path
        """
        LOGGER.debug("Write LIA")
        # Save the file as the terrain-corrected image
        # input data

        def interp_na(array, dim):
            try:
                array = array.interpolate_na(dim=dim, limit=10, keep_attrs=True)
            except ValueError:
                try:
                    # ValueError: Index 'y' must be monotonically increasing
                    dim_idx = getattr(array, dim)
                    reversed_dim_idx = list(reversed(dim_idx))
                    array = array.reindex(**{dim: reversed_dim_idx})
                    array = array.interpolate_na(dim=dim, limit=10, keep_attrs=True)
                    array = array.reindex(**{dim: dim_idx})
                except ValueError:
                    pass

            return array

        # Get the .img path(s)
        imgs = []
        try:
            imgs = utils.get_dim_img_path(dim_path, "*Incidence*")
        except FileNotFoundError:
            LOGGER.warning(
                "No Local Incidence Angle file found. Please activate the options to write these files from 'Terrain-Correction' node in a custuom SNAP graph"
            )

        for img in imgs:
            base_name = out_path.stem
            lia_out_path = out_path.parent / f"{base_name}_localIncidenceAngle.tif"

            # Open Local Incidence Angle image and convert it to a clean geotiff
            with rioxarray.open_rasterio(img) as arr:
                arr = arr.where(arr != self._snap_no_data, np.nan)

                # Interpolate if needed (interpolate na works only 1D-like, sadly)
                if kwargs.get(SAR_INTERP_NA, False):
                    arr = interp_na(arr, dim="y")
                    arr = interp_na(arr, dim="x")

                crop_window = kwargs.get("crop")
                if crop_window is not None:
                    if isinstance(crop_window, Window):
                        arr = arr.rio.isel_window(crop_window)
                    else:
                        arr = rasters.crop(arr, crop_window)

                # WARNING: Set nodata to 0 here as it is the value wanted by SNAP!
                # SNAP < 10.0.0 fails with classic predictor !!! Set the predictor to the default value (1) !!!
                # Caused by: javax.imageio.IIOException: Illegal value for Predictor in TIFF file
                arr = utils.write_path_in_attrs(arr, lia_out_path)
                utils.write(
                    arr,
                    lia_out_path,
                    dtype=np.float32,
                    nodata=self._snap_no_data,
                    predictor=self._get_predictor(),
                    driver="GTiff",  # SNAP doesn't handle COGs very well apparently
                )

        return lia_out_path

    def _compute_hillshade(
        self,
        dem_path: str = "",
        pixel_size: float | tuple = None,
        size: list | tuple = None,
        resampling: Resampling = Resampling.bilinear,
    ) -> AnyPathType:
        """
        Compute Hillshade mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            pixel_size (float | tuple): Pixel size in meters. If not specified, use the product pixel size.
            resampling (Resampling): Resampling method
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
        Returns:
            AnyPathType: Hillshade mask path
        """
        raise InvalidProductError("Impossible to compute hillshade mask for SAR data.")

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band?

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
            xr.DataArray: Updated array/dataset
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

    def _fallback_wgs84_extent(self, extent_file_name: str = None) -> gpd.GeoDataFrame:
        """
        Fallback for wgs84 extent (slower than to read a file, but should work in almost any case)

        Args:
            extent_file_name (str): Extent file name, if existing

        Returns:
            gpd.GeoDataFrame: WGS84 extent
        """
        with rasterio.open(
            str(self.get_raw_band_paths()[self.get_default_band()])
        ) as ds:
            if ds.crs is not None:
                extent_wgs84 = gpd.GeoDataFrame(
                    geometry=[geometry.from_bounds_to_polygon(*ds.bounds)],
                    crs=ds.crs,
                )
            elif ds.gcps is not None:
                gcps, crs = ds.gcps
                corners = geometry.from_bounds_to_polygon(*ds.bounds).exterior.coords
                extent_poly = Polygon(
                    [rasterio.transform.from_gcps(gcps) * corner for corner in corners]
                )
                extent_wgs84 = gpd.GeoDataFrame(geometry=[extent_poly], crs=crs)
            else:
                name = f"({extent_file_name}) " if extent_file_name else ""

                raise InvalidProductError(
                    f"Extent file {name}not found in {self.path}. "
                    "Default band isn't georeferenced and have no GCPs. "
                    "It is therefore impossible to determine quickly the extent of this product. "
                    "Please write an issue on GitHub!"
                )
        return extent_wgs84
