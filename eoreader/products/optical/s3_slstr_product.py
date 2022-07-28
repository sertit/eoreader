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
"""
Sentinel-3 SLSTR products

.. WARNING:
    Not georeferenced NetCDF files are badly opened by GDAL and therefore by rasterio !
    -> use xr.open_dataset that manages that correctly
"""
import logging
from collections import defaultdict, namedtuple
from enum import unique
from functools import reduce
from pathlib import Path
from typing import Union

import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from rasterio import features
from rasterio.enums import Resampling
from sertit import files, rasters, rasters_rio
from sertit.misc import ListEnum
from sertit.rasters import MAX_CORES
from sertit.vectors import WGS84

from eoreader import cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    RAW_CLOUDS,
    BandNames,
    SpectralBand,
)
from eoreader.bands import spectral_bands as spb
from eoreader.bands import to_str
from eoreader.exceptions import InvalidTypeError
from eoreader.keywords import CLEAN_OPTICAL, SLSTR_RAD_ADJUST, SLSTR_STRIPE, SLSTR_VIEW
from eoreader.products import S3DataType, S3Product, S3ProductType
from eoreader.products.optical.optical_product import DEF_CLEAN_METHOD, CleanMethod
from eoreader.stac import ASSET_ROLE, BT, CENTER_WV, DESCRIPTION, FWHM, GSD, ID, NAME
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# FROM SNAP (only for radiance bands, not for brilliance temperatures)
# https://github.com/senbox-org/s3tbx/blob/197c9a471002eb2ec1fbd54e9a31bfc963446645/s3tbx-rad2refl/src/main/java/org/esa/s3tbx/processor/rad2refl/Rad2ReflConstants.java#L141
# Not used for now
SLSTR_SOLAR_FLUXES_DEFAULT = {
    spb.GREEN: 1837.39,
    spb.RED: 1525.94,
    spb.NIR: 956.17,
    spb.NARROW_NIR: 956.17,
    spb.SWIR_CIRRUS: 365.90,
    spb.SWIR_1: 248.33,
    spb.SWIR_2: 78.33,
}

# Link band names to their stripe
SLSTR_A_BANDS = ["S1", "S2", "S3"]
SLSTR_ABC_BANDS = ["S4", "S5", "S6"]
SLSTR_F_BANDS = ["F1"]
SLSTR_I_BANDS = ["S7", "S8", "S9", "F1", "F2"]

# Link band names to their physical quantity (radiance vs brilliance temperature)
SLSTR_RAD_BANDS = SLSTR_A_BANDS + SLSTR_ABC_BANDS
SLSTR_BT_BANDS = SLSTR_I_BANDS

# Radiance adjustment
FIELDS = [f"{rad}_n" for rad in SLSTR_A_BANDS + SLSTR_ABC_BANDS] + [
    f"{rad}_o" for rad in SLSTR_A_BANDS + SLSTR_ABC_BANDS
]  # Nadir and Oblique

SlstrRadAdjustTuple = namedtuple(
    "SlstrRadAdjustTuple", FIELDS, defaults=(1.0,) * len(FIELDS)
)


@unique
class SlstrView(ListEnum):
    """
    Sentinel-3 SLSTR views: nadir view (n) and oblique view (o)

    Used in the context:
        - "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
        - "bn" and "bo" refer to the 500 m grid, stripe B
        - "cn" and "co" refer to the 500 m grid, stripe C
        - "in" and "io" refer to the 1 km grid
        - "fn" and "fo" refer to the F1 channel 1 km grid
    """

    NADIR = "n"
    """Nadir view (n)"""

    OBLIQUE = "o"
    """Oblique view (o)"""


@unique
class SlstrStripe(ListEnum):
    """
    Sentinel-3 SLSTR stripes for 500m data: A and B

    Used in the context:
        - "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
        - "bn" and "bo" refer to the 500 m grid, stripe B
        - "cn" and "co" refer to the 500 m grid, TDI
        - "in" and "io" refer to the 1 km grid
        - "fn" and "fo" refer to the F1 channel 1 km grid
    """

    A = "a"
    """Stripe A (a)"""

    B = "b"
    """Stripe B (b)"""

    TDI = "c"
    """TDI (c)"""

    I = "i"  # noqa
    """Not really a stripe, but refers to the 1 km grid"""

    F = "f"
    """Not really a stripe, but refers to the F1 channel 1 km grid"""


class SlstrRadAdjust(ListEnum):
    """
    SLSTR Radiance Adjustment dictionaries.

    Sentinel-3 SLSTR radiometry is not nominal, therefore a first-order radiometric correction is provided.
    """

    SNAP = SlstrRadAdjustTuple(
        # Nadir
        S5_n=1.12,
        S6_n=1.13,
        # Oblique
        S5_o=1.15,
        S6_o=1.14,
    )
    """
    SNAP Radiometric adjustment used in S3MPC Adjustment (optional in SNAP). Coefficients can be seen
    [here](https://github.com/senbox-org/s3tbx/blob/b10514e399f7a8a436002d2bacdb0c62be72f8f8/s3tbx-sentinel3-reader/src/main/java/org/esa/s3tbx/dataio/s3/slstr/SlstrLevel1ProductFactory.java#L72-L75)
    """

    S3_PN_SLSTR_L1_06 = SlstrRadAdjustTuple(
        # Nadir
        S5_n=1.12,
        S6_n=1.15,
        # Oblique
        S5_o=1.20,
        S6_o=1.26,
    )
    """
    Coefficients given in the
    [Sentinel-3 Product Notice 06](https://www-cdn.eumetsat.int/files/2020-04/pdf_s3a_pn_slstr_l1_06.pdf),
    edited the 07/11/2018 and reviewed the 19/11/2018
    """

    S3_PN_SLSTR_L1_07 = S3_PN_SLSTR_L1_06
    """
    Coefficients given in the
    [Sentinel-3 Product Notice 07](https://www-cdn.eumetsat.int/files/2020-06/pdf_s3a_pn_slstr_l1_07_1.1.pdf),
    edited the 15/01/2020 and reviewed the 09/06/2020, same as the Product Notice 06.
    """

    S3_PN_SLSTR_L1_08 = SlstrRadAdjustTuple(
        # Nadir
        S1_n=0.97,
        S2_n=0.98,
        S3_n=0.98,
        S5_n=1.11,
        S6_n=1.13,
        # Oblique
        S1_o=0.94,
        S2_o=0.95,
        S3_o=0.95,
        S5_o=1.04,
        S6_o=1.07,
    )
    """
    Coefficients given in the
    [Sentinel-3 Product Notice 08](https://www-cdn.eumetsat.int/files/2021-05/S3.PN-SLSTR-L1.08%20-%20i1r0%20-%20SLSTR%20L1%20PB%202.75-A%20and%201.53-B.pdf),
    edited the 18/05/2021.

    The default one.
    """

    NONE = SlstrRadAdjustTuple()
    """
    Coefficients set to one.
    """


class S3SlstrProduct(S3Product):
    """
    Class of Sentinel-3 SLSTR Products
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        """
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/observation-mode-desc
        Note that the name of each netCDF file provides information about its content.

        The suffix of each filename is associated with the selected grid:

        - "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
        - "bn" and "bo" refer to the 500 m grid, stripe B
        - "in" and "io" refer to the 1 km grid
        - "fn" and "fo" refer to the F1 channel 1 km grid
        - "tx/n/o" refer to the tie-point grid for agnostic/nadir and oblique view
        """
        self._flags_file = None
        self._cloud_name = None
        self._exception_name = None

        # Default stripe (A) and view (NADIR)
        self._stripe = SlstrStripe.A
        self._view = SlstrView.NADIR
        self._rad_adjust = SlstrRadAdjust.S3_PN_SLSTR_L1_08

        # Brilliance temperature
        self._bt_file = "{band}_BT_{suffix}.nc"
        self._bt_subds = "{band}_BT_{suffix}"

        super().__init__(
            product_path, archive_path, output_path, remove_tmp, **kwargs
        )  # Order is important here, gcps NEED to be after this

        self._gcps = defaultdict(list)
        self._F1_is_f = True
        try:
            self._get_raw_band_path(spb.F1)
        except (FileNotFoundError, StopIteration):
            self._F1_is_f = False

    def _get_preprocessed_band_path(
        self,
        filename: str,
        suffix: str,
        resolution: Union[float, tuple, list] = None,
        writable: bool = True,
    ) -> Union[CloudPath, Path]:
        """
        Create the pre-processed band path

        Args:
            filename (str): Filename
            resolution (Union[float, tuple, list]): Resolution of the wanted UTM band
            writable (bool): Do we need to write the pre-processed band ?

        Returns:
            Union[CloudPath, Path]: Pre-processed band path
        """
        res_str = self._resolution_to_str(resolution)
        if filename.endswith(suffix):
            pp_name = f"{self.condensed_name}_{filename}_{res_str}.tif"
        else:
            pp_name = f"{self.condensed_name}_{filename}_{suffix}_{res_str}.tif"

        return self._get_band_folder(writable=writable).joinpath(pp_name)

    def _set_preprocess_members(self):
        """ Set pre-process members """
        # Radiance bands
        self._radiance_file = "{band}_radiance_{suffix}.nc"
        self._radiance_subds = "{band}_radiance_{suffix}"

        # Geocoding
        self._geo_file = "geodetic_{suffix}.nc"
        self._lat_nc_name = "latitude_{suffix}"
        self._lon_nc_name = "longitude_{suffix}"
        self._alt_nc_name = "elevation_{suffix}"

        # Tie geocoding
        self._tie_geo_file = "geodetic_tx.nc"
        self._tie_lat_nc_name = "latitude_tx"
        self._tie_lon_nc_name = "longitude_tx"

        # Mean Sun angles
        self._geom_file = "geometry_t{view}.nc"
        self._saa_name = "solar_azimuth_t{view}"
        self._sza_name = "solar_zenith_t{view}"

        # Rad 2 Refl
        self._misc_file = "{band}_quality_{suffix}.nc"
        self._solar_flux_name = "{band}_solar_irradiance_{suffix}"

        # Clouds
        self._flags_file = "flags_{suffix}.nc"
        self._cloud_name = "cloud_{suffix}"

        # Other
        self._exception_name = "{band}_exception_{suffix}"

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        return 500.0

    def _set_product_type(self) -> None:
        """Set products type"""
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        self.product_type = S3ProductType.SLSTR_RBT
        self._data_type = S3DataType.RBT

    def _map_bands(self) -> None:
        """
        Map bands
        """
        # Bands
        bt_res = 1000.0
        slstr_bands = {
            spb.GREEN: SpectralBand(
                eoreader_name=spb.GREEN,
                **{
                    NAME: SLSTR_A_BANDS[0],
                    ID: SLSTR_A_BANDS[0],
                    GSD: self.resolution,
                    CENTER_WV: 554.27,
                    FWHM: 19.26,
                    DESCRIPTION: "Cloud screening, vegetation monitoring, aerosol",
                },
            ),
            spb.RED: SpectralBand(
                eoreader_name=spb.RED,
                **{
                    NAME: SLSTR_A_BANDS[1],
                    ID: SLSTR_A_BANDS[1],
                    GSD: self.resolution,
                    CENTER_WV: 659.47,
                    FWHM: 19.25,
                    DESCRIPTION: "NDVI, vegetation monitoring, aerosol",
                },
            ),
            spb.NIR: SpectralBand(
                eoreader_name=spb.NIR,
                **{
                    NAME: SLSTR_A_BANDS[2],
                    ID: SLSTR_A_BANDS[2],
                    GSD: self.resolution,
                    CENTER_WV: 868.00,
                    FWHM: 20.60,
                    DESCRIPTION: "NDVI, cloud flagging, pixel co-registration",
                },
            ),
            spb.NARROW_NIR: SpectralBand(
                eoreader_name=spb.NARROW_NIR,
                **{
                    NAME: SLSTR_A_BANDS[2],
                    ID: SLSTR_A_BANDS[2],
                    GSD: self.resolution,
                    CENTER_WV: 868.00,
                    FWHM: 20.60,
                    DESCRIPTION: "NDVI, cloud flagging, pixel co-registration",
                },
            ),
            spb.SWIR_CIRRUS: SpectralBand(
                eoreader_name=spb.SWIR_CIRRUS,
                **{
                    NAME: SLSTR_ABC_BANDS[0],
                    ID: SLSTR_ABC_BANDS[0],
                    GSD: self.resolution,
                    CENTER_WV: 1374.80,
                    FWHM: 20.80,
                    DESCRIPTION: "Cirrus detection over land",
                },
            ),
            spb.SWIR_1: SpectralBand(
                eoreader_name=spb.SWIR_1,
                **{
                    NAME: SLSTR_ABC_BANDS[1],
                    ID: SLSTR_ABC_BANDS[1],
                    GSD: self.resolution,
                    CENTER_WV: 1613.40,
                    FWHM: 60.68,
                    DESCRIPTION: "Cloud clearing, ice, snow, vegetation monitoring",
                },
            ),
            spb.SWIR_2: SpectralBand(
                eoreader_name=spb.SWIR_2,
                **{
                    NAME: SLSTR_ABC_BANDS[2],
                    ID: SLSTR_ABC_BANDS[2],
                    GSD: bt_res,
                    CENTER_WV: 2255.70,
                    FWHM: 50.15,
                    DESCRIPTION: "Vegetation state and cloud clearing",
                },
            ),
            spb.S7: SpectralBand(
                eoreader_name=spb.S7,
                **{
                    NAME: SLSTR_I_BANDS[0],
                    ID: SLSTR_I_BANDS[0],
                    GSD: bt_res,
                    CENTER_WV: 3742.00,
                    FWHM: 398.00,
                    DESCRIPTION: "SST, LST, Active fire, brilliance temperature, 1km",
                    ASSET_ROLE: BT,
                },
            ),
            spb.TIR_1: SpectralBand(
                eoreader_name=spb.TIR_1,
                **{
                    NAME: SLSTR_I_BANDS[1],
                    ID: SLSTR_I_BANDS[1],
                    GSD: bt_res,
                    CENTER_WV: 10854.00,
                    FWHM: 776.00,
                    DESCRIPTION: "SST, LST, Active fire, brilliance temperature, 1km",
                    ASSET_ROLE: BT,
                },
            ),
            spb.TIR_2: SpectralBand(
                eoreader_name=spb.TIR_2,
                **{
                    NAME: SLSTR_I_BANDS[2],
                    ID: SLSTR_I_BANDS[2],
                    GSD: bt_res,
                    CENTER_WV: 12022.50,
                    FWHM: 905.00,
                    DESCRIPTION: "SST, LST, brilliance temperature, 1km",
                    ASSET_ROLE: BT,
                },
            ),
            spb.F1: SpectralBand(
                eoreader_name=spb.F1,
                **{
                    NAME: SLSTR_I_BANDS[3],
                    ID: SLSTR_I_BANDS[3],
                    GSD: bt_res,
                    CENTER_WV: 3742.00,
                    FWHM: 398.00,
                    DESCRIPTION: "Active fire, brilliance temperature, 1km",
                    ASSET_ROLE: BT,
                },
            ),
            spb.F2: SpectralBand(
                eoreader_name=spb.F2,
                **{
                    NAME: SLSTR_I_BANDS[4],
                    ID: SLSTR_I_BANDS[4],
                    GSD: bt_res,
                    CENTER_WV: 10854.00,
                    FWHM: 776.00,
                    DESCRIPTION: "Active fire, brilliance temperature, 1km",
                    ASSET_ROLE: BT,
                },
            ),
        }

        # Bands
        self.bands.map_bands(slstr_bands)

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the raw band paths.

        Args:
            kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raw_band_paths = {}
        for band in self.get_existing_bands():
            raw_band_paths[band] = self._get_raw_band_path(band, **kwargs)

        return raw_band_paths

    def _get_raw_band_path(self, band: BandNames, **kwargs) -> Union[Path, CloudPath]:
        """
        Return the raw band path.

        Args:
            band (BandNames): Wanted band
            kwargs: Additional arguments

        Returns:
            Union[Path, CloudPath]: Raw path of queried band
        """
        band_id = self.bands[band].id

        # Get this band's suffix
        suffix = kwargs.get("suffix", self._get_suffix(band, **kwargs))

        # Get band filename and subdataset
        if band_id in SLSTR_RAD_BANDS:
            filename = self._replace(self._radiance_file, band=band, suffix=suffix)
        elif band_id in SLSTR_BT_BANDS:
            filename = self._replace(self._bt_file, band=band, suffix=suffix)
        else:
            filename = band

        if self.is_archived:
            raw_path = files.get_archived_path(self.path, f".*{filename}*")
        else:
            raw_path = next(self.path.glob(f"*{filename}*"))

        return raw_path

    def _preprocess(
        self,
        band: Union[BandNames, str],
        resolution: float = None,
        to_reflectance: bool = True,
        subdataset: str = None,
        **kwargs,
    ) -> Union[CloudPath, Path]:
        """
        Pre-process S3 SLSTR bands:
        - Geocode
        - Adjust radiance
        - Convert radiance to reflectance

        Args:
            band (Union[BandNames, str]): Band to preprocess (quality flags or others are accepted)
            resolution (float): Resolution
            to_reflectance (bool): Convert band to reflectance
            subdataset (str): Subdataset
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing {band: path}
        """
        if isinstance(band, BandNames):
            band_id = self.bands[band].id
            band_str = band.name
        else:
            band_id = band
            band_str = band

        # Get this band's suffix
        suffix = kwargs.get("suffix", self._get_suffix(band, **kwargs))

        # Get band filename and subdataset
        pp_name = subdataset if subdataset else band_str
        if band_id in SLSTR_RAD_BANDS:
            if not subdataset:
                subdataset = self._replace(
                    self._radiance_subds, band=band, suffix=suffix
                )
            filename = self._replace(self._radiance_file, band=band, suffix=suffix)
        elif band_id in SLSTR_BT_BANDS:
            if not subdataset:
                subdataset = self._replace(self._bt_subds, band=band, suffix=suffix)
            filename = self._replace(self._bt_file, band=band, suffix=suffix)
        else:
            filename = band

        # Get the pre-processed path
        path = self._get_preprocessed_band_path(
            pp_name, suffix=suffix, resolution=resolution, writable=False
        )

        if not path.is_file():
            path = self._get_preprocessed_band_path(
                pp_name, suffix=suffix, resolution=resolution, writable=True
            )

            # Get raw band
            band_arr = self._read_nc(
                filename, subdataset, dtype=kwargs.get("dtype", np.float32)
            )

            # Radiance pre process (BT bands are given in BT !)
            if not kwargs.get("flags", False) and band_id in SLSTR_RAD_BANDS:
                # Adjust radiance if needed
                # Get the user's radiance adjustment if existing
                rad_adjust = kwargs.get(SLSTR_RAD_ADJUST, self._rad_adjust)
                try:
                    # Try to convert the rad_adjust to the correct enum
                    rad_adjust = SlstrRadAdjust.from_value(rad_adjust)
                except ValueError:
                    # Allow the user to pass a custom SlstrRadAdjustTuple
                    assert isinstance(rad_adjust, SlstrRadAdjustTuple)

                band_arr = self._radiance_adjustment(
                    band_arr, band, view=suffix[-1], rad_adjust=rad_adjust
                )

                # Convert radiance to reflectances if needed
                # Convert first pixel by pixel before reprojection !
                if to_reflectance:
                    LOGGER.debug(f"Converting {band_str} to reflectance")
                    band_arr = self._rad_2_refl(band_arr, band, suffix)

                    # Debug
                    # utils.write(
                    #     band_arr,
                    #     self._get_band_folder(writable=True).joinpath(
                    #         f"{self.condensed_name}_{band.name}_rad2refl.tif"
                    #     ),
                    # )

            # Geocode
            LOGGER.debug(f"Geocoding {pp_name}")
            pp_arr = self._geocode(band_arr, resolution=resolution, suffix=suffix)

            # Write on disk
            utils.write(pp_arr, path)

        return path

    def _get_suffix(self, band: Union[str, BandNames] = None, **kwargs) -> str:
        """
        Get the suffix according to the (given) stripe and view.
            - "an" and "ao" refer to the 500 m grid, stripe A, respectively for nadir view (n) and oblique view (o)
            - "bn" and "bo" refer to the 500 m grid, stripe B
            - "cn" and "co" refer to the 500 m grid, stripe C
            - "in" and "io" refer to the 1 km grid
            - "fn" and "fo" refer to the F1 channel 1 km grid

        Args:
            band (Union[BandNames, str]): Band from which to get the stripe
            kwargs: Other arguments

        Returns:
            str: Suffix (an, bn, cn, in, fn, ao, bo, co, io, fo)
        """
        # Get the view
        view = SlstrView.from_value(kwargs.get(SLSTR_VIEW, self._view))

        if band is not None:
            # Get the stripe
            if isinstance(band, BandNames):
                band = self.bands[band].id

            if band == spb.F1.value:
                if self._F1_is_f:
                    stripe = SlstrStripe.F
                else:
                    stripe = SlstrStripe.I
            else:
                if band in SLSTR_I_BANDS:
                    stripe = SlstrStripe.I
                elif band in SLSTR_ABC_BANDS:
                    stripe = SlstrStripe.from_value(
                        kwargs.get(SLSTR_STRIPE, SlstrStripe.A)
                    )
                else:
                    stripe = SlstrStripe.A
        else:
            stripe = SlstrStripe.from_value(kwargs.get(SLSTR_STRIPE, SlstrStripe.A))

        # Return the prefix
        return f"{stripe.value}{view.value}"

    def _create_gcps(self, suffix: str) -> None:
        """
        Create the GCPs sequence (WGS84)
        """
        if suffix not in self._gcps and not self._gcps[suffix]:
            geo_file = self._replace(self._geo_file, suffix=suffix)
            lon_nc_name = self._replace(self._lon_nc_name, suffix=suffix)
            lat_nc_name = self._replace(self._lat_nc_name, suffix=suffix)
            alt_nc_name = self._replace(self._alt_nc_name, suffix=suffix)

            # Open cartesian files to populate the GCPs
            lat = self._read_nc(geo_file, lat_nc_name)
            lon = self._read_nc(geo_file, lon_nc_name)
            alt = self._read_nc(geo_file, alt_nc_name)

            # Create GCPs
            self._gcps[suffix] = utils.create_gcps(lon, lat, alt)

    def _geocode(
        self, band_arr: xr.DataArray, suffix: str, resolution: float = None
    ) -> xr.DataArray:
        """
        Geocode Sentinel-3 SLSTR bands (using cartesian coordinates)

        Args:
            band_arr (xr.DataArray): Band array
            suffix (str): Suffix (for the grid)
            resolution (float): Resolution

        Returns:
            xr.DataArray: Geocoded DataArray
        """
        # Create GCPs if not existing
        self._create_gcps(suffix)

        # Assign a projection
        band_arr.rio.write_crs(WGS84, inplace=True)

        return band_arr.rio.reproject(
            dst_crs=self.crs(),
            resolution=resolution,
            gcps=self._gcps[suffix],
            nodata=self._mask_nodata if band_arr.dtype == np.uint8 else self.nodata,
            num_threads=MAX_CORES,
            resampling=Resampling.nearest,
            **{"SRC_METHOD": "GCP_TPS"},
        )

    def _tie_to_img(self, tie_arr: np.ndarray, suffix: str) -> np.ndarray:
        """
        Convert an image sampled on the tie point grid (tx) to the wanted gris, given by the suffix

        Args:
            tie_arr (xr.Dataset): Image sampled on the tie point grid (tx)
            suffix: Suffix of the new grid

        Returns:
            np.ndarray: Array resampled to the wanted grid as a numpy array
        """
        # Load tie point grid
        tie_cart_file = "cartesian_tx.nc"
        tx_nc_name = "x_tx"
        ty_nc_name = "y_tx"

        # WARNING: RectBivariateSpline must have increasing values
        tx = np.squeeze(self._read_nc(tie_cart_file, tx_nc_name).data)[0, ::-1]
        ty = np.squeeze(self._read_nc(tie_cart_file, ty_nc_name).data)[:, 0]

        # Load fill image grid (cartesian)
        geo_file = f"cartesian_{suffix}.nc"
        fx_nc_name = f"x_{suffix}"
        fy_nc_name = f"y_{suffix}"

        fx = np.squeeze(self._read_nc(geo_file, fx_nc_name))
        fy = np.squeeze(self._read_nc(geo_file, fy_nc_name))

        # Interpolate via Spline (as extrapolation is possible and the grid is very sparse along the rows)
        # Import scipy here (long import)
        from scipy.interpolate import RectBivariateSpline

        # WARNING 2: Rasterio reads like [count, y, x] !
        no_nan_arr = np.nan_to_num(np.squeeze(tie_arr).data[:, ::-1])
        spline_interp = RectBivariateSpline(ty, tx, no_nan_arr)

        # Interpolate and set nodata back
        img_arr = spline_interp.ev(fy, fx)
        img_arr[img_arr == 0] = np.nan

        return img_arr

    # def _bt_2_rad(self, band_arr: xr.DataArray, band: BandNames = None) -> xr.DataArray:
    #     """
    #     Convert brightness temperature to radiance
    #
    #     The Level-1 brightness temperature measurements provided for the thermal channels (S7-S9, F1 and F2)
    #     can be converted to radiance by integrating the Planck function at the BT of interest multiplied over the
    #     spectral response of each band. The spectral response functions for SLSTR-A and SLSTR-B are available on
    #     the ESA Sentinel Online website (see Section 8.2.10)
    #     https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-slstr/instrument/measured-spectral-response-function-data
    #
    #     In https://sentinel.esa.int/documents/247904/4598085/Sentinel-3-SLSTR-Land-Handbook.pdf/bee342eb-40d4-9b31-babb-8bea2748264a
    #
    #     Args:
    #         band_arr (xr.DataArray): Band array
    #         band (BandNames): Spectral Band
    #
    #     Returns:
    #         dict: Dictionary containing {band: path}
    #     """
    #
    #     return band_arr

    def _rad_2_refl(
        self, band_arr: xr.DataArray, band: BandNames, suffix: str
    ) -> xr.DataArray:
        """
        Convert radiance to reflectance

        The visible and SWIR channels (S1-S6) provide measurements of top of atmosphere (ToA) radiances
        (mW/m2/sr/nm). These values can be converted to normalised reflectance for better comparison or
        merging of data with different sun angles as follows:
        reflectance = π* (ToA radiance / solar irradiance / COS(solar zenith angle))
        where the solar irradiance at ToA is given in the ‘quality’ dataset for the channel,
        and the solar zenith angle is given in the ‘geometry’ dataset.

        The solar irradiance contained in the quality dataset is derived from the solar spectrum
        of Thuillier et al. (2003) integrated over the measured SLSTR spectral responses
        and corrected for the earth-to-sun distance at the time of the measurement.

        In https://sentinel.esa.int/documents/247904/4598085/Sentinel-3-SLSTR-Land-Handbook.pdf/bee342eb-40d4-9b31-babb-8bea2748264a

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Spectral Band
            suffix (str): Band suffix

        Returns:
            dict: Dictionary containing {band: path}
        """
        rad_2_refl_path = (
            self._get_band_folder() / f"rad_2_refl_{band.name}_{suffix}.npy"
        )

        if not rad_2_refl_path.is_file():
            rad_2_refl_path = (
                self._get_band_folder(writable=True)
                / f"rad_2_refl_{band.name}_{suffix}.npy"
            )

            # Open SZA array (resampled to band_arr size)
            sza = self._compute_sza_img_grid(suffix)

            # Open solar flux (resampled to band_arr size)
            e0 = self._compute_e0(band, suffix)

            # Compute rad_2_refl coeff
            rad_2_refl_coeff = (np.pi / e0 / np.cos(sza)).astype(np.float32)

            # Write on disk
            np.save(rad_2_refl_path, rad_2_refl_coeff)

        else:
            # Open rad_2_refl_coeff (resampled to band_arr size)
            rad_2_refl_coeff = np.load(rad_2_refl_path)

        return band_arr * rad_2_refl_coeff

    def _radiance_adjustment(
        self,
        band_arr: xr.DataArray,
        band: Union[str, BandNames],
        view: str,
        rad_adjust: SlstrRadAdjust = SlstrRadAdjust.S3_PN_SLSTR_L1_08,
    ) -> xr.DataArray:
        """
        Applying the radiance adjustment as recommended in the product notice:
        S3.PN-SLSTR-L1.08 (https://www-cdn.eumetsat.int/files/2021-05/S3.PN-SLSTR-L1.08%20-%20i1r0%20-%20SLSTR%20L1%20PB%202.75-A%20and%201.53-B.pdf):

        SLSTR-A/B: All solar channels (S1-S6) have been undergoing a vicarious calibration assessment to
        quantify their radiometric calibration adjustment. Recent analysis of vicarious calibration results
        over desert sites performed by RAL, CNES, Rayference and University of Arizona have determined
        new and consistent radiometric deviations wrt. common reference sensors (MERIS, MODIS)
        [S3MPC.RAL.TN.010]. Consequently, these have been used to provide a first-order radiometric
        corrections which are provided in the below tables with more detail at the following link
        [S3MPC.RAL.TN.020]. Current radiances in the L1B product remain uncorrected of these
        radiometric calibration adjustments. Hence, these multiplicative coefficients are strongly
        recommended to be used by all users.

        Nadir view
                      S1   S2   S3   S5   S6
        Correction  0.97 0.98 0.98 1.11 1.13
        Uncertainty 0.03 0.02 0.02 0.02 0.02

        Oblique view
                      S1   S2   S3   S5   S6
        Correction  0.94 0.95 0.95 1.04 1.07
        Uncertainty 0.05 0.03 0.03 0.03 0.05

        Args:
            band_arr (xr.DataArray): Band array
            band (Union[str, BandNames]): Optical Band
            view (str): View (n or o for Nadir and Oblique)
            rad_adjust (SlstrRadAdjust): Radiance Adjustment

        Returns:
            xr.DataArray: Adjusted band array
        """
        try:
            band_id = self.bands[band].id
            if band_id in SLSTR_RAD_BANDS:
                # Allow the tuple and the enum
                if isinstance(rad_adjust, SlstrRadAdjust):
                    rad_adjust_tuple = rad_adjust.value
                else:
                    rad_adjust_tuple = rad_adjust

                # Get the band coefficient and multiply the band
                rad_coeff = getattr(rad_adjust_tuple, f"{band_id}_{view}")
                band_arr *= rad_coeff
        except KeyError:
            # Not a band (ie Quality Flags) or Brilliance temperature: no adjust needed
            pass

        return band_arr

    def _compute_sza_img_grid(self, suffix) -> np.ndarray:
        """
        Compute Sun Zenith Angle (in radian) resampled to the image grid (from the tie point grid)

        Args:
            suffix (str): Suffix
        Returns:
            np.ndarray: Resampled Sun Zenith Angle as a numpy array
        """
        sza_img_path = self._get_band_folder() / f"sza_{suffix}.npy"
        if not sza_img_path.exists():
            sza_img_path = self._get_band_folder(writable=True) / f"sza_{suffix}.npy"

            geom_file = self._replace(self._geom_file, view=suffix[-1])
            sza_name = self._replace(self._sza_name, view=suffix[-1])
            sza = self._read_nc(geom_file, sza_name)
            sza_rad = sza * np.pi / 180.0

            # From tie grid to image grid
            sza_img = self._tie_to_img(sza_rad, suffix)

            # Write on disk
            np.save(sza_img_path, sza_img)

        else:
            # Open rad_2_refl_coeff (resampled to band_arr size)
            sza_img = np.load(sza_img_path)

        return sza_img

    def _compute_e0(self, band: BandNames, suffix: str) -> np.ndarray:
        """
        Compute the solar spectral flux in mW / (m^2 * sr * nm)

        Args:
            band (BandNames): Optical Band
            suffix (str): Suffix

        Returns:
            np.ndarray: Solar Flux

        """
        misc = self._replace(self._misc_file, band=band, suffix=suffix)
        solar_flux_name = self._replace(self._solar_flux_name, band=band, suffix=suffix)

        e0 = self._read_nc(misc, solar_flux_name).data
        e0 = np.nanmean(e0)
        if np.isnan(e0):
            e0 = SLSTR_SOLAR_FLUXES_DEFAULT[band]

        return e0

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        ISP_absent pixel_absent not_decompressed no_signal saturation invalid_radiance no_parameters unfilled_pixel"

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as a SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # Open quality flags
        # NOT OPTIMIZED, MAYBE CHECK INVALID PIXELS ON NOT GEOCODED DATA
        suffix = self._get_suffix(band, **kwargs)
        qual_flags_path = self._preprocess(
            band,
            suffix=suffix,
            subdataset=self._replace(self._exception_name, band=band, suffix=suffix),
            resolution=band_arr.rio.resolution(),
            to_reflectance=False,
            flags=True,
            dtype=np.uint8,
        )

        # Open flag file
        qual_arr, _ = rasters_rio.read(
            qual_flags_path,
            size=(band_arr.rio.width, band_arr.rio.height),
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
        )

        # Set no data for everything that caused an exception (3 and more)
        exception = np.where(qual_arr >= 3, self._mask_true, self._mask_false)

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), self._mask_true, self._mask_false)

        # Combine masks
        mask = no_data | exception

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        -> SLSTR does
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

    def _open_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
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
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            all_ids = list(np.arange(0, 14))
            cir_id = 8
            cloud_ids = [cid for cid in all_ids if cid != cir_id]

            # Open path
            suffix = self._get_suffix(**kwargs)
            flags_file = self._replace(self._flags_file, suffix=suffix)
            cloud_name = self._replace(self._cloud_name, suffix=suffix)
            cloud_path = self._preprocess(
                flags_file,
                suffix=suffix,
                subdataset=cloud_name,
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
                    cloud = self._create_mask(clouds_array, all_ids, nodata)
                elif band == CLOUDS:
                    cloud = self._create_mask(clouds_array, cloud_ids, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(clouds_array, cir_id, nodata)
                elif band == RAW_CLOUDS:
                    cloud = clouds_array
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-3 SLSTR: {band}"
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

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

    @cache
    def get_mean_sun_angles(self, view: SlstrView = SlstrView.NADIR) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (78.55043955912154, 31.172127033319388)

        Args:
            view (SlstrView): SLSTR View (Nadir or Oblique)
        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        geom_file = self._replace(self._geom_file, view=view.value)
        saa_name = self._replace(self._saa_name, view=view.value)
        sza_name = self._replace(self._sza_name, view=view.value)

        # Open sun azimuth and zenith files
        sun_az = self._read_nc(geom_file, saa_name)
        sun_ze = self._read_nc(geom_file, sza_name)

        return float(sun_az.mean().data) % 360, float(sun_ze.mean().data)

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
            kwargs: Additional arguments

        Returns:
            Union[CloudPath, Path]: Clean band path
        """
        cleaning_method = CleanMethod.from_value(
            kwargs.get(CLEAN_OPTICAL, DEF_CLEAN_METHOD)
        )

        suffix = self._get_suffix(band, **kwargs)
        res_str = self._resolution_to_str(resolution)

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band.name}_{suffix}_{res_str.replace('.', '-')}_{cleaning_method.value}.tif",
        )
