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
""" Sentinel-3 OLCI products """
import logging
from typing import Union

import numpy as np
from rasterio.enums import Resampling
from sertit import rasters, rasters_rio
from sertit.rasters import XDS_TYPE

from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidTypeError
from eoreader.products.optical.s3_product import S3DataType, S3Product, S3ProductType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

# FROM SNAP:
# https://github.com/senbox-org/s3tbx/blob/197c9a471002eb2ec1fbd54e9a31bfc963446645/s3tbx-rad2refl/src/main/java/org/esa/s3tbx/processor/rad2refl/Rad2ReflConstants.java#L97
OLCI_SOLAR_FLUXES_DEFAULT = {
    "01": 1714.9084,  # Not used by EOReader
    "02": 1872.3961,  # Not used by EOReader
    obn.CA: 1926.6102,
    obn.BLUE: 1930.2483,
    "05": 1804.2762,  # Not used by EOReader
    obn.GREEN: 1651.5836,
    "07": 1531.4067,  # Not used by EOReader
    obn.RED: 1475.615,
    "09": 1408.9949,  # Not used by EOReader
    "10": 1265.5425,  # Not used by EOReader
    obn.VRE_1: 1255.4227,
    obn.VRE_2: 1178.0286,
    "13": 955.07043,  # Not used by EOReader
    "14": 914.18945,  # Not used by EOReader
    "15": 882.8275,  # Not used by EOReader
    obn.VRE_3: 882.8275,
    obn.NIR: 882.8275,
    obn.NARROW_NIR: 882.8275,
    "18": 882.8275,  # Not used by EOReader
    "19": 882.8275,  # Not used by EOReader
    obn.WV: 882.8275,
    obn.FAR_NIR: 882.8275,
}


class S3OlciProduct(S3Product):
    """
    Class of Sentinel-3 OLCI Products

    **Note**: All S3-OLCI bands won't be used in EOReader !
    """

    def _set_preprocess_members(self):
        """ Set pre-process members """
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
        self._sza_name = "SZA"
        self._sze_name = "SZA"

        # Rad 2 Refl
        self._misc_file = "instrument_data.nc"
        self._solar_flux_name = "solar_flux"

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Post init done by the super class
        super()._pre_init()

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
                obn.CA: "03",
                obn.BLUE: "04",
                obn.GREEN: "06",
                obn.RED: "08",
                obn.VRE_1: "11",
                obn.VRE_2: "12",
                obn.VRE_3: "16",
                obn.NIR: "17",
                obn.NARROW_NIR: "17",
                obn.WV: "20",
                obn.FAR_NIR: "21",
            }
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
            band_regex = f"Oa{self.band_names[band]}_radiance.nc"
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
        Manage invalid pixels (Nodata, saturated, defective...) for OLCI data.
        See there:
        https:#sentinel.esa.int/documents/247904/1872756/Sentinel-3-OLCI-Product-Data-Format-Specification-OLCI-Level-1

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
        | 11 |   saturated09        |
        | 12 |   saturated08        |
        | 13 |   saturated07        |
        | 14 |   saturated06        |
        | 15 |   saturated05        |
        | 16 |   saturated04        |
        | 17 |   saturated03        |
        | 18 |   saturated02        |
        | 19 |   saturated01        |
        | 20 |   dubious            |
        | 21 |   sun-glint_risk     |
        | 22 |   duplicated         |
        | 23 |   cosmetic           |
        | 24 |   invalid            |
        | 25 |   straylight_risk    |
        | 26 |   bright             |
        | 27 |   tidal_region       |
        | 28 |   fresh_inland_water |
        | 29 |   coastline          |
        | 30 |   land               |

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames

        Returns:
            XDS_TYPE: Cleaned band array
        """
        nodata_true = 1
        nodata_false = 0

        # Bit ids
        band_bit_id = {
            obn.CA: 18,  # Band 2
            obn.BLUE: 17,  # Band 3
            obn.GREEN: 14,  # Band 6
            obn.RED: 12,  # Band 8
            obn.VRE_1: 10,  # Band 11
            obn.VRE_2: 9,  # Band 12
            obn.VRE_3: 5,  # Band 16
            obn.NIR: 4,  # Band 17
            obn.NARROW_NIR: 4,  # Band 17
            obn.WV: 1,  # Band 20
            obn.FAR_NIR: 0,  # Band 21
        }
        invalid_id = 24
        sat_band_id = band_bit_id[band]

        # Open quality flags
        qual_regex = "qualityFlags"
        qual_flags_path = self._preprocess(
            qual_regex, resolution=band_arr.rio.resolution(), to_reflectance=False
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
        no_data = np.where(np.isnan(band_arr.data), nodata_true, nodata_false)

        # Combine masks
        mask = no_data | invalid | sat

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        - SLSTR does
        - OLCI does not provide any cloud mask
        """
        return False

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Does nothing for OLCI data

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        return {}
