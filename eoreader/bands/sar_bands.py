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
""" SAR Bands """
from eoreader.bands.bands import Band, BandMap, BandNames
from eoreader.exceptions import InvalidTypeError


class SarBand(Band):
    """
    SAR Band object.
    Based on STAC band object.
    See `here <https://github.com/stac-extensions/eo/#band-object>`_ for more information, without useless information.
    """

    def __init__(self, eoreader_name, **kwargs):
        # Initialization from the super class
        super().__init__(eoreader_name, **kwargs)

        # Set names
        try:
            self.eoreader_name = SarBandNames.convert_from(eoreader_name)[0]
        except TypeError:
            raise InvalidTypeError

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """

        return []


# too many ancestors
# pylint: disable=R0901
class SarBandMap(BandMap):
    """SAR band map class"""

    def __init__(self) -> None:
        super().__init__({band_name: None for band_name in SarBandNames})

    def map_bands(self, band_map: dict) -> None:
        """
        Mapping band names to specific satellite band numbers, as strings.

        .. code-block:: python

            >>> sb = SarBandMap()
            >>> sb.map_bands({
                    VV: 1,
                })

        Args:
            band_map (dict): Band mapping as {SarBandNames: Band number for loading band}
        """
        for band_name, band in band_map.items():
            if not isinstance(band, SarBand):
                band = SarBand(eoreader_name=band_name, name=band, id=band)
            if band_name not in self._band_map or not isinstance(
                band_name, SarBandNames
            ):
                raise InvalidTypeError(f"{band_name} should be a SarBandNames object")

            # Set number
            self._band_map[band_name] = band


class SarBandNames(BandNames):
    """SAR Band names"""

    VV = "VV"
    """ Vertical Transmit-Vertical Receive Polarisation """

    VV_DSPK = "VV_DSPK"
    """ Vertical Transmit-Vertical Receive Polarisation (Despeckled) """

    HH = "HH"
    """ Horizontal Transmit-Horizontal Receive Polarisation """

    HH_DSPK = "HH_DSPK"
    """ Horizontal Transmit-Horizontal Receive Polarisation (Despeckled) """

    VH = "VH"
    """ Vertical Transmit-Horizontal Receive Polarisation """

    VH_DSPK = "VH_DSPK"
    """ Vertical Transmit-Horizontal Receive Polarisation (Despeckled) """

    HV = "HV"
    """ Horizontal Transmit-Vertical Receive Polarisation """

    HV_DSPK = "HV_DSPK"
    """ Horizontal Transmit-Vertical Receive Polarisation (Despeckled) """

    RH = "RH"
    """ Compact polarization: right circular transmit, horizontal receive """

    RH_DSPK = "RH_DSPK"
    """ Compact polarization: right circular transmit, horizontal receive """

    RV = "RV"
    """ Compact polarization: right circular transmit, vertical receive (Despeckled) """

    RV_DSPK = "RV_DSPK"
    """ Compact polarization: right circular transmit, horizontal receive (Despeckled) """

    @classmethod
    def corresponding_despeckle(cls, band: "SarBandNames"):
        """
        Corresponding despeckled band.

        .. code-block:: python

            >>> SarBandNames.corresponding_despeckle(SarBandNames.VV)
            <SarBandNames.VV_DSPK: 'VV_DSPK'>
            >>> SarBandNames.corresponding_despeckle(SarBandNames.VV_DSPK)
            <SarBandNames.VV_DSPK: 'VV_DSPK'>

        Args:
            band (SarBandNames): Noisy (speckle) band

        Returns:
            SarBandNames: Despeckled band
        """
        if cls.is_despeckle(band):
            dspk = band
        else:
            dspk = cls.from_value(f"{band.name}_DSPK")

        return dspk

    @classmethod
    def corresponding_speckle(cls, band: "SarBandNames"):
        """
        Corresponding speckle (noisy) band.

        .. code-block:: python

            >>> SarBandNames.corresponding_speckle(SarBandNames.VV)
            <SarBandNames.VV: 'VV'>
            >>> SarBandNames.corresponding_speckle(SarBandNames.VV_DSPK)
            <SarBandNames.VV: 'VV'>

        Args:
            band (SarBandNames): Noisy (speckle) band

        Returns:
            SarBandNames: Despeckled band
        """
        return cls.from_value(f"{band.name[:2]}")

    @classmethod
    def is_despeckle(cls, band: "SarBandNames"):
        """
        Returns True if the band corresponds to a despeckled one.

        .. code-block:: python

            >>> SarBandNames.is_despeckle(SarBandNames.VV)
            False
            >>> SarBandNames.is_despeckle(SarBandNames.VV_DSPK)
            True

        Args:
            band (SarBandNames): Band to test

        Returns:
            SarBandNames: Despeckled band
        """
        return "DSPK" in band.name

    @classmethod
    def speckle_list(cls):
        return [band for band in cls if not cls.is_despeckle(band)]


VV = SarBandNames.VV
VV_DSPK = SarBandNames.VV_DSPK
HH = SarBandNames.HH
HH_DSPK = SarBandNames.HH_DSPK
VH = SarBandNames.VH
VH_DSPK = SarBandNames.VH_DSPK
HV = SarBandNames.HV
HV_DSPK = SarBandNames.HV_DSPK
RH = SarBandNames.RH
RH_DSPK = SarBandNames.RH_DSPK
RV = SarBandNames.RV
RV_DSPK = SarBandNames.RV_DSPK


def is_sar_band(band) -> bool:
    """
    Returns True if is a SAR band (from :code:`SarBandNames`)

    .. code-block:: python

        >>> from eoreader.bands import *
        >>> is_sar_band(NDVI)
        False
        >>> is_sar_band(HH)
        True
        >>> is_sar_band(GREEN)
        False
        >>> is_sar_band(SLOPE)
        False
        >>> is_sar_band(CLOUDS)
        False

    Args:
        band (Any): Anything that could be a SAR band

    Returns:
        bool: True if the band asked is a SAR band

    """
    try:
        is_valid = SarBandNames(band)
    except ValueError:
        is_valid = False
    return is_valid
