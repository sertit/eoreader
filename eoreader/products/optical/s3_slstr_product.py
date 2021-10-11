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
""" Sentinel-3 SLSTR products """
import logging
from functools import reduce
from pathlib import Path
from typing import Union

import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from rasterio import features
from rasterio.enums import Resampling
from sertit import rasters, rasters_rio
from sertit.rasters import XDS_TYPE

from eoreader import utils
from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidTypeError
from eoreader.products.optical.s3_product import S3DataType, S3Product, S3ProductType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
BT_BANDS = [obn.MIR, obn.TIR_1, obn.TIR_2]

# FROM SNAP (only for radiance bands, not for brilliance temperatures)
# https://github.com/senbox-org/s3tbx/blob/197c9a471002eb2ec1fbd54e9a31bfc963446645/s3tbx-rad2refl/src/main/java/org/esa/s3tbx/processor/rad2refl/Rad2ReflConstants.java#L141
SLSTR_SOLAR_FLUXES_DEFAULT = {
    obn.GREEN: 1837.39,
    obn.RED: 1525.94,
    obn.NIR: 956.17,
    obn.NARROW_NIR: 956.17,
    obn.SWIR_CIRRUS: 365.90,
    obn.SWIR_1: 248.33,
    obn.SWIR_2: 78.33,
}


class S3SlstrProduct(S3Product):
    """
    Class of Sentinel-3 Products

    **Note**: All S3-OLCI bands won't be used in EOReader !

    **Note**: We only use NADIR rasters for S3-SLSTR bands
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:

        """
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/observation-mode-desc
        Note that the name of each netCDF file provides information about it's content.
        The suffix of each filename is associated with the selected grid:
            "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
            "bn" and "bo" refer to the 500 m grid, stripe B
            "in" and "io" refer to the 1 km grid
            "fn" and "fo" refer to the F1 channel 1 km grid
            "tx/n/o" refer to the tie-point grid for agnostic/nadir and oblique view
        """
        self._suffix = "an"

        self._flags_file = None
        self._cloud_name = None
        self._exception_name = None

        super().__init__(
            product_path, archive_path, output_path, remove_tmp
        )  # Order is important here

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Post init done by the super class
        super()._pre_init()

    def change_suffix(self, new_suffix: str) -> None:
        """
        Changing the file [suffix]
        (https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/observation-mode-desc)

        Note that the name of each netCDF file provides information about it's content.
        The suffix of each filename is associated with the selected grid:
        - "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
        - "bn" and "bo" refer to the 500 m grid, stripe B
        - "in" and "io" refer to the 1 km grid
        - "fn" and "fo" refer to the F1 channel 1 km grid
        - "tx/n/o" refer to the tie-point grid for agnostic/nadir and oblique view

        Args:
            new_suffix (str): New suffix (accepted ones: `an`, `ao`, `bn`, `bo`, `in`, `io`, `fn`, `fo`)
        """
        assert new_suffix in ["an", "ao", "bn", "bo", "in", "io", "fn", "fo"]
        self._suffix = new_suffix
        self._set_preprocess_members()

    def _set_preprocess_members(self):
        """ Set pre-process members """
        # Geocoding
        self._geo_file = f"geodetic_{self._suffix}.nc"
        self._lat_nc_name = f"latitude_{self._suffix}"
        self._lon_nc_name = f"longitude_{self._suffix}"
        self._alt_nc_name = f"elevation_{self._suffix}"

        # Tie geocoding
        self._tie_geo_file = "geodetic_tx.nc"
        self._tie_lat_nc_name = "latitude_tx"
        self._tie_lon_nc_name = "longitude_tx"

        # Mean Sun angles
        self._geom_file = f"geometry_t{self._suffix[-1]}.nc"
        self._sza_name = f"solar_azimuth_t{self._suffix[-1]}"
        self._sze_name = f"solar_zenith_t{self._suffix[-1]}"

        # Rad 2 Refl
        self._misc_file = f"S{{}}_quality_{self._suffix}.nc"
        self._solar_flux_name = f"S{{}}_solar_irradiance_{self._suffix}"

        # Clouds
        self._flags_file = f"flags_{self._suffix}.nc"
        self._cloud_name = f"cloud_{self._suffix}"

        # Other
        self._exception_name = f"S{{}}_exception_{self._suffix}"

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        return 500.0

    def _set_product_type(self) -> None:
        """Set products type"""
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        self.product_type = S3ProductType.SLSTR_RBT
        self._data_type = S3DataType.RBT

        # Bands
        self.band_names.map_bands(
            {
                obn.GREEN: "1",  # radiance, 500m
                obn.RED: "2",  # radiance, 500m
                obn.NIR: "3",  # radiance, 500m
                obn.NARROW_NIR: "3",  # radiance, 500m
                obn.SWIR_CIRRUS: "4",  # radiance, 500m
                obn.SWIR_1: "5",  # radiance, 500m
                obn.SWIR_2: "6",  # radiance, 500m
                # obn.MIR: "7",  # brilliance temperature, 1km
                obn.TIR_1: "8",  # brilliance temperature, 1km
                obn.TIR_2: "9",  # brilliance temperature, 1km
            }
            # TODO: manage F1 and F2 ?
        )

    def _get_raw_band_path(self, band: Union[obn, str], subdataset: str = None) -> str:
        """
        Return the paths of raw band.

        Args:
            band (Union[obn, str]): Wanted raw bands
            subdataset (str): Subdataset

        Returns:
            str: Raw band path
        """
        # Try to convert to obn if existing
        try:
            band = obn.convert_from(band)[0]
        except TypeError:
            pass

        # Get band regex
        if isinstance(band, obn):
            band_regex = f"S{self.band_names[band]}_radiance_{self._suffix}.nc"
            if not subdataset:
                subdataset = f"S{self.band_names[band]}_radiance_{self._suffix}"
        else:
            band_regex = band

        # Get raw band path
        try:
            band_path = next(self.path.glob(f"*{band_regex}*"))
        except StopIteration:
            raise FileNotFoundError(f"Non existing file {band_regex} in {self.path}")

        return self._get_nc_path_str(band_path.name, subdataset)

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(self, band_arr: XDS_TYPE, band: obn) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        ISP_absent pixel_absent not_decompressed no_signal saturation invalid_radiance no_parameters unfilled_pixel"

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Open quality flags
        qual_flags_path = self._preprocess(
            band,
            subdataset=self._exception_name.replace("{}", self.band_names[band]),
            resolution=band_arr.rio.resolution(),
            to_reflectance=False,
        )

        # Open flag file
        qual_arr, _ = rasters_rio.read(
            qual_flags_path,
            size=(band_arr.rio.width, band_arr.rio.height),
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
        )

        # Set no data for everything (except ISP) that caused an exception
        exception = np.where(qual_arr > 2, self._mask_true, self._mask_false)

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), self._mask_true, self._mask_false)

        # Combine masks
        mask = no_data | exception

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        - SLSTR does
        - OLCI does not provide any cloud mask
        """
        if band in [
            RAW_CLOUDS,
            ALL_CLOUDS,
            CLOUDS,
            CIRRUS,
        ]:
            has_band = True
        else:
            has_band = False

        return has_band

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read S3 SLSTR clouds from the flags file:cloud netcdf file.
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/cloud-identification

        bit_id  flag_masks (ushort)     flag_meanings
        ===     ===                     ===
        0       1US                     visible
        1       2US                     1.37_threshold
        2       4US                     1.6_small_histogram
        3       8US                     1.6_large_histogram
        4       16US                    2.25_small_histogram
        5       32US                    2.25_large_histogram
        6       64US                    11_spatial_coherence
        7       128US                   gross_cloud
        8       256US                   thin_cirrus
        9       512US                   medium_high
        10      1024US                  fog_low_stratus
        11      2048US                  11_12_view_difference
        12      4096US                  3.7_11_view_difference
        13      8192US                  thermal_histogram
        14      16384US                 spare
        15      32768US                 spare

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            all_ids = list(np.arange(0, 14))
            cir_id = 8
            cloud_ids = [id for id in all_ids if id != cir_id]

            # Open path
            # TODO
            cloud_path = self._preprocess(
                self._flags_file,
                subdataset=self._cloud_name,
                resolution=resolution,
                to_reflectance=False,
            )

            # Open cloud file
            clouds_array = utils.read(
                cloud_path,
                resolution=resolution,
                size=size,
                resampling=Resampling.nearest,
                masked=False,
            ).astype(np.uint16)

            # Get nodata mask
            nodata = np.where(np.isnan(clouds_array), 1, 0)

            for band in bands:
                if band == ALL_CLOUDS:
                    band_dict[band] = self._create_mask(clouds_array, all_ids, nodata)
                elif band == CLOUDS:
                    band_dict[band] = self._create_mask(clouds_array, cloud_ids, nodata)
                elif band == CIRRUS:
                    band_dict[band] = self._create_mask(clouds_array, cir_id, nodata)
                elif band == RAW_CLOUDS:
                    band_dict[band] = clouds_array
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-3 SLSTR: {band}"
                    )

        return band_dict

    def _create_mask(
        self,
        bit_array: xr.DataArray,
        bit_ids: Union[int, list],
        nodata: np.ndarray,
    ) -> xr.DataArray:
        """
        Create a mask masked array (uint8) from a bit array, bit IDs and a nodata mask.

        Args:
            bit_array (xr.DataArray): Conditional array
            bit_ids (Union[int, list]): Bit IDs
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Mask masked array

        """
        if not isinstance(bit_ids, list):
            bit_ids = [bit_ids]
        conds = rasters.read_bit_array(bit_array, bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every conditions (bitwise or)

        cond_arr = np.where(cond, self._mask_true, self._mask_false).astype(np.uint8)
        cond_arr = np.squeeze(cond_arr)
        try:
            cond_arr = features.sieve(cond_arr, size=10, connectivity=4)
        except TypeError:
            # Manage dask arrays that fails with rasterio sieve
            cond_arr = features.sieve(cond_arr.compute(), size=10, connectivity=4)
        cond_arr = np.expand_dims(cond_arr, axis=0)

        return super()._create_mask(bit_array, cond_arr, nodata)
