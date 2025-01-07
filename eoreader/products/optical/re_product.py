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
"""
RapidEye products.
See
`Product specifications <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
and `Planet documentation <https://developers.planet.com/docs/data/rapideye/>`_
for more information.
"""

import logging
from datetime import datetime
from enum import unique
from typing import Union

import numpy as np
import xarray as xr
from sertit import files
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME
from eoreader.bands import (
    BLUE,
    GREEN,
    NARROW_NIR,
    NIR,
    RED,
    VRE_1,
    BandNames,
    SpectralBand,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.planet_product import PlanetProduct
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN

LOGGER = logging.getLogger(EOREADER_NAME)

_RE_EAI = {
    BLUE: 1997.8,
    GREEN: 1863.5,
    RED: 1560.4,
    VRE_1: 1395.0,
    NIR: 1124.4,
    NARROW_NIR: 1124.4,
}
"""
From RE `Product specifications <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
"""


@unique
class ReProductType(ListEnum):
    """
    RapidEye product types (processing levels)

    See `Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
    for more information.
    """

    L1B = "RapidEye Basic Scene Product"
    """
    Radiometric and sensor corrections applied to the data.
    On-board spacecraft attitude and ephemeris applied to the data.
    """

    L3A = "RapidEye Ortho Tile Product"
    """
    Radiometric and sensor corrections applied to the data.
    Imagery is orthorectified using the RPCs and an elevation model.
    """


class ReProduct(PlanetProduct):
    """
    Class of PlanetScope products.
    See `Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.constellation = self._get_constellation()
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        try:
            if self.is_archived:
                self._get_archived_path(r".*udm\.tif")
            else:
                next(self.path.glob("**/*udm.tif"))
            self._has_udm = True
        except (FileNotFoundError, StopIteration):
            # Some RE products don't have udm files
            LOGGER.warning(
                "UDM mask not found. This product won't be cleaned and won't have any cloud band."
            )
            pass

        self._has_cloud_cover = True

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        self.pixel_size = 5.0

    def _set_instrument(self) -> None:
        """
        Set instrument

        See: https://space.oscar.wmo.int/instruments/view/reis
        """
        self.instrument = "REIS"

    def _map_bands(self):
        """
        Map bands
        See <Product specs `https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf`>_ for more information.
        """
        gsd = 6.5

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "Blue", ID: 1, GSD: gsd, WV_MIN: 440, WV_MAX: 510},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "Green", ID: 2, GSD: gsd, WV_MIN: 520, WV_MAX: 590},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "Red", ID: 3, GSD: gsd, WV_MIN: 630, WV_MAX: 685},
        )

        vre = SpectralBand(
            eoreader_name=VRE_1,
            **{NAME: "Red Edge", ID: 4, GSD: gsd, WV_MIN: 690, WV_MAX: 730},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 5, GSD: gsd, WV_MIN: 760, WV_MAX: 850},
        )

        # Set the band map
        self.bands.map_bands(
            {
                BLUE: blue,
                GREEN: green,
                RED: red,
                VRE_1: vre,
                NIR: nir,
                NARROW_NIR: nir,
            }
        )

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Manage product type
        prod_type = root.findtext(f".//{nsmap['eop']}productType")
        if not prod_type:
            raise InvalidProductError(
                "Cannot find the product type in the metadata file"
            )

        # Set correct product type
        self.product_type = getattr(ReProductType, prod_type)
        if self.product_type == ReProductType.L1B:
            # TODO: implement orthorectification for Planet products
            raise NotImplementedError(
                f"Basic Scene Product are not managed for {self.constellation.value} products:\n{self.path}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms
            >>> prod.get_datetime(as_datetime=False)
            '20190625T105728'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, nsmap = self.read_mtd()
            datetime_str = root.findtext(f".//{nsmap['eop']}acquisitionDate")
            if not datetime_str:
                raise InvalidProductError(
                    "Cannot find acquisitionDate in the metadata file."
                )

            # Convert to datetime
            datetime_str = datetime_str.split(".")[
                0
            ]  # Too many microseconds, remove them
            datetime_str = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")

        else:
            datetime_str = self.datetime

        if not as_datetime:
            datetime_str = datetime_str.strftime(DATETIME_FMT)

        return datetime_str

    def _get_stack_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet stack path(s)

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        if self._merged:
            stack_path, _ = self._get_out_path(f"{self.condensed_name}_analytic.vrt")
            if as_list:
                stack_path = [stack_path]
        else:
            stack_path = self._get_path(
                self.name, "tif", invalid_lookahead=["_udm", "_browse"], as_list=as_list
            )
            if not stack_path:
                stack_path = self._get_path(self.name, "TIF", as_list=as_list)

        return stack_path

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        See
        `Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
        for more information.

        Args:
            dn_arr (xr.DataArray): DN array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Radiance array
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Open identifier
        rad_coef = None
        for band_mtd in root.iterfind(
            f".//{nsmap[self._nsmap_key]}bandSpecificMetadata"
        ):
            if (
                int(band_mtd.findtext(f".//{nsmap[self._nsmap_key]}bandNumber"))
                == self.bands[band].id
            ):
                rad_coef = float(
                    band_mtd.findtext(
                        f".//{nsmap[self._nsmap_key]}radiometricScaleFactor"
                    )
                )
                break

        if rad_coef is None:
            raise InvalidProductError(
                "Couldn't find any radiometricScaleFactor in the product metadata!"
            )

        # To reflectance
        return dn_arr * rad_coef

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        See
        `Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
        for more information.

        WARNING: in this formula, d**2 = 1 / sqrt(dt) !

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """

        # Compute the coefficient converting TOA radiance in TOA reflectance
        dt = self._sun_earth_distance_variation() ** 2
        _, sun_zen = self.get_mean_sun_angles()
        rad_sun_zen = np.deg2rad(sun_zen)
        eai = _RE_EAI[band]
        toa_refl_coeff = np.pi / (eai * dt * np.cos(rad_sun_zen))

        return rad_arr.copy(data=toa_refl_coeff * rad_arr)

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
        # Convert DN into radiance
        band_arr = self._dn_to_toa_rad(band_arr, band)

        # Convert radiance into reflectance
        band_arr = self._toa_rad_to_toa_refl(band_arr, band)

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self._get_archived_rio_path(regex=r".*_browse\.tif")
            else:
                quicklook_path = str(next(self.path.glob("**/*_browse.tif")))
        except (StopIteration, FileNotFoundError):
            pass

        return quicklook_path

    def _merge_subdatasets_mtd(self):
        """
        Merge subdataset, when several Planet products avec been ordered together
        Will create a reflectance (if possible) VRT, a UDM/UDM2 VRT and a merged metadata XML file.
        """
        LOGGER.warning(
            "_merge_subdatasets_mtd is not yet implemented (because of lack of tiled RapideEye product), only copying the first metadata file!"
        )

        mtd_file, mtd_exists = self._get_out_path(
            f"{self.condensed_name}_metadata.json"
        )
        if not mtd_exists:
            files.copy(self._get_path("metadata", "xml"), mtd_file)
