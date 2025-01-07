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
GEOSAT-2 products.
See `here <https://geosat.space/wp-content/uploads/2022/04/GEOSAT-2-Imagery-User-Guide-v3.2.pdf>`_
for more information.
"""

import io
import logging
from enum import unique

import numpy as np
import xarray as xr
from lxml import etree
from rasterio import crs as riocrs
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    BLUE,
    GREEN,
    NARROW_NIR,
    NIR,
    PAN,
    RED,
    BandNames,
    SpectralBand,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.dimap_v1_product import DimapV1Product
from eoreader.products.optical.optical_product import RawUnits
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Gs2BandCombination(ListEnum):
    """
    GEOSAT-2 band combination.
    See `here <https://geosat.space/wp-content/uploads/2022/04/GEOSAT-2-Imagery-User-Guide-v3.2.pdf>`_
    for more information.
    """

    PSH = "Pansharpened"
    """
    Pan-sharpened 4 bands
    """

    PS3 = "Pansharpened Natural Colors"
    """
    Pan-sharpened 321 Natural Colors
    """

    PS4 = "Pansharpened False Colors"
    """
    Pan-sharpened 432 False Colors
    """

    PAN = "Panchromatic"
    """
    Panchromatic only
    """

    MS4 = "Multispectral"
    """
    4 Multispectral files only
    """

    PM4 = "Bundle"
    """
    Bundle (Pan + Multispectral)
    """

    VAP = "Value Added Product"
    """
    Derived Product with original (i.e. vegetation index) -> Not handled by EOReader
    """


@unique
class Gs2ProductType(ListEnum):
    """
    GEOSAT-2 product types (processing levels)
    See `here <https://geosat.space/wp-content/uploads/2022/04/GEOSAT-2-Imagery-User-Guide-v3.2.pdf>`_
    for more information.
    """

    L1B = "Level 1B"
    """
    A calibrated and radiometrically corrected product, but not resampled.
    The geometric information is contained in a rational polynomial.
    The product includes: the Rational Polynomial Coefficients (RPC); the metadata with gain and bias values for
    each band, needed to convert the digital numbers into radiances at pixel level, and information about geographic
    projection (EPGS), corners geolocation, etc.
    """

    L1C = "Level 1C"
    """
    A calibrated and radiometrically corrected product, manually orthorectified and resampled to a map grid up to 75cm resolution.
    The geometric information is contained in the GeoTIFF tags.
    By default, the reference base for orthorectification is Google Earth.
    Other user-provided bases can be used on demand.
    Typical geometric error of this product is <10 m CE90, although lower geometric errors could be requested if needed.
    """

    L1D = "Level 1D"
    """
    A calibrated and radiometrically corrected product, manually orthorectified and resampled to a map grid up to 40cm resolution.
    The geometric information is contained in the GeoTIFF tags.
    """

    L1S = "Level 1S"
    """
    A calibrated and radiometrically corrected product, with enhanced resolution due to an AI-based process without losing quality.
    The geometric information is contained in a rational polynomial.
    The product includes:
    - the Rational Polynomial Coefficients (RPC);
    - the metadata with gain and bias values for each band, needed to convert the digital numbers into radiances at pixel level,
    - and information about geographic projection (EPGS), corners geolocation, etc.
    """


class Gs2Product(DimapV1Product):
    """
    Class of GEOSAT-2 products.
    See `here <https://geosat.space/wp-content/uploads/2022/04/GEOSAT-2-Imagery-User-Guide-v3.2.pdf>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._pan_res = None
        self._ms_res = None
        self.needs_extraction = False
        self._proj_prod_type = [Gs2ProductType.L1B, Gs2ProductType.L1S]
        self._raw_units = RawUnits.DN

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.band_combi = getattr(Gs2BandCombination, self.split_name[1])

        if self.band_combi == Gs2BandCombination.VAP:
            raise NotImplementedError(
                "VAP GEOSAT-2 products are not handled by EOReader."
            )

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        if self.band_combi in [
            Gs2BandCombination.PAN,
            Gs2BandCombination.PSH,
            Gs2BandCombination.PS3,
            Gs2BandCombination.PS4,
        ]:
            is_psh = "P"
        else:
            is_psh = "MS"

        resol = {
            Gs2ProductType.L1B: {"P": 1.0, "MS": 4.0},
            Gs2ProductType.L1S: {"P": 0.5, "MS": 2.0},
            Gs2ProductType.L1C: {"P": 0.75, "MS": 3.0},
            Gs2ProductType.L1D: {"P": 0.4, "MS": 2.0},
        }
        # Set MS and PAN resolutions
        self._ms_res = resol[self.product_type]["MS"]
        self._pan_res = resol[self.product_type]["P"]

        # Bundle: return MS resolution
        if self.product_type == Gs2BandCombination.PM4:
            self.pixel_size = self._ms_res
        # One res product
        else:
            self.pixel_size = resol[self.product_type][is_psh]

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        self.instrument = "HiRAIS"

    def _set_product_type(self) -> None:
        """
        Set products type
        """
        # Get MTD XML file
        prod_type = self.split_name[2]
        self.product_type = getattr(Gs2ProductType, prod_type)

        # Manage not orthorectified product
        if self.product_type in self._proj_prod_type:
            self.is_ortho = False

        if self.band_combi == Gs2ProductType.L1S:
            LOGGER.warning(
                "L1S processing level never have been tested with EOReader. Use it at your own risk!"
            )

    def _map_bands(self) -> None:
        """
        Map bands
        """
        # Create spectral bands
        pan = SpectralBand(
            eoreader_name=PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 560, WV_MAX: 900},
        )

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "BLUE", ID: 4, GSD: self._ms_res, WV_MIN: 466, WV_MAX: 525},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "GREEN", ID: 3, GSD: self._ms_res, WV_MIN: 532, WV_MAX: 599},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "RED", ID: 2, GSD: self._ms_res, WV_MIN: 640, WV_MAX: 697},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 1, GSD: self._ms_res, WV_MIN: 770, WV_MAX: 892},
        )

        # Manage bands of the product
        if self.band_combi == Gs2BandCombination.PAN:
            self.bands.map_bands({PAN: pan})
        elif self.band_combi == Gs2BandCombination.MS4:
            self.bands.map_bands(
                {
                    BLUE: blue,
                    GREEN: green,
                    RED: red,
                    NIR: nir,
                    NARROW_NIR: nir,
                }
            )
        elif self.band_combi == Gs2BandCombination.PM4:
            # Don't manage PAN band as it needs to rewrite the whole get_tile, get_ortho_path functions, even for other VHR products...
            LOGGER.warning(
                "For now, PAN bands are ignored in GEOSAT-2 Bundle products. "
                "If you need its support, please write an issue on GitHub."
            )
            self.bands.map_bands(
                {
                    # PAN: pan,
                    BLUE: blue,
                    GREEN: green,
                    RED: red,
                    NIR: nir,
                    NARROW_NIR: nir,
                }
            )
        elif self.band_combi == Gs2BandCombination.PSH:
            self.bands.map_bands(
                {
                    BLUE: blue.update(gsd=self._pan_res),
                    GREEN: green.update(gsd=self._pan_res),
                    RED: red.update(gsd=self._pan_res),
                    NIR: nir.update(gsd=self._pan_res),
                    NARROW_NIR: nir.update(gsd=self._pan_res),
                }
            )
        elif self.band_combi == Gs2BandCombination.PS3:
            self.bands.map_bands(
                {
                    BLUE: blue.update(gsd=self._pan_res, id=3),
                    GREEN: green.update(gsd=self._pan_res, id=2),
                    RED: red.update(gsd=self._pan_res, id=1),
                }
            )
        elif self.band_combi == Gs2BandCombination.PS4:
            self.bands.map_bands(
                {
                    GREEN: green.update(gsd=self._pan_res),
                    RED: red.update(gsd=self._pan_res),
                    NIR: nir.update(gsd=self._pan_res),
                    NARROW_NIR: nir.update(gsd=self._pan_res),
                }
            )
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        # TODO: check if HTML encoded or not
        crs_name = root.findtext(".//Projection_OGCWKT")

        return riocrs.CRS.from_string(crs_name)

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

        def get_curr_stack_mtd():
            # Two metadata files, on for MS the other for PAN
            # The default is to give the MS one
            if self.band_combi == Gs2BandCombination.PM4 and band == PAN:
                xml_root, _ = self._read_mtd_xml("PAN*.dim", r"PAN.*\.dim")
            else:
                xml_root, _ = self.read_mtd()

            return xml_root

        def get_curr_band_mtd(root_mtd):
            curr_band_mtd = None
            for band_info in root_mtd.iterfind(".//Spectral_Band_Info"):
                if int(band_info.findtext("BAND_INDEX")) == self.bands[band].id:
                    curr_band_mtd = band_info
                    break

            if curr_band_mtd is None:
                raise InvalidProductError(
                    "Incomplete metadata file: missing Spectral_Band_Info fields."
                )

            return curr_band_mtd

        curr_band_info = None
        root = None
        try:
            phys_unit = band_arr.PHYSICAL_UNIT
        except AttributeError:
            root = get_curr_stack_mtd()
            curr_band_info = get_curr_band_mtd(root)
            phys_unit = curr_band_info.findtext("PHYSICAL_UNIT")

        # If "N/A" is specified, it is impossible to convert to radiance/reflectance
        if phys_unit != "N/A":
            # Search in mtd as the band_array only contains last band metadata!
            if root is None:
                root = get_curr_stack_mtd()

            # Get the current band metadata
            if curr_band_info is None:
                curr_band_info = get_curr_band_mtd(root)

            # Load conversion parameters
            bias = float(curr_band_info.findtext("PHYSICAL_BIAS"))
            gain = float(curr_band_info.findtext("PHYSICAL_GAIN"))
            e_sun = float(curr_band_info.findtext("ESUN"))
            sun_earth_dist = float(root.findtext(".//EARTH_SUN_DISTANCE"))

            # Compute band in radiance
            band_arr = bias + band_arr * gain
            band_arr = self._toa_rad_to_toa_refl(band_arr, band, e_sun, sun_earth_dist)

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        if self.band_combi == Gs2BandCombination.PM4:
            LOGGER.warning(
                f"For {self.constellation.value} {self.band_combi.value} products, "
                f"the default metadata comes from the MS4 file."
            )
            mtd_from_path = "MS4*.dim"
            mtd_archived = r"MS4.*\.dim"
        else:
            mtd_from_path = ".dim"
            mtd_archived = r"\.dim"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _get_tile_path(self) -> AnyPathType:
        """
        Get the DIMAP filepath

        Returns:
            AnyPathType: DIMAP filepath
        """
        # TODO: support PAN bands
        prefix = "DE2_MS4_" if self.band_combi == Gs2BandCombination.PM4 else "DE2_"
        return self._get_path(prefix, "dim")

    def _get_ortho_path(self, **kwargs) -> AnyPathType:
        """
        Get the orthorectified path of the bands.

        Returns:
            AnyPathType: Orthorectified path
        """
        if self.product_type in self._proj_prod_type:
            # Compute RPCSs
            if self.is_archived:
                rpcs_file = io.BytesIO(self._read_archived_file(r".*_RPC\.txt"))
            else:
                rpcs_file = self.path.joinpath(self.name + "_RPC.txt")

            rpcs = utils.open_rpc_file(rpcs_file)
        else:
            rpcs = None
        return super()._get_ortho_path(rpcs=rpcs, **kwargs)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(regex=r".*QL\.png")
            else:
                quicklook_path = str(next(self.path.glob("*QL.png")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path
