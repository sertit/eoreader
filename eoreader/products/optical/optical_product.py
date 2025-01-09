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
"""Super class for optical products"""

import logging
from abc import abstractmethod
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from rasterio import crs as riocrs
from rasterio.enums import Resampling
from sertit import AnyPath, files, path, rasters
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    GREEN,
    BandNames,
    SpectralBandMap,
    is_spectral_band,
    is_thermal_band,
    to_str,
)
from eoreader.keywords import CLEAN_OPTICAL, TO_REFLECTANCE
from eoreader.products.product import OrbitDirection, Product, SensorType

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


@unique
class RawUnits(ListEnum):
    """
    Units of the raw band
    """

    DN = "digital number"
    """
    Digital Number
    """

    RAD = "radiance"
    """
    Radiance
    """

    REFL = "reflectance"
    """
    Reflectance
    """

    NONE = "none"
    """
    No relevant unit (i.e. SEAMLESS bands for DIMAP or visualisation bands)
    """


DEF_CLEAN_METHOD = CleanMethod.NODATA


class OpticalProduct(Product):
    """Super class for optical products"""

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._has_cloud_cover = False
        self._raw_units = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

        # For optical products, we assume the resolution is the same as the pixel size
        self.resolution = self.pixel_size

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
        return GREEN

    def get_default_band_path(self, **kwargs) -> AnyPathType:
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
            AnyPathType: Default band path
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
        raise NotImplementedError

    def _open_bands(
        self,
        band_paths: dict,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Open bands from disk.

        Args:
            band_paths (dict): Band dict: {band_enum: band_path}
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
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
                band_path, band=band, pixel_size=pixel_size, size=size, **kwargs
            )

            if not pixel_size:
                pixel_size = band_arr.rio.resolution()[0]
            clean_band_path = self._get_clean_band_path(
                band, pixel_size=pixel_size, writable=True, **kwargs
            )
            # If raw data, clean it !
            if AnyPath(band_path).name != clean_band_path.name:
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

                # Manage reflectance
                # (after cleaning -> don't alter pixel value before managing nodata)
                if kwargs.get(TO_REFLECTANCE, True):
                    LOGGER.debug(f"Converting {band.name} to reflectance")
                    band_arr = self._to_reflectance(band_arr, band_path, band)

                    # b_min = band_arr.min().data
                    # if b_min < 0:
                    #     LOGGER.debug(
                    #         f"Reflectance array has negative values ({b_min} < 0): clipping negative reflectances to 0."
                    #     )
                    # Negative reflectances should be discarded: https://labo.obs-mip.fr/multitemp/can-surface-reflectance-be-negative
                    # NB: Reflectances > 1 are valid, see https://forum.step.esa.int/t/toa-range-in-sentinel-2-images-between-0-an-1/3168
                    band_arr = band_arr.clip(min=0, keep_attrs=True)

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
    def _set_nodata_mask(band_arr: xr.DataArray, mask: xr.DataArray) -> xr.DataArray:
        """
        Create the correct xarray with well positioned nodata

        Args:
            band_arr (xr.DataArray): Band array
            mask (xr.DataArray): Mask array

        Returns:
            (xr.DataArray): Corrected band array
        """
        # Binary mask
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        if len(mask.shape) < len(band_arr.shape):
            mask = np.expand_dims(mask, axis=0)

        from dask import array as da

        # Set masked values to nodata
        if isinstance(mask, xr.DataArray):
            # Xarray
            mask = mask.data
        elif isinstance(mask, (np.ndarray, da.Array)):
            # np.ndarray
            # LOGGER.debug(
            #     "The nodata mask is given as a 'np.ndarray' or a 'dask.array'. Please look into this (or write an issue to GitHub)."
            # )
            pass
        else:
            raise NotImplementedError

        band_arr_nodata = band_arr.where(mask == 0)

        # Where sadly drops the encoding dict...
        band_arr_nodata.rio.update_encoding(band_arr.encoding, inplace=True)
        return band_arr_nodata

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
        # Warp DEM
        warped_dem_path = self._warp_dem(dem_path, pixel_size, size, resampling)

        # Get Hillshade path
        hillshade_name = (
            f"{self.condensed_name}_HILLSHADE_{path.get_filename(dem_path)}.tif"
        )

        hillshade_path, hillshade_exists = self._get_out_path(hillshade_name)
        if hillshade_exists:
            LOGGER.debug(
                "Already existing hillshade DEM for %s. Skipping process.", self.name
            )
        else:
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
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Open cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError

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
        band_dict = {}
        if bands:
            # First, try to open the cloud band written on disk
            bands_to_load = []
            for band in bands:
                cloud_path = self._construct_band_path(
                    band, pixel_size, size, writable=False, **kwargs
                )
                if cloud_path.is_file():
                    band_dict[band] = utils.read(cloud_path)
                else:
                    bands_to_load.append(band)

            # Then load other bands that haven't been loaded before
            loaded_bands = self._open_clouds(bands_to_load, pixel_size, size, **kwargs)

            # Write them on disk
            for band_id, band_arr in loaded_bands.items():
                cloud_path = self._construct_band_path(
                    band_id, pixel_size, size, writable=True, **kwargs
                )
                utils.write(band_arr, cloud_path)

            # Merge the dict
            band_dict.update(loaded_bands)

        return band_dict

    def _create_mask(
        self, xda: xr.DataArray, cond: np.ndarray, nodata: np.ndarray = None
    ) -> xr.DataArray:
        """
        Create a mask from a conditional array and a nodata mask.

        Args:
            xda (xr.DataArray): xarray to retrieve attributes
            cond (np.ndarray): Conditional array
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Mask as xarray
        """
        # Create mask
        mask = xda.copy(data=xr.where(cond, self._mask_true, self._mask_false))

        # Set nodata to mask
        if nodata is not None:
            mask = mask.where(nodata == 0)

        return mask

    def _get_clean_band_path(
        self,
        band: BandNames,
        pixel_size: float = None,
        writable: bool = False,
        **kwargs,
    ) -> AnyPathType:
        """
        Get clean band path.

        The clean band is the opened band where invalid pixels have been managed.

        Args:
            band (BandNames): Wanted band
            pixel_size (float): Band pixel size in meters
            writable (bool): True if we want the band folder to be writeable
            kwargs: Additional arguments

        Returns:
            AnyPathType: Clean band path
        """
        cleaning_method = CleanMethod.from_value(
            kwargs.get(CLEAN_OPTICAL, DEF_CLEAN_METHOD)
        )

        # Manage multi resolution bands opened with native resolution (such as PAN in Landsat)
        if pixel_size is None:
            pixel_size = self.bands[band].gsd

        res_str = self._pixel_size_to_str(pixel_size)

        # Radiometric processing
        rad_proc = "" if kwargs.get(TO_REFLECTANCE, True) else "_as_is"

        # Window name
        window = kwargs.get("window")

        win_suffix = ""
        if window is not None:
            if path.is_path(window):
                win_suffix = path.get_filename(window)
            elif isinstance(window, gpd.GeoDataFrame):
                win_suffix = window.attrs.get("name")
            if not win_suffix:
                win_suffix = f"win{files.hash_file_content(str(window))}"

            win_suffix += "_"

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band.name}_{res_str.replace('.', '-')}_{win_suffix}{cleaning_method.value}{rad_proc}.tif",
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
            xr.DataArray: Updated array/dataset
        """
        has_spectral_bands = [is_spectral_band(band) for band in bands]

        # Do not add this if one non-spectral bands exists
        if all(has_spectral_bands):
            if kwargs.get(TO_REFLECTANCE, True):
                has_thermal = [is_thermal_band(band) for band in bands]
                if all(has_thermal):
                    xarr.attrs["radiometry"] = "brightness temperature"
                elif any(has_thermal):
                    xarr.attrs["radiometry"] = "reflectance and brightness temperature"
                else:
                    xarr.attrs["radiometry"] = "reflectance"
            else:
                xarr.attrs["radiometry"] = "as is"

        # Add this if at least one spectral bands exists
        if any(has_spectral_bands) and self._has_cloud_cover:
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
        repr_str = []
        if self._has_cloud_cover:
            repr_str.append(f"\tcloud cover: {self.get_cloud_cover()}")

        if self.tile_name is not None:
            repr_str.append(f"\ttile name: {self.tile_name}")

        return repr_str
