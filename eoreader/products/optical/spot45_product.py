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
SPOT-4/5 products.
See `here <http://www.engesat.com.br/wp-content/uploads/S5-ST-73-1-CN_2_9-Spec-Format-Produits-SPOT.pdf>`_
for more information.
"""

import logging
from datetime import timedelta
from enum import unique

import numpy as np
import xarray as xr
from lxml import etree
from rasterio import crs as riocrs
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    GREEN,
    NARROW_NIR,
    NIR,
    PAN,
    RED,
    SWIR_1,
    BandNames,
    SpectralBand,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products import DimapV1Product
from eoreader.products.optical.optical_product import RawUnits
from eoreader.reader import Constellation
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN

LOGGER = logging.getLogger(EOREADER_NAME)

_DIMAP_BAND_MTD = {
    PAN: "PAN",
    GREEN: "XS1",
    RED: "XS2",
    NIR: "XS3",
    NARROW_NIR: "XS3",
    SWIR_1: "XS4",
}

# https://spot.cnes.fr/sites/default/files/migration/smsc/spot/calibration_synthesis_SPOT1245_ed1.pdf (3.3)
# HRVIR 1, 2
_SPOT4_E0 = {
    PAN: [1570.2, 1589],
    GREEN: [1842.9, 1850.9],
    RED: [1570.2, 1589],
    NIR: [1052.1, 1054.8],
    NARROW_NIR: [1052.1, 1054.8],
    SWIR_1: [235.84, 241.93],
}

# HRG 1, 2
_SPOT5_E0 = {
    PAN: [1764.2, 1775],
    GREEN: [1859.8, 1859.8],
    RED: [1575.3, 1577.6],
    NIR: [1043.9, 1048.2],
    NARROW_NIR: [1043.9, 1048.2],
    SWIR_1: [238.87, 237.78],
}
"""
The values of the normalized solar irradiance have been computed using WMO (World Meteorogical Organization) spectral solar irradiance.
"""


@unique
class Spot4BandCombination(ListEnum):
    """
    Band combination for SPOT4 data
    See `this <https://www.intelligence-airbusds.com/files/pmedia/public/r451_9_resolutionspectralmodes_uk_sept2010.pdf>`_ for more information.
    """

    M = "M"
    """
    "M" for Spot 4 PAN product (10 m)
    """

    X = "X"
    """
    "X" for Spot 4 multispectral product (3 bands, without SWIR) (20 m)
    """

    I = "I"  # noqa
    """
    "I" for Spot 4 multispectral product (4 bands, with SWIR) (20 m)
    """

    MX = "M+X"
    """
    "M+X" for Spot 4 merge product (3 bands, without SWIR) (10 m)
    """

    MI = "M+I"
    """
    "M+I" for Spot 4 merge product (4 bands, with SWIR) (10 m)
    """


@unique
class Spot5BandCombination(ListEnum):
    """
    Band combination for SPOT4/5 data
    See `this <https://www.intelligence-airbusds.com/files/pmedia/public/r451_9_resolutionspectralmodes_uk_sept2010.pdf>`_ for more information.
    """

    T = "T"
    """
    "T" for supermode Spot data (2.5 m)
    """

    HM = "HM"
    """
    "HM" for Spot-5 PAN data (5 m)
    """

    X = "X"
    """
    "X" for 3 bands extracted from 4 bands (10 m)
    """

    J = "J"
    """
    "J" for Spot 5 multipectral product (4 bands, with SWIR) (10 m)
    """

    HMX = "HM+X"
    """
    "HM+X" for Spot 5 merge product (3 bands, without SWIR) (5 m)
    """

    TX = "T+X"
    """
    "T+X" for Spot 5 supermode and multipectral merge product (3 bands, without SWIR) (2.5 m)
    """


@unique
class Spot45ProductType(ListEnum):
    """
    Product Type for SPOT4/5 data
    See `here <http://www.engesat.com.br/wp-content/uploads/S5-ST-73-1-CN_2_9-Spec-Format-Produits-SPOT.pdf>`_ for more information.
    """

    L0 = "0"
    """
    Level-0
    """

    L1A = "1A"
    """
    Level-1A
    """

    L1B = "1B"
    """
    Level-1B
    """

    L2A = "2A"
    """
    Level-2A
    """


class Spot45Product(DimapV1Product):
    """
    Class of SPOT4/5 products.
    See `here <http://www.engesat.com.br/wp-content/uploads/S5-ST-73-1-CN_2_9-Spec-Format-Produits-SPOT.pdf>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        root, _ = self.read_mtd()
        mission_idx = int(root.findtext(".//MISSION_INDEX"))
        if mission_idx == 4:
            self._supermode_res = None
            self._pan_res = 10.0
            self._ms_res = 20.0
            self.constellation = Constellation.SPOT4
        elif mission_idx == 5:
            self._supermode_res = 2.5
            self._pan_res = 5.0
            self._ms_res = 10.0
            self.constellation = Constellation.SPOT5
        else:
            raise InvalidProductError("Mission index should be 4 or 5.")

        self.needs_extraction = False
        self._use_filename = True
        self._proj_prod_type = [Spot45ProductType.L0]

        # Raw units
        rad_proc = root.findtext(".//RADIOMETRIC_PROCESSING").upper()

        if rad_proc == "REFLECTANCE":
            self._raw_units = RawUnits.REFL
        elif rad_proc in "BASIC":
            self._raw_units = RawUnits.DN
        else:
            self._raw_units = RawUnits.NONE

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _set_band_combi(self) -> None:
        """
        Set Band combination
        """
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//SPECTRAL_PROCESSING")
        if not band_combi:
            raise InvalidProductError("SPECTRAL_PROCESSING not found in metadata!")
        if self.constellation == Constellation.SPOT4:
            self.band_combi = Spot4BandCombination.from_value(band_combi)
        else:
            self.band_combi = Spot5BandCombination.from_value(band_combi)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        if self.band_combi is None:
            self._set_band_combi()

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Not Pansharpened images
        if self.band_combi in [
            Spot4BandCombination.X,
            Spot4BandCombination.I,
            Spot5BandCombination.X,
            Spot5BandCombination.J,
        ]:
            self.pixel_size = self._ms_res
        # Pansharpened images
        elif self.band_combi in [
            Spot4BandCombination.M,
            Spot4BandCombination.MX,
            Spot4BandCombination.MI,
            Spot5BandCombination.HM,
            Spot5BandCombination.HMX,
        ]:
            self.pixel_size = self._pan_res
        # Supermode images
        else:
            self.pixel_size = self._supermode_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        SPOT-4: https://space.oscar.wmo.int/instruments/view/hrvir
        SPOT-5: https://space.oscar.wmo.int/instruments/view/hrg
        """
        if self.constellation == Constellation.SPOT4:
            self.instrument = "HRVIR"
        else:
            self.instrument = "HRG"

    def _set_product_type(self) -> None:
        """
        Set products type

        See Vision-1_web_201906.pdf for more information.
        """
        if self.product_type is None:
            # Get MTD XML file
            root, _ = self.read_mtd()
            proc_lvl = root.findtext(".//SCENE_PROCESSING_LEVEL")
            self.product_type = Spot45ProductType.from_value(proc_lvl)

            # Manage not orthorectified product
            if self.product_type == Spot45ProductType.L0:
                self.is_ortho = False

    def _map_bands(self) -> None:
        """
        Map bands
        """
        if self.constellation == Constellation.SPOT4:
            # Create spectral bands
            pan = SpectralBand(
                eoreader_name=PAN,
                **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 610, WV_MAX: 680},
            )

            green = SpectralBand(
                eoreader_name=GREEN,
                **{NAME: "GREEN", ID: 3, GSD: self._ms_res, WV_MIN: 500, WV_MAX: 590},
            )

            red = SpectralBand(
                eoreader_name=RED,
                **{NAME: "RED", ID: 2, GSD: self._ms_res, WV_MIN: 610, WV_MAX: 680},
            )

            nir = SpectralBand(
                eoreader_name=NIR,
                **{NAME: "NIR", ID: 1, GSD: self._ms_res, WV_MIN: 790, WV_MAX: 890},
            )

            swir1 = SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "SWIR_1",
                    ID: 4,
                    GSD: self._ms_res,
                    WV_MIN: 1580,
                    WV_MAX: 1750,
                },
            )
        else:
            # Create spectral bands
            pan = SpectralBand(
                eoreader_name=PAN,
                **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 490, WV_MAX: 690},
            )

            green = SpectralBand(
                eoreader_name=GREEN,
                **{NAME: "GREEN", ID: 3, GSD: self._ms_res, WV_MIN: 490, WV_MAX: 610},
            )

            red = SpectralBand(
                eoreader_name=RED,
                **{NAME: "RED", ID: 2, GSD: self._ms_res, WV_MIN: 610, WV_MAX: 680},
            )

            nir = SpectralBand(
                eoreader_name=NIR,
                **{NAME: "NIR", ID: 1, GSD: self._ms_res, WV_MIN: 780, WV_MAX: 890},
            )

            swir1 = SpectralBand(
                eoreader_name=SWIR_1,
                **{NAME: "SWIR_1", ID: 4, GSD: 20.0, WV_MIN: 1580, WV_MAX: 1750},
            )

        # Manage bands of the product
        if self.band_combi in [Spot4BandCombination.M, Spot5BandCombination.HM]:
            self.bands.map_bands({PAN: pan})
        elif self.band_combi in [
            Spot4BandCombination.X,
            Spot5BandCombination.X,
        ]:
            self.bands.map_bands(
                {
                    GREEN: green,
                    RED: red,
                    NIR: nir,
                    NARROW_NIR: nir,
                }
            )
        elif self.band_combi in [
            Spot4BandCombination.MX,
            Spot5BandCombination.HMX,
        ]:
            self.bands.map_bands(
                {
                    GREEN: green.update(gsd=self._pan_res),
                    RED: red.update(gsd=self._pan_res),
                    NIR: nir.update(gsd=self._pan_res),
                    NARROW_NIR: nir.update(gsd=self._pan_res),
                }
            )
        elif self.band_combi == Spot5BandCombination.T:
            self.bands.map_bands({PAN: pan.update(gsd=self._supermode_res)})
        elif self.band_combi == Spot5BandCombination.TX:
            self.bands.map_bands(
                {
                    GREEN: green.update(gsd=self._supermode_res),
                    RED: red.update(gsd=self._supermode_res),
                    NIR: nir.update(gsd=self._supermode_res),
                    NARROW_NIR: nir.update(gsd=self._supermode_res),
                }
            )
        elif self.band_combi in [
            Spot4BandCombination.I,
            Spot5BandCombination.J,
        ]:
            self.bands.map_bands(
                {
                    GREEN: green,
                    RED: red,
                    NIR: nir,
                    NARROW_NIR: nir,
                    SWIR_1: swir1,
                }
            )
        elif self.band_combi == Spot4BandCombination.MI:
            self.bands.map_bands(
                {
                    GREEN: green.update(gsd=self._pan_res),
                    RED: red.update(gsd=self._pan_res),
                    NIR: nir.update(gsd=self._pan_res),
                    NARROW_NIR: nir.update(gsd=self._pan_res),
                    SWIR_1: swir1.update(gsd=self._pan_res),
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
        crs_name = root.findtext(".//HORIZONTAL_CS_CODE")
        if not crs_name:
            raise InvalidProductError(
                "Cannot find the CRS name (from GEOGRAPHIC_CS_CODE or HORIZONTAL_CS_CODE) type in the metadata file"
            )

        return riocrs.CRS.from_string(crs_name)

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation"""
        if self.split_name[0] == "SP04":
            const = Constellation.SPOT4
        elif self.split_name[0] == "SP05":
            const = Constellation.SPOT5
        else:
            raise InvalidProductError(
                f"Invalid name: {self.name}, should start with SP04 or SP05."
            )

        return const

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Mission index
        mission_idx = int(root.findtext(".//MISSION_INDEX"))

        # Instrument
        instrument = "HIR" if self.constellation == Constellation.SPOT4 else "HRG"

        # Product type
        self._set_band_combi()  # Not set yet
        band_combi = f"{self.band_combi.name:_<4}"

        # Datetimes
        dt = self.get_datetime(as_datetime=True)
        start_dt = (dt - timedelta(seconds=4)).strftime(DATETIME_FMT)
        end_dt = (dt + timedelta(seconds=4)).strftime(DATETIME_FMT)

        # Unknown data
        digit = 3  # TODO: what's this ?
        suffix = "TOU_1234_eord"

        # Create name
        name = f"SP0{mission_idx}_{instrument}_{band_combi}_{digit}_{start_dt}_{end_dt}_{suffix}"

        return name

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
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open incidence and off-nadir angle
        az = None
        try:
            incidence_angle = abs(float(root.findtext(".//INCIDENCE_ANGLE")))
        except TypeError as exc:
            raise InvalidProductError(
                "INCIDENCE_ANGLE or VIEWING_ANGLE not found in metadata!"
            ) from exc
        if self.constellation == Constellation.SPOT5:
            try:
                off_nadir = abs(float(root.findtext(".//VIEWING_ANGLE")))
            except TypeError as exc:
                raise InvalidProductError(
                    "VIEWING_ANGLE not found in metadata!"
                ) from exc
        else:
            # See: https://earth.esa.int/eogateway/missions/spot-4
            orbit_height = 832000
            earth_radius = 6378137
            orbit_coeff = (earth_radius + orbit_height) / earth_radius
            off_nadir = np.rad2deg(
                np.arcsin(np.sin(np.deg2rad(90 - incidence_angle)) / orbit_coeff)
            )

        return az, off_nadir, incidence_angle

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
        if self._raw_units == RawUnits.REFL:
            # Compute the correct radiometry of the band
            if utils.is_uint16(band_arr):
                band_arr /= 10000.0
        elif self._raw_units == RawUnits.DN:
            # Convert DN into radiance
            band_arr = self._dn_to_toa_rad(band_arr, band)

            # Get the solar irradiance value of raw radiometric Band (in watt/m2/micron)
            root, _ = self.read_mtd()
            instrument_idx = int(root.findtext(".//INSTRUMENT_INDEX")) - 1

            if self.constellation == Constellation.SPOT4:
                e0 = _SPOT4_E0[band][instrument_idx]
            else:
                e0 = _SPOT5_E0[band][instrument_idx]

            # Convert radiance into reflectance
            band_arr = self._toa_rad_to_toa_refl(band_arr, band, e0=e0)

        else:
            LOGGER.warning(
                "The spectral properties of a SEAMLESS radiometric processed image "
                "cannot be retrieved since the initial images have undergone "
                "several radiometric adjustments for aesthetic rendering."
                "Returned as is."
            )

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
        mtd_from_path = "METADATA.DIM"
        mtd_archived = r"METADATA\.DIM"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _get_tile_path(self) -> AnyPathType:
        """
        Get the DIMAP filepath

        Returns:
            AnyPathType: DIMAP filepath
        """
        return self._get_path("IMAGERY", "TIF")

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        Args:
            dn_arr (xr.DataArray): DN array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Radiance array
        """
        band_mtd_str = _DIMAP_BAND_MTD[band]

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Convert DN to TOA radiance
        # <MEASURE_DESC>Raw radiometric counts (DN) to TOA Radiance (L). Formulae L=DN/GAIN+BIAS</MEASURE_DESC>
        try:
            rad_gain = None
            rad_bias = None
            for br in root.iterfind(".//Spectral_Band_Info"):
                if br.findtext("BAND_DESCRIPTION") == band_mtd_str:
                    rad_gain = float(br.findtext("PHYSICAL_GAIN"))
                    rad_bias = float(br.findtext("PHYSICAL_BIAS"))
                    break

            if rad_gain is None or rad_bias is None:
                raise TypeError

        except TypeError as exc:
            raise InvalidProductError(
                "PHYSICAL_GAIN and PHYSICAL_BIAS from Spectral_Band_Info not found in metadata!"
            ) from exc
        return dn_arr / rad_gain + rad_bias

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(
                    regex=r".*PREVIEW\.JPG"
                )
            else:
                quicklook_path = str(next(self.path.glob("*PREVIEW.JPG")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        # Get MTD XML file
        root, _ = self.read_mtd()
        return root.findtext(".//JOB_ID")

    def _get_condensed_name(self) -> str:
        """
        Get PlanetScope products condensed name ({date}_PLD_{product_type}_{band_combi}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{self.band_combi.name}"
