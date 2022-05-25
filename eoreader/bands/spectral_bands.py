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
""" Spectral Bands """
import numpy as np

from eoreader.bands.bands import Band, BandMap, BandNames
from eoreader.exceptions import InvalidTypeError
from eoreader.stac import (
    CENTER_WV,
    FWHM,
    SOLAR_ILLUMINATION,
    WV_MAX,
    WV_MIN,
    StacCommonNames,
)


class SpectralBand(Band):
    """
    Spectral Band object.
    Based on STAC band object.
    See `here <https://github.com/stac-extensions/eo/#band-object>`_ for more information.
    """

    @staticmethod
    def _from_nm_microm(wavelength: float, thresh=100) -> float:
        """
        Convert wavelength in nanometers (if > 100) to micrometers

        Args:
            wavelength (float):  Wavelength in nanometers

        Returns:
            float: Wavelength in micrometers
        """
        if wavelength and wavelength > thresh:
            wavelength = np.round(wavelength / 1000.0, 6)
        return wavelength

    def __init__(self, eoreader_name, **kwargs):
        self.center_wavelength = None
        """
        STAC :code:`center_wavelength`.
        The center wavelength of the band, in micrometers (μm).
        """

        self.full_width_half_max = None
        """
        STAC :code:`full_width_half_max`.
        Full width at half maximum (FWHM). The width of the band, as measured at half the maximum transmission, in micrometers (μm).
        """

        if WV_MAX in kwargs and WV_MIN in kwargs:
            wv_max = self._from_nm_microm(kwargs[WV_MAX])
            wv_min = self._from_nm_microm(kwargs[WV_MIN])

            assert wv_max > wv_min
            self.full_width_half_max = np.round(wv_max - wv_min, 6)
            self.center_wavelength = np.round(
                wv_min + self.full_width_half_max / 2.0, 6
            )
        else:
            self.center_wavelength = self._from_nm_microm(kwargs.get(CENTER_WV))
            self.full_width_half_max = self._from_nm_microm(kwargs.get(FWHM), thresh=1)

        self.solar_illumination = kwargs.get(SOLAR_ILLUMINATION)
        """
        STAC :code:`solar_illumination`.
        The solar illumination of the band, as measured at half the maximum transmission, in W/m2/micrometers.
        """

        # Initialization from the super class
        super().__init__(eoreader_name, **kwargs)

        # Set names
        try:
            self.eoreader_name = SpectralBandNames.convert_from(eoreader_name)[0]
            self.common_name = SpectralBandNames.eoreader_to_stac(self.eoreader_name)
        except TypeError:
            raise InvalidTypeError

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        repr = []

        if self.center_wavelength is not None:
            repr.append(f"\tCenter wavelength (nm): {self.center_wavelength * 1000}")

        if self.full_width_half_max is not None:
            repr.append(f"\tBandwidth (nm): {self.full_width_half_max * 1000}")

        if self.solar_illumination is not None:
            repr.append(
                f"\tSolar Illumination (W/m2/micrometers): {self.solar_illumination}"
            )

        return repr


# too many ancestors
# pylint: disable=R0901
class SpectralBandMap(BandMap):
    """Spectral band map class"""

    def __init__(self) -> None:
        super().__init__({band_name: None for band_name in SpectralBandNames})

    def map_bands(self, band_map: dict) -> None:
        """
        Mapping band names to specific satellite band numbers, as strings.

        .. code-block:: python

            >>> ob = SpectralBandMap()
            >>> ob.map_bands({
                    CA: '01',
                    BLUE: '02',
                    GREEN: '03',
                    RED: '04',
                    VRE_1: '05',
                    VRE_2: '06',
                    VRE_3: '07',
                    NIR: '08',
                    WV: '09',
                    SWIR_1: '11',
                    SWIR_2: '12'
                })

        Args:
            band_map (dict): Band mapping as {SpectralBandNames: Band number for loading band}
        """
        for band_name, band in band_map.items():
            if not isinstance(band, SpectralBand):
                band = SpectralBand(eoreader_name=band_name, name=band, id=band)
            if band_name not in self._band_map or not isinstance(
                band_name, SpectralBandNames
            ):
                raise InvalidTypeError(
                    f"{band_name} should be a SpectralBandNames object"
                )

            # Set number
            self._band_map[band_name] = band

    def __repr__(self):
        bands = [band for band in self._band_map.values() if band is not None]
        try:
            bands.sort(key=lambda x: int(x.id))
        except ValueError:
            bands.sort(key=lambda x: x.id)

        return "\n".join([band.__repr__() for band in bands])


class SpectralBandNames(BandNames):
    """
    This class aims to regroup equivalent bands under the same nomenclature.
    Each products will set their band number in regard to their corresponding name.

    **Note**: The mapping is based on Sentinel-2 spectral bands.

    More information can be retrieved here:

    - `Overall comparison <http://blog.imagico.de/wp-content/uploads/2016/11/sat_spectra_full4a.png>`_
    - L8/S2:
        - `Resource 1 <https://reader.elsevier.com/reader/sd/pii/S0034425718301883>`_
        - `Resource 2 <https://landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png>`_
    - `L4/L5, MSS-TM <https://landsat.gsfc.nasa.gov/the-multispectral-scanner-system/>`_
    - `All Landsats <https://landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png>`_
    - `S2 <https://discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png>`_
    - `S3 OLCI <https://discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png>`_
    - `S3 SLSTR <https://discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png>`_
    - `Index consistency <https://www.indexdatabase.de/>`_

    This classification allows index computation and algorithms to run without knowing the band nb of every satellite.
    If None, then the band does not exist for the satellite.
    """

    CA = "COASTAL_AEROSOL"
    """Coastal aerosol"""

    BLUE = "BLUE"
    """Blue"""

    GREEN = "GREEN"
    """Green"""

    YELLOW = "YELLOW"
    """Yellow"""

    RED = "RED"
    """Red"""

    VRE_1 = "VEGETATION_RED_EDGE_1"
    """Vegetation red edge, Band 1"""

    VRE_2 = "VEGETATION_RED_EDGE_2"
    """Vegetation red edge, Band 2"""

    VRE_3 = "VEGETATION_RED_EDGE_3"
    """Vegetation red edge, Band 3"""

    NIR = "NIR"
    """NIR"""

    NARROW_NIR = "NARROW_NIR"
    """Narrow NIR"""

    WV = "WATER_VAPOUR"
    """Water vapour"""

    SWIR_CIRRUS = "CIRRUS"
    """Cirrus"""

    SWIR_1 = "SWIR_1"
    """SWIR, Band 1"""

    SWIR_2 = "SWIR_2"
    """SWIR, Band 2"""

    TIR_1 = "THERMAL_IR_1"
    """Thermal IR, Band 1"""

    TIR_2 = "THERMAL_IR_2"
    """Thermal IR, Band 2"""

    PAN = "PANCHROMATIC"
    """Panchromatic"""

    # SLSTR additional band names
    S7 = "S7"
    """
    S7
    """

    F1 = "F1"
    """
    F1
    """

    F2 = "F2"
    """
    F2
    """

    # S3-OLCI additional band names
    Oa01 = "Oa01"
    """
    Oa01
    """

    Oa02 = "Oa02"
    """
    Oa02
    """

    Oa09 = "Oa09"
    """
    Oa09
    """

    Oa10 = "Oa10"
    """
    Oa10
    """

    Oa13 = "Oa13"
    """
    Oa13
    """

    Oa14 = "Oa14"
    """
    Oa14
    """

    Oa15 = "Oa15"
    """
    Oa15
    """

    Oa18 = "Oa18"
    """
    Oa18
    """

    Oa19 = "Oa19"
    """
    Oa01
    """

    Oa21 = "Oa21"
    """
    Oa01
    """

    # -- PlanetScope PSB.SD instrument additional band --
    GREEN1 = "GREEN_I"
    """
    GREEN I
    """

    @classmethod
    def stac_to_eoreader(cls, common_name: str, name: str) -> "SpectralBandNames":
        """
        Convert STAC common names or name to EOReader bands

        Args:
            common_name (str): STAC common name
            name (str): STAC name

        Returns:
            SpectralBandNames: EOReader name
        """
        # Try directly from raw name (especially for Sentinel-3 raw bands etc)
        try:
            return cls.from_value(name)
        except ValueError:
            eoreader_name = None

        stac_common_name = StacCommonNames.from_value(common_name)

        for key, val in _EOREADER_STAC_MAP.items():
            if val == stac_common_name:
                eoreader_name = key
                break

        return eoreader_name

    @classmethod
    def eoreader_to_stac(cls, eoreader_name: "SpectralBandNames") -> str:
        """
        Convert STAC common names or name to EOReader bands

        Args:
            eoreader_name (SpectralBandNames): EOReader name

        Returns:
            SpectralBandNames: EOReader name
        """
        return _EOREADER_STAC_MAP.get(eoreader_name, "")


# -- SPECTRAL BANDS --
CA = SpectralBandNames.CA  # Coastal aerosol
BLUE = SpectralBandNames.BLUE
GREEN = SpectralBandNames.GREEN
YELLOW = SpectralBandNames.YELLOW
RED = SpectralBandNames.RED
VRE_1 = SpectralBandNames.VRE_1
VRE_2 = SpectralBandNames.VRE_2
VRE_3 = SpectralBandNames.VRE_3
NIR = SpectralBandNames.NIR
NARROW_NIR = SpectralBandNames.NARROW_NIR
WV = SpectralBandNames.WV  # Water vapour
SWIR_CIRRUS = SpectralBandNames.SWIR_CIRRUS  # Spectral band based on cirrus
SWIR_1 = SpectralBandNames.SWIR_1
SWIR_2 = SpectralBandNames.SWIR_2
TIR_1 = SpectralBandNames.TIR_1
TIR_2 = SpectralBandNames.TIR_2
PAN = SpectralBandNames.PAN

# -- S3-SLSTR Additional bands --
S7 = SpectralBandNames.S7
F1 = SpectralBandNames.F1
F2 = SpectralBandNames.F2

# -- S3-OCLI Additional bands --
Oa01 = SpectralBandNames.Oa01
Oa02 = SpectralBandNames.Oa02
Oa09 = SpectralBandNames.Oa09
Oa10 = SpectralBandNames.Oa10
Oa13 = SpectralBandNames.Oa13
Oa14 = SpectralBandNames.Oa14
Oa15 = SpectralBandNames.Oa15
Oa18 = SpectralBandNames.Oa18
Oa19 = SpectralBandNames.Oa19
Oa21 = SpectralBandNames.Oa21

# -- PlanetScope PSB.SD instrument additional band --
GREEN1 = SpectralBandNames.GREEN1

_EOREADER_STAC_MAP = {
    CA: StacCommonNames.COASTAL,
    BLUE: StacCommonNames.BLUE,
    GREEN: StacCommonNames.GREEN,
    RED: StacCommonNames.RED,
    YELLOW: StacCommonNames.YELLOW,
    PAN: StacCommonNames.PAN,
    VRE_1: StacCommonNames.RE,
    VRE_2: StacCommonNames.RE,
    VRE_3: StacCommonNames.RE,
    NIR: StacCommonNames.NIR,
    NARROW_NIR: StacCommonNames.NIR08,
    WV: StacCommonNames.NIR09,
    SWIR_CIRRUS: StacCommonNames.CIRRUS,
    SWIR_1: StacCommonNames.SWIR16,
    SWIR_2: StacCommonNames.SWIR22,
    TIR_1: StacCommonNames.LWIR11,
    TIR_2: StacCommonNames.LWIR12,
}


def is_spectral_band(band) -> bool:
    """
    Returns True if is an spectral band (from :code:`SpectralBandNames`)

    .. code-block:: python

        >>> from eoreader.bands import *
        >>> is_spectral_band(NDVI)
        False
        >>> is_spectral_band(HH)
        False
        >>> is_spectral_band(GREEN)
        True
        >>> is_spectral_band(SLOPE)
        False
        >>> is_spectral_band(CLOUDS)
        False

    Args:
        band (Any): Anything that could be an optical band

    Returns:
        bool: True if the band asked is an optical band

    """
    try:
        is_valid = SpectralBandNames(band)
    except ValueError:
        is_valid = False
    return is_valid
