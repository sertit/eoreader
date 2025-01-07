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
"""Spectral Bands"""

import numpy as np

from eoreader.bands.band_names import SpectralBandNames
from eoreader.bands.bands import Band, BandMap
from eoreader.bands.mappings import EOREADER_TO_SPYNDEX_DICT
from eoreader.exceptions import InvalidTypeError
from eoreader.stac import CENTER_WV, FWHM, SOLAR_ILLUMINATION, WV_MAX, WV_MIN


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
        except TypeError as exc:
            raise InvalidTypeError from exc

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        repr_str = []

        if self.center_wavelength is not None:
            repr_str.append(
                f"\tCenter wavelength (nm): {self.center_wavelength * 1000}"
            )

        if self.full_width_half_max is not None:
            repr_str.append(f"\tBandwidth (nm): {self.full_width_half_max * 1000}")

        if self.solar_illumination is not None:
            repr_str.append(
                f"\tSolar Illumination (W/m2/micrometers): {self.solar_illumination}"
            )

        return repr_str


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
                band = SpectralBand(
                    eoreader_name=band_name,
                    name=band,
                    id=band,
                    spyndex_name=EOREADER_TO_SPYNDEX_DICT.get(band_name),
                )
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
