# -*- coding: utf-8 -*-
# Copyright 2021, SERTIT-ICube - France, https:#sertit.unistra.fr/
# This file is part of eoreader project
#     https:#github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Sentinel-3 OLCI products

.. WARNING:
    Not georeferenced NetCDF files are badly opened by GDAL and therefore by rasterio !
    -> use xr.open_dataset that manages that correctly
"""
import logging
from pathlib import Path
from typing import Union

import numpy as np
import rasterio
import xarray as xr
from cloudpathlib import CloudPath
from rasterio.enums import Resampling
from sertit import rasters, rasters_rio
from sertit.rasters import MAX_CORES, XDS_TYPE
from sertit.vectors import WGS84

from eoreader import cache, utils
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.s3_product import (
    S3DataType,
    S3Instrument,
    S3Product,
    S3ProductType,
)
from eoreader.reader import Platform
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# FROM SNAP:
# https://github.com/senbox-org/s3tbx/blob/197c9a471002eb2ec1fbd54e9a31bfc963446645/s3tbx-rad2refl/src/main/java/org/esa/s3tbx/processor/rad2refl/Rad2ReflConstants.java#L97
# Not used for now
OLCI_SOLAR_FLUXES_DEFAULT = {
    obn.Oa01: 1714.9084,
    obn.Oa02: 1872.3961,
    obn.CA: 1926.6102,
    obn.BLUE: 1930.2483,
    obn.Oa05: 1804.2762,
    obn.GREEN: 1651.5836,
    obn.YELLOW: 1531.4067,
    obn.RED: 1475.615,
    obn.Oa09: 1408.9949,
    obn.Oa10: 1265.5425,
    obn.VRE_1: 1255.4227,
    obn.VRE_2: 1178.0286,
    obn.Oa13: 955.07043,
    obn.Oa14: 914.18945,
    obn.Oa15: 882.8275,
    obn.VRE_3: 882.8275,
    obn.NIR: 882.8275,
    obn.NARROW_NIR: 882.8275,
    obn.Oa18: 882.8275,
    obn.Oa19: 882.8275,
    obn.WV: 882.8275,
    obn.Oa21: 882.8275,
}


class S3OlciProduct(S3Product):
    """
    Class of Sentinel-3 OLCI Products
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
        super().__init__(
            product_path, archive_path, output_path, remove_tmp
        )  # Order is important here

        self._gcps = []

    def _get_preprocessed_band_path(
        self,
        band: Union[obn, str],
        resolution: Union[float, tuple, list] = None,
        writable=True,
    ) -> Union[CloudPath, Path]:
        """
        Create the pre-processed band path

        Args:
            band (band: Union[obn, str]): Wanted band (quality flags accepted)
            resolution (Union[float, tuple, list]): Resolution of the wanted UTM band
            writable (bool): Do we need to write the pre-processed band ?

        Returns:
            Union[CloudPath, Path]: Pre-processed band path
        """
        res_str = self._resolution_to_str(resolution)
        band_str = band.name if isinstance(band, obn) else band

        return self._get_band_folder(writable=writable).joinpath(
            f"{self.condensed_name}_{band_str}_{res_str}.tif"
        )

    def _set_preprocess_members(self):
        """ Set pre-process members """
        # Radiance bands
        self._radiance_file = "{band}_radiance.nc"
        self._radiance_subds = "{band}_radiance"

        # Geocoding
        self._geo_file = "geo_coordinates.nc"
        self._lat_nc_name = "latitude"
        self._lon_nc_name = "longitude"
        self._alt_nc_name = "altitude"

        # Tie geocoding
        self._tie_geo_file = "tie_geo_coordinates.nc"
        self._tie_lat_nc_name = "latitude"
        self._tie_lon_nc_name = "longitude"

        # Mean Sun angles
        self._geom_file = "tie_geometries.nc"
        self._saa_name = "SAA"
        self._sza_name = "SZA"

        # Rad 2 Refl
        self._misc_file = "instrument_data.nc"
        self._solar_flux_name = "solar_flux"
        self._det_index = "detector_index"

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Post init done by the super class
        super()._pre_init()

    def _get_platform(self) -> Platform:
        """ Getter of the platform """
        if "OL" in self.name:
            # Instrument
            self._instrument = S3Instrument.OLCI
            sat_id = self._instrument.value
        else:
            raise InvalidProductError(
                f"Only OLCI and SLSTR are valid Sentinel-3 instruments : {self.name}"
            )

        return getattr(Platform, sat_id)

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        return 300.0

    def _set_product_type(self) -> None:
        """Set products type"""
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        self.product_type = S3ProductType.OLCI_EFR
        self._data_type = S3DataType.EFR

        # Bands
        self.band_names.map_bands(
            {
                obn.Oa01: "Oa01",
                obn.Oa02: "Oa02",
                obn.CA: "Oa03",
                obn.BLUE: "Oa04",
                obn.Oa05: "Oa05",
                obn.GREEN: "Oa06",
                obn.YELLOW: "Oa07",
                obn.RED: "Oa08",
                obn.Oa09: "Oa09",
                obn.Oa10: "Oa10",
                obn.VRE_1: "Oa11",
                obn.VRE_2: "Oa12",
                obn.Oa13: "Oa13",
                obn.Oa14: "Oa14",
                obn.Oa15: "Oa15",
                obn.VRE_3: "Oa16",
                obn.NIR: "Oa17",
                obn.NARROW_NIR: "Oa17",
                obn.Oa18: "Oa18",
                obn.Oa19: "Oa19",
                obn.WV: "Oa20",
                obn.Oa21: "Oa21",
            }
        )

    def _create_gcps(self) -> None:
        """
        Create the GCPs sequence
        """

        # Compute only ig needed
        if not self._gcps:
            # Open lon/lat/alt files to populate the GCPs
            lat = self._read_nc(self._geo_file, self._lat_nc_name)
            lon = self._read_nc(self._geo_file, self._lon_nc_name)
            alt = self._read_nc(self._geo_file, self._alt_nc_name)

            # Create GCPs
            self._gcps = utils.create_gcps(lon, lat, alt)

    def _preprocess(
        self,
        band: Union[obn, str],
        resolution: float = None,
        to_reflectance: bool = True,
        subdataset: str = None,
        **kwargs,
    ) -> Union[CloudPath, Path]:
        """
        Pre-process S3 OLCI bands:
        - Convert radiance to reflectance
        - Geocode

        Args:
            band (Union[obn, str]): Band to preprocess (quality flags or others are accepted)
            resolution (float): Resolution
            to_reflectance (bool): Convert band to reflectance
            subdataset (str): Subdataset
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing {band: path}
        """
        band_str = band if isinstance(band, str) else band.name

        path = self._get_preprocessed_band_path(band, resolution=resolution)

        if not path.is_file():
            path = self._get_preprocessed_band_path(
                band, resolution=resolution, writable=True
            )

            # Get band regex
            if isinstance(band, obn):
                band_name = self.band_names[band]
                if not subdataset:
                    subdataset = self._replace(self._radiance_subds, band=band_name)
                filename = self._replace(self._radiance_file, band=band_name)
            else:
                filename = band

            # Get raw band
            band_arr = self._read_nc(
                filename, subdataset, dtype=kwargs.get("dtype", np.float32)
            )

            # Convert radiance to reflectances if needed
            # Convert first pixel by pixel before reprojection !
            if to_reflectance:
                LOGGER.debug(f"Converting {band_str} to reflectance")
                band_arr = self._rad_2_refl(band_arr, band)

                # Debug
                # utils.write(
                #     band_arr,
                #     self._get_band_folder(writable=True).joinpath(
                #         f"{self.condensed_name}_{band.name}_rad2refl.tif"
                #     ),
                # )

            # Geocode
            LOGGER.debug(f"Geocoding {band_str}")
            pp_arr = self._geocode(band_arr, resolution=resolution)

            # Write on disk
            utils.write(pp_arr, path)

        return path

    def _geocode(
        self, band_arr: xr.DataArray, resolution: float = None
    ) -> xr.DataArray:
        """
        Geocode Sentinel-3 bands

        Args:
            band_arr (xr.DataArray): Band array
            resolution (float): Resolution

        Returns:
            xr.DataArray: Geocoded DataArray
        """
        # Create GCPs if not existing
        self._create_gcps()

        # Assign a projection
        band_arr.rio.write_crs(WGS84, inplace=True)

        return band_arr.rio.reproject(
            dst_crs=self.crs,
            resolution=resolution,
            gcps=self._gcps,
            nodata=self._mask_nodata if band_arr.dtype == np.uint8 else self.nodata,
            num_threads=MAX_CORES,
            **{"SRC_METHOD": "GCP_TPS"},
        )

    def _rad_2_refl(self, band_arr: xr.DataArray, band: obn = None) -> xr.DataArray:
        """
        Convert radiance to reflectance

        Args:
            band_arr (xr.DataArray): Band array
            band (obn): Optical Band (for SLSTR only)

        Returns:
            dict: Dictionary containing {band: path}
        """
        rad_2_refl_path = self._get_band_folder() / f"rad_2_refl_{band.name}.npy"

        if not rad_2_refl_path.is_file():
            rad_2_refl_path = (
                self._get_band_folder(writable=True) / f"rad_2_refl_{band.name}.npy"
            )

            # Open SZA array (resampled to band_arr size)
            sza_path = self._get_band_folder() / "sza.tif"
            if not sza_path.is_file():
                sza_path = self._get_band_folder(writable=True) / "sza.tif"
                sza_nc = self._read_nc(self._geom_file, self._sza_name)
                utils.write(sza_nc, sza_path)

            with rasterio.open(sza_path) as ds_sza:
                # Values can be easily interpolated at pixels from Tie Points by linear interpolation using the
                # image column coordinate.
                sza, _ = rasters_rio.read(
                    ds_sza,
                    size=(band_arr.rio.width, band_arr.rio.height),
                    resampling=Resampling.bilinear,
                    masked=False,
                )
                sza_rad = sza.astype(np.float32) * np.pi / 180.0

            # Open solar flux (resampled to band_arr size)
            e0 = self._compute_e0(band)

            # Compute rad_2_refl coeff
            rad_2_refl_coeff = (np.pi / e0 / np.cos(sza_rad)).astype(np.float32)

            # Write on disk
            np.save(rad_2_refl_path, rad_2_refl_coeff)

        else:
            # Open rad_2_refl_coeff (resampled to band_arr size)
            rad_2_refl_coeff = np.load(rad_2_refl_path)

        return band_arr * rad_2_refl_coeff

    def _compute_e0(self, band: obn = None) -> np.ndarray:
        """
        Compute the solar spectral flux in mW / (m^2 * sr * nm)

        The Level 1 product provides measurements of top of atmosphere (ToA) radiances (mW/m2/sr/nm). These
        values can be converted to normalised reflectance for better comparison or merging of data with different
        sun angles as follows:
        reflectance = π* (ToA radiance / solar irradiance / cos(solar zenith angle))
        where the solar irradiance at ToA is given in the ‘solar_flux’ dataset  (instrument_data.nc  file)  for  each
        detector  and  each  channel,  and  the  solar  zenith  angle  is  given  at  Tie  Points  in the ‘SZA’ dataset
        (tie_geometry.nc file). The appropriate instrument detector is given at each pixel by the ‘detector_index’
        dataset (instrument_data.nc file).

        In https://sentinel.esa.int/documents/247904/4598069/Sentinel-3-OLCI-Land-Handbook.pdf/455f8c88-520f-da18-d744-f5cda41d2d91

        Args:
            band (obn): Optical Band (for SLSTR only)

        Returns:
            np.ndarray: Solar Flux

        """
        # Do not convert to int here as we want to keep the nans
        det_idx = self._read_nc(self._misc_file, self._det_index).data
        e0_det = self._read_nc(self._misc_file, self._solar_flux_name).data

        # Get band slice and open corresponding e0 for the detectors
        band_slice = int(self.band_names[band][-2:]) - 1
        e0_det = np.squeeze(e0_det[0, band_slice, :])

        # Create e0
        e0 = det_idx
        not_nan_idx = ~np.isnan(det_idx)
        e0[not_nan_idx] = e0_det[det_idx[not_nan_idx].astype(int)]

        return e0

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(
        self, band_arr: XDS_TYPE, band: obn, **kwargs
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...) for OLCI data.
        See there:
        https:sentinel.esa.int/documents/247904/1872756/Sentinel-3-OLCI-Product-Data-Format-Specification-OLCI-Level-1

        QUALITY FLAGS (From end to start of the 32 bits):
        | Bit |  Flag               |
        |----|----------------------|
        | 0  |   saturated21        |
        | 1  |   saturated20        |
        | 2  |   saturated19        |
        | 3  |   saturated18        |
        | 4  |   saturated17        |
        | 5  |   saturated16        |
        | 6  |   saturated15        |
        | 7  |   saturated14        |
        | 8  |   saturated13        |
        | 9  |   saturated12        |
        | 10 |   saturated11        |
        | 11 |   saturated10        |
        | 12 |   saturated09        |
        | 13 |   saturated08        |
        | 14 |   saturated07        |
        | 15 |   saturated06        |
        | 16 |   saturated05        |
        | 17 |   saturated04        |
        | 18 |   saturated03        |
        | 19 |   saturated02        |
        | 20 |   saturated01        |
        | 21 |   dubious            |
        | 22 |   sun-glint_risk     |
        | 23 |   duplicated         |
        | 24 |   cosmetic           |
        | 25 |   invalid            |
        | 26 |   straylight_risk    |
        | 27 |   bright             |
        | 28 |   tidal_region       |
        | 29 |   fresh_inland_water |
        | 30 |   coastline          |
        | 31 |   land               |

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            kwargs: Other arguments used to load bands

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Bit ids
        band_bit_id = {
            obn.Oa01: 20,  # Band 1
            obn.Oa02: 19,  # Band 2
            obn.CA: 18,  # Band 3
            obn.BLUE: 17,  # Band 4
            obn.Oa05: 16,  # Band 5
            obn.GREEN: 15,  # Band 6
            obn.YELLOW: 14,  # Band 7
            obn.RED: 13,  # Band 8
            obn.Oa09: 12,  # Band 9
            obn.Oa10: 11,  # Band 10
            obn.VRE_1: 10,  # Band 11
            obn.VRE_2: 9,  # Band 12
            obn.Oa13: 8,  # Band 13
            obn.Oa14: 7,  # Band 14
            obn.Oa15: 6,  # Band 15
            obn.VRE_3: 5,  # Band 16
            obn.NIR: 4,  # Band 17
            obn.NARROW_NIR: 4,  # Band 17
            obn.Oa18: 3,  # Band 18
            obn.Oa19: 2,  # Band 19
            obn.WV: 1,  # Band 20
            obn.Oa21: 0,  # Band 21
        }
        invalid_id = 25
        sat_band_id = band_bit_id[band]

        # Open quality flags
        # NOT OPTIMIZED, MAYBE CHECK INVALID PIXELS ON NOT GEOCODED DATA
        qual_regex = "qualityFlags"
        subds = "quality_flags"
        qual_flags_path = self._preprocess(
            qual_regex,
            subdataset=subds,
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
        invalid, sat = rasters.read_bit_array(
            qual_arr.astype(np.uint32), [invalid_id, sat_band_id]
        )

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), self._mask_true, self._mask_false)

        # Combine masks
        mask = no_data | invalid | sat

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        -> OLCI does not provide any cloud mask
        """
        return False

    def _load_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Does nothing for OLCI data

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        if bands:
            LOGGER.warning("Sentinel-3 OLCI L1B does not provide any cloud file")
        return {}

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (78.55043955912154, 31.172127033319388)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Open sun azimuth and zenith files
        sun_az = self._read_nc(self._geom_file, self._saa_name)
        sun_ze = self._read_nc(self._geom_file, self._sza_name)

        return sun_az.mean().data % 360, sun_ze.mean().data
