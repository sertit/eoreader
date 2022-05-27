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
""" Super class for optical products """
import logging
from abc import abstractmethod
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from cloudpathlib import AnyPath, CloudPath
from rasterio import crs as riocrs
from rasterio.enums import Resampling
from sertit import files, rasters
from sertit.misc import ListEnum

from eoreader import cache, utils
from eoreader.bands import BandNames, SpectralBandMap
from eoreader.bands import SpectralBandNames as spb
from eoreader.bands import (
    indices,
    is_clouds,
    is_dem,
    is_index,
    is_sar_band,
    is_spectral_band,
    to_str,
)
from eoreader.exceptions import InvalidBandError, InvalidIndexError
from eoreader.keywords import CLEAN_OPTICAL, TO_REFLECTANCE
from eoreader.products.product import OrbitDirection, Product, SensorType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CleanMethod(ListEnum):
    """
    Cleaning method for optical bands
    """

    CLEAN = "clean"
    """
    Clean everything that can be cleaned (nodata, saturated pixels, cosmic rays, broken detectors...).
    Default method but slowest.
    """

    NODATA = "nodata"
    """
    Clean only the detector nodata (nan outside the detector footprint).
    A bit faster than the previous method.
    """

    RAW = "raw"
    """ Return raw band without any cleaning (fastest method) """


DEF_CLEAN_METHOD = CleanMethod.NODATA


class OpticalProduct(Product):
    """Super class for optical products"""

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._has_cloud_cover = False

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # They may be overloaded
        if not self.bands:
            self.bands = SpectralBandMap()
        self.sensor_type = SensorType.OPTICAL

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self._set_product_type()

    def get_default_band(self) -> BandNames:
        """
        Get default band: :code:`GREEN` for optical data as every optical satellite has a GREEN band.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band()
            <SpectralBandNames.GREEN: 'GREEN'>

        Returns:
            str: Default band
        """
        return spb.GREEN

    def get_default_band_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get default band (:code:`GREEN` for optical data) path.

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
        default_band = self.get_default_band()
        return self.get_band_paths([default_band], **kwargs)[default_band]

    @cache
    def crs(self) -> riocrs.CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.crs()
            CRS.from_epsg(32630)

        Returns:
            rasterio.crs.CRS: CRS object
        """
        band_path = self.get_default_band_path()
        with rasterio.open(str(band_path)) as dst:
            utm = dst.crs

        return utm

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.extent()
                                                        geometry
            0  POLYGON ((309780.000 4390200.000, 309780.000 4...

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get extent
        return rasters.get_extent(self.get_default_band_path()).to_crs(self.crs())

    def get_existing_bands(self) -> list:
        """
        Return the existing band.

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
        return [name for name, nb in self.bands.items() if nb]

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
        existing_bands = self.get_existing_bands()
        return self.get_band_paths(band_list=existing_bands)

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        path: Union[Path, CloudPath],
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        raise NotImplementedError

    def _open_bands(
        self,
        band_paths: dict,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Open bands from disk.

        Args:
            band_paths (dict): Band dict: {band_enum: band_path}
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary {band_name, band_xarray}

        """
        # Open bands and get array (resampled if needed)
        band_arrays = {}
        for band, band_path in band_paths.items():
            # Read band
            LOGGER.debug(f"Read {band.name}")
            band_arr = self._read_band(
                band_path, band=band, resolution=resolution, size=size, **kwargs
            )

            if not resolution:
                resolution = band_arr.rio.resolution()[0]
            clean_band_path = self._get_clean_band_path(
                band, resolution=resolution, writable=True, **kwargs
            )
            # If raw data, clean it !
            if AnyPath(band_path).name != clean_band_path.name:
                # Manage reflectance
                if kwargs.get(TO_REFLECTANCE, True):
                    LOGGER.debug(f"Converting {band.name} to reflectance")
                    band_arr = self._to_reflectance(band_arr, band_path, band)

                # Clean pixels
                cleaning_method = CleanMethod.from_value(
                    kwargs.get(CLEAN_OPTICAL, DEF_CLEAN_METHOD)
                )
                if cleaning_method == CleanMethod.RAW:
                    pass
                elif cleaning_method == CleanMethod.NODATA:
                    LOGGER.debug(f"Manage nodata for band {band.name}")
                    band_arr = self._manage_nodata(band_arr, band=band, **kwargs)
                else:
                    LOGGER.debug(f"Manage invalid pixels for band {band.name}")
                    band_arr = self._manage_invalid_pixels(
                        band_arr, band=band, **kwargs
                    )
                band_arr.attrs["cleaning_method"] = cleaning_method.value

                # Write on disk
                try:
                    utils.write(
                        band_arr.rename(f"{to_str(band)[0]} CLEAN"), clean_band_path
                    )
                except Exception:
                    # Not important if we cannot write it
                    LOGGER.debug(f"Cannot write {clean_band_path} on disk.")

            # Save band array
            band_arrays[band] = band_arr

        return band_arrays

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
        raise NotImplementedError

    @abstractmethod
    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        raise NotImplementedError

    @abstractmethod
    def _manage_nodata(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage only nodata pixels

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        raise NotImplementedError

    @staticmethod
    def _set_nodata_mask(band_arr: xr.DataArray, mask: np.ndarray) -> xr.DataArray:
        """
        Create the correct xarray with well positioned nodata

        Args:
            band_arr (xr.DataArray): Band array
            mask (np.ndarray): Mask array

        Returns:
            (xr.DataArray): Corrected band array
        """
        # Binary mask
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        if len(mask.shape) < len(band_arr.shape):
            mask = np.expand_dims(mask, axis=0)

        # Set masked values to nodata
        return band_arr.where(mask == 0)

    def _load(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Core function loading optical data bands

        Args:
            bands (list): Band list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands

        Returns:
            Dictionary {band_name, band_xarray}
        """
        band_list = []
        index_list = []
        dem_list = []
        clouds_list = []

        # Check if everything is valid
        for idx_or_band in bands:
            if is_index(idx_or_band):
                if self._has_index(idx_or_band):
                    index_list.append(idx_or_band)
                else:
                    raise InvalidIndexError(
                        f"{idx_or_band} cannot be computed from {self.condensed_name}."
                    )
            elif is_sar_band(idx_or_band):
                raise TypeError(
                    f"You should ask for Optical bands as {self.name} is an optical product."
                )
            elif is_spectral_band(idx_or_band):
                if self.has_band(idx_or_band):
                    band_list.append(idx_or_band)
                else:
                    raise InvalidBandError(
                        f"{idx_or_band} cannot be retrieved from {self.condensed_name}."
                    )
            elif is_dem(idx_or_band):
                dem_list.append(idx_or_band)
            elif is_clouds(idx_or_band):
                clouds_list.append(idx_or_band)

        # Check if DEM is set and exists
        if dem_list:
            self._check_dem_path(bands, **kwargs)

        # Get all bands to be open
        bands_to_load = band_list.copy()
        for idx in index_list:
            bands_to_load += indices.NEEDED_BANDS[idx]

        # Load band arrays (only keep unique bands: open them only one time !)
        unique_bands = list(set(bands_to_load))
        if unique_bands:
            LOGGER.debug(f"Loading bands {to_str(unique_bands)}")
        bands = self._load_bands(
            unique_bands, resolution=resolution, size=size, **kwargs
        )

        # Compute index (they conserve the nodata)
        if index_list:
            LOGGER.debug(f"Loading indices {to_str(index_list)}")
        bands_dict = {idx: idx(bands) for idx in index_list}

        # Add bands
        bands_dict.update({band: bands[band] for band in band_list})

        # Add DEM
        if dem_list:
            LOGGER.debug(f"Loading DEM bands {to_str(dem_list)}")
        bands_dict.update(
            self._load_dem(dem_list, resolution=resolution, size=size, **kwargs)
        )

        # Add Clouds
        if clouds_list:
            LOGGER.debug(f"Loading Cloud bands {to_str(clouds_list)}")
        bands_dict.update(
            self._load_clouds(clouds_list, resolution=resolution, size=size, **kwargs)
        )

        return bands_dict

    @abstractmethod
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
        raise NotImplementedError

    @cache
    def get_mean_viewing_angles(self) -> (float, float, float):
        """
        Get Mean Viewing angles (azimuth, off-nadir and incidence angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_viewing_angles()

        Returns:
            (float, float, float): Mean azimuth, off-nadir and incidence angles
        """
        return None, None, None

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
        # Warp DEM
        warped_dem_path = self._warp_dem(dem_path, resolution, size, resampling)

        # Get Hillshade path
        hillshade_name = (
            f"{self.condensed_name}_HILLSHADE_{files.get_filename(dem_path)}.tif"
        )
        hillshade_path = self._get_band_folder().joinpath(hillshade_name)
        if hillshade_path.is_file():
            LOGGER.debug(
                "Already existing hillshade DEM for %s. Skipping process.", self.name
            )
        else:
            hillshade_path = self._get_band_folder(writable=True).joinpath(
                hillshade_name
            )
            LOGGER.debug("Computing hillshade DEM for %s", self.name)

            # Get angles
            mean_azimuth_angle, mean_zenith_angle = self.get_mean_sun_angles()

            # Compute hillshade
            hillshade = rasters.hillshade(
                warped_dem_path, mean_azimuth_angle, mean_zenith_angle
            )
            utils.write(hillshade, hillshade_path)

        return hillshade_path

    @abstractmethod
    def _open_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Open cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

    def _load_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}
        if bands:
            # First, try to open the cloud band written on disk
            bands_to_load = []
            for band in bands:
                cloud_path = self._get_cloud_band_path(
                    band, resolution, size, writable=False, **kwargs
                )
                if cloud_path.is_file():
                    band_dict[band] = utils.read(cloud_path)
                else:
                    bands_to_load.append(band)

            # Then load other bands that haven't be loaded before
            loaded_bands = self._open_clouds(bands_to_load, resolution, size, **kwargs)

            # Write them on disk
            for band_id, band_arr in loaded_bands.items():
                cloud_path = self._get_cloud_band_path(
                    band_id, resolution, size, writable=True, **kwargs
                )
                utils.write(band_arr, cloud_path)

            # Merge the dict
            band_dict.update(loaded_bands)

        return band_dict

    def _create_mask(
        self, xds: xr.DataArray, cond: np.ndarray, nodata: np.ndarray
    ) -> xr.DataArray:
        """
        Create a mask from a conditional array and a nodata mask.

        Args:
            xds (xr.DataArray): xarray to retrieve attributes
            cond (np.ndarray): Conditional array
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Mask as xarray
        """
        mask = xds.copy(data=np.where(cond, self._mask_true, self._mask_false))
        mask = mask.where(nodata == 0)

        return mask

    def _get_clean_band_path(
        self,
        band: BandNames,
        resolution: float = None,
        writable: bool = False,
        **kwargs,
    ) -> Union[CloudPath, Path]:
        """
        Get clean band path.

        The clean band is the opened band where invalid pixels have been managed.

        Args:
            band (BandNames): Wanted band
            resolution (float): Band resolution in meters
            writable (bool): True if we want the band folder to be writeable
            kwargs: Additional arguments

        Returns:
            Union[CloudPath, Path]: Clean band path
        """
        cleaning_method = CleanMethod.from_value(
            kwargs.get(CLEAN_OPTICAL, DEF_CLEAN_METHOD)
        )

        res_str = self._resolution_to_str(resolution)

        # Radiometric processing
        rad_proc = "" if kwargs.get(TO_REFLECTANCE, True) else "_as_is"

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band.name}_{res_str.replace('.', '-')}_{cleaning_method.value}{rad_proc}.tif",
        )

    def _get_cloud_band_path(
        self,
        band: BandNames,
        resolution: float = None,
        size: Union[list, tuple] = None,
        writable: bool = False,
        **kwargs,
    ) -> Union[CloudPath, Path]:
        """
        Get cloud band path.

        Args:
            band (BandNames): Wanted band
            resolution (float): Band resolution in meters
            writable (bool): True if we want the band folder to be writeable
            kwargs: Additional arguments

        Returns:
            Union[CloudPath, Path]: Clean band path
        """
        # Manage resolution
        if resolution is None:
            if size is not None:
                resolution = self._resolution_from_size(size)
            else:
                resolution = self.resolution

        # Convert to str
        res_str = self._resolution_to_str(resolution)

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band.name}_{res_str.replace('.', '-')}.tif",
        )

    @cache
    def _sun_earth_distance_variation(self) -> float:
        """
        Correction for the Sun-Earth distance variation

        It utilises the inverse square law of irradiance, under which,
        the intensity (or irradiance) of light radiating from a point source is inversely proportional to the square of the distance from the source.

         - t is the Julian Day corresponding to the acquisition date (reference day: 01/01/1950).
         - 0.01673 is the Earth orbit eccentricity.
         - 0.0172 is the Earth angular velocity (radians/day).

        See `here <https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-1c/algorithm>`_ for more information.

        Returns:
            float: Sun-Earth distance variation
        """
        # julian_date is the Julian Day corresponding to the acquisition date (reference day: 01/01/1950).
        ref_julian_date = datetime(year=1950, month=1, day=1)
        julian_date = (self.date - ref_julian_date).days + 1

        # Compute Sun-Earth distance variation
        return 1 / (1 - 0.01673 * np.cos(0.0172 * (julian_date - 2))) ** 2

    @cache
    def get_cloud_cover(self) -> float:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_cloud_cover()
            55.5

        Returns:
            float: Cloud cover as given in the metadata
        """
        LOGGER.warning(
            f"No cloud cover available for {self.constellation.value} data !"
        )
        return 0.0

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
        has_spectral_bands = [is_spectral_band(band) for band in bands]

        # Do not add this if one non-spectral bands exists
        if all(has_spectral_bands):
            if kwargs.get(TO_REFLECTANCE, True):
                xarr.attrs["radiometry"] = "reflectance"
            else:
                xarr.attrs["radiometry"] = "as is"

        # Add this if at least one spectral bands exists
        if any(has_spectral_bands):
            if self._has_cloud_cover:
                xarr.attrs["cloud_cover"] = self.get_cloud_cover()

        return xarr

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
        # All optical satellite are descending by default
        return OrbitDirection.DESCENDING

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        repr = []
        if self._has_cloud_cover:
            repr.append(f"\tcloud cover: {self.get_cloud_cover()}")

        if self.tile_name is not None:
            repr.append(f"\ttile name: {self.tile_name}")

        return repr
