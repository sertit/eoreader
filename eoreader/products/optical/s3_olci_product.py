# Copyright 2025, SERTIT-ICube - France, https:#sertit.unistra.fr/
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
from typing import Union

import numpy as np
import rasterio
import xarray as xr
from rasterio.enums import Resampling
from sertit import rasters, rasters_rio
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    BLUE,
    CA,
    GREEN,
    GREEN_1,
    NARROW_NIR,
    NIR,
    RED,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    YELLOW,
    BandNames,
    Oa01,
    Oa02,
    Oa09,
    Oa10,
    Oa13,
    Oa14,
    Oa15,
    Oa18,
    Oa19,
    Oa21,
    SpectralBand,
)
from eoreader.exceptions import InvalidTypeError
from eoreader.products import S3DataType, S3Product, S3ProductType
from eoreader.stac import CENTER_WV, DESCRIPTION, FWHM, GSD, ID, NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# FROM SNAP:
# https://github.com/senbox-org/s3tbx/blob/197c9a471002eb2ec1fbd54e9a31bfc963446645/s3tbx-rad2refl/src/main/java/org/esa/s3tbx/processor/rad2refl/Rad2ReflConstants.java#L97
# Not used for now
OLCI_SOLAR_FLUXES_DEFAULT = {
    Oa01: 1714.9084,
    Oa02: 1872.3961,
    CA: 1926.6102,
    BLUE: 1930.2483,
    GREEN_1: 1804.2762,
    GREEN: 1651.5836,
    YELLOW: 1531.4067,
    RED: 1475.615,
    Oa09: 1408.9949,
    Oa10: 1265.5425,
    VRE_1: 1255.4227,
    VRE_2: 1178.0286,
    Oa13: 955.07043,
    Oa14: 914.18945,
    Oa15: 882.8275,
    VRE_3: 882.8275,
    NIR: 882.8275,
    NARROW_NIR: 882.8275,
    Oa18: 882.8275,
    Oa19: 882.8275,
    WV: 882.8275,
    Oa21: 882.8275,
}


class S3OlciProduct(S3Product):
    """
    Class of Sentinel-3 OLCI Products
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        """
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/observation-mode-desc

        Note that the name of each netCDF file provides information about its content.
        """
        super().__init__(
            product_path, archive_path, output_path, remove_tmp, **kwargs
        )  # Order is important here, gcps NEED to be after this

    def _get_preprocessed_band_path(
        self,
        band: Union[BandNames, str],
        pixel_size: Union[float, tuple, list] = None,
        writable=True,
    ) -> AnyPathType:
        """
        Create the pre-processed band path

        Args:
            band (band: Union[BandNames, str]): Wanted band (quality flags accepted)
            pixel_size (Union[float, tuple, list]): Resolution of the wanted UTM band
            writable (bool): Do we need to write the pre-processed band ?

        Returns:
            AnyPathType: Pre-processed band path
        """
        res_str = self._pixel_size_to_str(pixel_size)
        band_str = band.name if isinstance(band, BandNames) else band

        return self._get_band_folder(writable=writable).joinpath(
            f"{self.condensed_name}_{band_str}_{res_str}.tif"
        )

    def _set_preprocess_members(self):
        """Set pre-process members"""
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

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        self.pixel_size = 300.0

    def _set_product_type(self) -> None:
        """
        Set products type

        More on spectral bands `here <https://sentinel.esa.int/web/sentinel/user-guides/sentinel-3-olci/resolutions/radiometric>`_.
        """
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        self.product_type = S3ProductType.OLCI_EFR
        self._data_type = S3DataType.EFR

    def _map_bands(self) -> None:
        """
        Map bands
        """
        # Bands
        olci_bands = {
            Oa01: SpectralBand(
                eoreader_name=Oa01,
                **{
                    NAME: "Oa01",
                    ID: 1,
                    GSD: self.pixel_size,
                    CENTER_WV: 400,
                    FWHM: 15,
                    DESCRIPTION: "Aerosol correction, improved water constituent retrieval",
                },
            ),
            Oa02: SpectralBand(
                eoreader_name=Oa02,
                **{
                    NAME: "Oa02",
                    ID: 2,
                    GSD: self.pixel_size,
                    CENTER_WV: 412.5,
                    FWHM: 10,
                    DESCRIPTION: "Yellow substance and detrital pigments (turbidity)",
                },
            ),
            CA: SpectralBand(
                eoreader_name=CA,
                **{
                    NAME: "Oa03",
                    ID: 3,
                    GSD: self.pixel_size,
                    CENTER_WV: 442.5,
                    FWHM: 10,
                    DESCRIPTION: "Chlorophyll absorption maximum, biogeochemistry, vegetation",
                },
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "Oa04",
                    ID: 4,
                    GSD: self.pixel_size,
                    CENTER_WV: 490,
                    FWHM: 10,
                    DESCRIPTION: "High Chlorophyll",
                },
            ),
            GREEN_1: SpectralBand(
                eoreader_name=GREEN_1,
                **{
                    NAME: "Oa05",
                    ID: 5,
                    GSD: self.pixel_size,
                    CENTER_WV: 510,
                    FWHM: 10,
                    DESCRIPTION: "Chlorophyll, sediment, turbidity, red tide",
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "Oa06",
                    ID: 6,
                    GSD: self.pixel_size,
                    CENTER_WV: 560,
                    FWHM: 10,
                    DESCRIPTION: "Chlorophyll reference (Chlorophyll minimum)",
                },
            ),
            YELLOW: SpectralBand(
                eoreader_name=YELLOW,
                **{
                    NAME: "Oa07",
                    ID: 7,
                    GSD: self.pixel_size,
                    CENTER_WV: 620,
                    FWHM: 10,
                    DESCRIPTION: "Sediment loading",
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "Oa08",
                    ID: 8,
                    GSD: self.pixel_size,
                    CENTER_WV: 665,
                    FWHM: 10,
                    DESCRIPTION: "Chlorophyll (2nd Chlorophyll absorption maximum), sediment, yellow substance / vegetation",
                },
            ),
            Oa09: SpectralBand(
                eoreader_name=Oa09,
                **{
                    NAME: "Oa09",
                    ID: 9,
                    GSD: self.pixel_size,
                    CENTER_WV: 673.75,
                    FWHM: 7.5,
                    DESCRIPTION: "For improved fluorescence retrieval and to better account for smile together with the bands 665 and 680 nm",
                },
            ),
            Oa10: SpectralBand(
                eoreader_name=Oa10,
                **{
                    NAME: "Oa10",
                    ID: 10,
                    GSD: self.pixel_size,
                    CENTER_WV: 681.25,
                    FWHM: 7.5,
                    DESCRIPTION: "Chlorophyll fluorescence peak, red edge",
                },
            ),
            VRE_1: SpectralBand(
                eoreader_name=VRE_1,
                **{
                    NAME: "Oa11",
                    ID: 11,
                    GSD: self.pixel_size,
                    CENTER_WV: 708.75,
                    FWHM: 10,
                    DESCRIPTION: "Chlorophyll fluorescence baseline, red edge transition",
                },
            ),
            VRE_2: SpectralBand(
                eoreader_name=VRE_2,
                **{
                    NAME: "Oa12",
                    ID: 12,
                    GSD: self.pixel_size,
                    CENTER_WV: 753.75,
                    FWHM: 7.5,
                    DESCRIPTION: "O2 absorption/clouds, vegetation",
                },
            ),
            Oa13: SpectralBand(
                eoreader_name=Oa13,
                **{
                    NAME: "Oa13",
                    ID: 13,
                    GSD: self.pixel_size,
                    CENTER_WV: 761.25,
                    FWHM: 2.5,
                    DESCRIPTION: "O2 absorption band/aerosol correction.",
                },
            ),
            Oa14: SpectralBand(
                eoreader_name=Oa14,
                **{
                    NAME: "Oa14",
                    ID: 14,
                    GSD: self.pixel_size,
                    CENTER_WV: 764.375,
                    FWHM: 3.75,
                    DESCRIPTION: "Atmospheric correction",
                },
            ),
            Oa15: SpectralBand(
                eoreader_name=Oa15,
                **{
                    NAME: "Oa15",
                    ID: 15,
                    GSD: self.pixel_size,
                    CENTER_WV: 767.5,
                    FWHM: 2.5,
                    DESCRIPTION: "O2A used for cloud top pressure, fluorescence over land",
                },
            ),
            VRE_3: SpectralBand(
                eoreader_name=VRE_3,
                **{
                    NAME: "Oa16",
                    ID: 16,
                    GSD: self.pixel_size,
                    CENTER_WV: 778.75,
                    FWHM: 15,
                    DESCRIPTION: "Atmos. corr./aerosol corr.",
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "Oa17",
                    ID: 17,
                    GSD: self.pixel_size,
                    CENTER_WV: 865,
                    FWHM: 20,
                    DESCRIPTION: "Atmospheric correction/aerosol correction, clouds, pixel co-registration",
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "Oa17",
                    ID: 17,
                    GSD: self.pixel_size,
                    CENTER_WV: 865,
                    FWHM: 20,
                    DESCRIPTION: "Atmospheric correction/aerosol correction, clouds, pixel co-registration",
                },
            ),
            Oa18: SpectralBand(
                eoreader_name=Oa18,
                **{
                    NAME: "Oa18",
                    ID: 18,
                    GSD: self.pixel_size,
                    CENTER_WV: 885,
                    FWHM: 10,
                    DESCRIPTION: "Water vapour absorption reference band. Common reference band with SLSTR instrument. Vegetation monitoring",
                },
            ),
            Oa19: SpectralBand(
                eoreader_name=Oa19,
                **{
                    NAME: "Oa19",
                    ID: 19,
                    GSD: self.pixel_size,
                    CENTER_WV: 900,
                    FWHM: 10,
                    DESCRIPTION: "Water vapour absorption/vegetation monitoring (maximum reflectance)",
                },
            ),
            WV: SpectralBand(
                eoreader_name=WV,
                **{
                    NAME: "Oa20",
                    ID: 20,
                    GSD: self.pixel_size,
                    CENTER_WV: 940,
                    FWHM: 20,
                    DESCRIPTION: "Water vapour absorption, Atmospheric correction/aerosol correction",
                },
            ),
            Oa21: SpectralBand(
                eoreader_name=Oa21,
                **{
                    NAME: "Oa21",
                    ID: 21,
                    GSD: self.pixel_size,
                    CENTER_WV: 1020,
                    FWHM: 40,
                    DESCRIPTION: "Atmospheric correction/aerosol correction",
                },
            ),
        }
        self.bands.map_bands(olci_bands)

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
            # Get band filename and subdataset
            filename = self._replace(self._radiance_file, band=self.bands[band].name)

            if self.is_archived:
                raw_path = self._get_archived_path(f".*{filename}")
            else:
                try:
                    raw_path = next(self.path.glob(f"*{filename}"))
                except StopIteration as exc:
                    raise FileNotFoundError(
                        f"Non existing file {filename} in {self.path}"
                    ) from exc

            raw_band_paths[band] = raw_path

        return raw_band_paths

    def _preprocess(
        self,
        band: Union[BandNames, str],
        pixel_size: float = None,
        to_reflectance: bool = True,
        subdataset: str = None,
        **kwargs,
    ) -> AnyPathType:
        """
        Pre-process S3 OLCI bands:
        - Convert radiance to reflectance
        - Geocode

        Args:
            band (Union[BandNames, str]): Band to preprocess (quality flags or others are accepted)
            pixel_size (float): Pixl size
            to_reflectance (bool): Convert band to reflectance
            subdataset (str): Subdataset
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing {band: path}
        """
        band_str = band if isinstance(band, str) else band.name

        pp_path = self._get_preprocessed_band_path(
            band, pixel_size=pixel_size, writable=False
        )

        if not pp_path.is_file():
            pp_path = self._get_preprocessed_band_path(
                band, pixel_size=pixel_size, writable=True
            )

            # Get band regex
            if isinstance(band, BandNames):
                band_name = self.bands[band].name
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

            # Geocode
            LOGGER.debug(f"Geocoding {band_str}")
            band_arr = self._geocode(band_arr, pixel_size=pixel_size, **kwargs)

            # Write on disk
            utils.write(band_arr, pp_path)

        return pp_path

    def _rad_2_refl(
        self, band_arr: xr.DataArray, band: BandNames = None
    ) -> xr.DataArray:
        """
        Convert radiance to reflectance

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
            band_arr (xr.DataArray): Band array
            band (BandNames): Spectral Band (for SLSTR only)

        Returns:
            dict: Dictionary containing {band: path}
        """
        rad_2_refl_path, rad_2_refl_exists = self._get_out_path(
            f"rad_2_refl_{band.name}.npy"
        )
        if not rad_2_refl_exists:
            # Open SZA array (resampled to band_arr size)
            sza_path, sza_exists = self._get_out_path("sza.tif")

            # May have been created before (don't recreate it)
            if not sza_exists and not sza_path.is_file():
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
            np.save(str(rad_2_refl_path), rad_2_refl_coeff)

        else:
            # Open rad_2_refl_coeff (resampled to band_arr size)
            rad_2_refl_coeff = utils.load_np(rad_2_refl_path, self._tmp_process)

        return band_arr * rad_2_refl_coeff

    def _compute_e0(self, band: BandNames = None) -> np.ndarray:
        """
        Compute the solar spectral flux in mW / (m^2 * sr * nm)

        Args:
            band (BandNames): Spectral Band (for SLSTR only)

        Returns:
            np.ndarray: Solar Flux

        """
        # Do not convert to int here as we want to keep the nans
        det_idx = self._read_nc(self._misc_file, self._det_index).data
        e0_det = self._read_nc(self._misc_file, self._solar_flux_name).data

        # Get band slice and open corresponding e0 for the detectors
        band_slice = int(self.bands[band].name[-2:]) - 1
        e0_det = np.squeeze(e0_det[0, band_slice, :])

        # Create e0
        e0 = det_idx
        not_nan_idx = ~np.isnan(det_idx)
        e0[not_nan_idx] = e0_det[det_idx[not_nan_idx].astype(int)]

        return e0

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
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
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # Bit ids
        band_bit_id = {
            Oa01: 20,  # Band 1
            Oa02: 19,  # Band 2
            CA: 18,  # Band 3
            BLUE: 17,  # Band 4
            GREEN_1: 16,  # Band 5
            GREEN: 15,  # Band 6
            YELLOW: 14,  # Band 7
            RED: 13,  # Band 8
            Oa09: 12,  # Band 9
            Oa10: 11,  # Band 10
            VRE_1: 10,  # Band 11
            VRE_2: 9,  # Band 12
            Oa13: 8,  # Band 13
            Oa14: 7,  # Band 14
            Oa15: 6,  # Band 15
            VRE_3: 5,  # Band 16
            NIR: 4,  # Band 17
            NARROW_NIR: 4,  # Band 17
            Oa18: 3,  # Band 18
            Oa19: 2,  # Band 19
            WV: 1,  # Band 20
            Oa21: 0,  # Band 21
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
            pixel_size=band_arr.rio.resolution(),
            to_reflectance=False,
        )

        # Open flag file
        qual_arr = utils.read(
            qual_flags_path,
            size=(band_arr.rio.width, band_arr.rio.height),
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            as_type=np.uint32,
            **kwargs,
        )
        invalid, sat = rasters.read_bit_array(qual_arr, [invalid_id, sat_band_id])

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), self._mask_true, self._mask_false)

        # Combine masks
        mask = no_data | invalid | sat

        return self._set_nodata_mask(band_arr, mask)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        -> OLCI does not provide any cloud mask
        """
        return False

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Does nothing for OLCI data

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
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

        return float(sun_az.mean().data) % 360, float(sun_ze.mean().data)
