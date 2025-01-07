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
Band module containing:

- wrapper for SAR and optical bands
- Index definitions
- Aliases for all these useful variables

To use it, simply type:

.. code-block:: python

    >>> from eoreader.bands import *
    >>> GREEN
    <SpectralBandNames.GREEN: 'GREEN'>
    >>> HH
    <SarBandNames.HH: 'HH'>
    >>> NDVI
    <function NDVI at 0x00000261F6FFA950>
"""

# flake8: noqa
from eoreader.bands.bands import Band, BandMap

__all__ = ["Band", "BandMap"]

from eoreader.bands.band_names import BandNames

__all__ += ["BandNames"]

from eoreader.bands.band_names import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    RAW_CLOUDS,
    SHADOWS,
    CloudsBandNames,
)

__all__ += [
    "CloudsBandNames",
    "RAW_CLOUDS",
    "CLOUDS",
    "SHADOWS",
    "CIRRUS",
    "ALL_CLOUDS",
]

from eoreader.bands.band_names import DEM, HILLSHADE, SLOPE, DemBandNames

__all__ += ["DemBandNames", "DEM", "SLOPE", "HILLSHADE"]

from eoreader.bands.indices import (
    get_all_index_names,
    get_all_needed_bands,
    get_needed_bands,
    is_index,
)

__all__ += [
    "get_all_index_names",
    "get_needed_bands",
    "get_all_needed_bands",
    "is_index",
]

# Spyndex indices
__all__ += get_all_index_names()
from eoreader.bands.band_names import (
    HH,
    HH_DSPK,
    HV,
    HV_DSPK,
    RH,
    RH_DSPK,
    RV,
    RV_DSPK,
    VH,
    VH_DSPK,
    VV,
    VV_DSPK,
    SarBandNames,
)
from eoreader.bands.indices import *
from eoreader.bands.sar_bands import SarBand, SarBandMap

__all__ += [
    "SarBand",
    "SarBandMap",
    "SarBandNames",
    "VV",
    "VV_DSPK",
    "HH",
    "HH_DSPK",
    "VH",
    "VH_DSPK",
    "HV",
    "HV_DSPK",
    "RH",
    "RH_DSPK",
    "RV",
    "RV_DSPK",
]

from eoreader.bands.band_names import GREEN1  # To be deprecated
from eoreader.bands.band_names import (
    BLUE,
    CA,
    F1,
    F2,
    GREEN,
    GREEN_1,
    NARROW_NIR,
    NIR,
    PAN,
    RED,
    S7,
    SWIR_1,
    SWIR_2,
    SWIR_CIRRUS,
    TIR_1,
    TIR_2,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    YELLOW,
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
    SpectralBandNames,
)
from eoreader.bands.spectral_bands import SpectralBand, SpectralBandMap

__all__ += [
    "SpectralBand",
    "SpectralBandMap",
    "SpectralBandNames",
    "CA",
    "BLUE",
    "GREEN",
    "GREEN_1",
    "GREEN1",  # To be deprecated
    "YELLOW",
    "RED",
    "VRE_1",
    "VRE_2",
    "VRE_3",
    "NIR",
    "NARROW_NIR",
    "WV",
    "SWIR_CIRRUS",
    "SWIR_1",
    "SWIR_2",
    "TIR_1",
    "TIR_2",
    "PAN",
    "S7",
    "F1",
    "F2",
    "Oa01",
    "Oa02",
    "Oa09",
    "Oa10",
    "Oa13",
    "Oa14",
    "Oa15",
    "Oa18",
    "Oa19",
    "Oa21",
]

from eoreader.bands.mappings import (
    EOREADER_STAC_MAP,
    EOREADER_TO_SPYNDEX_DICT,
    SPYNDEX_TO_EOREADER_DICT,
)

__all__ += ["EOREADER_TO_SPYNDEX_DICT", "SPYNDEX_TO_EOREADER_DICT", "EOREADER_STAC_MAP"]

__all__ += [
    "is_spectral_band",
    "is_thermal_band",
    "is_sar_band",
    "is_sat_band",
    "is_clouds",
    "is_dem",
    "to_band",
    "to_str",
]

from typing import Union

from eoreader.exceptions import InvalidTypeError as _ite

BandType = Union[
    str, SpectralBandNames, SarBandNames, CloudsBandNames, DemBandNames, BandNames
]
""" EOReader band type, either a string, a BandName or its children: Spectral, SAR, DEM or Cloud band names """

BandsType = Union[list, BandType]
""" EOReader bands type, either a list or a BandType. """


def is_spectral_band(band: BandType) -> bool:
    """
    Returns True if is a spectral band (from :code:`SpectralBandNames`)

    Args:
        band (BandType): Anything that could be an optical band

    Returns:
        bool: True if the band asked is an optical band

    Examples:

        >>> from eoreader.bands import NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
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

    """
    is_valid = True
    try:
        SpectralBandNames(band)
    except ValueError:
        is_valid = False
    return is_valid


def is_thermal_band(band: BandType) -> bool:
    """
    Returns True if is a spectral and a thermal band (from :code:`SpectralBandNames`)

    Args:
        band (BandType): Anything that could be an optical band

    Returns:
        bool: True if the band asked is an optical band

    Examples:

        >>> from eoreader.bands import SWIR_1, NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
        >>> is_thermal_band(SWIR_1)
        True
        >>> is_thermal_band(NDVI)
        False
        >>> is_thermal_band(HH)
        False
        >>> is_thermal_band(GREEN)
        False
        >>> is_thermal_band(SLOPE)
        False
        >>> is_thermal_band(CLOUDS)
        False

    """
    return is_spectral_band(band) and band in [TIR_1, TIR_2, F1, F2, S7]


def is_sar_band(band: BandType) -> bool:
    """
    Returns True if is a SAR band (from :code:`SarBandNames`)

    Args:
        band (BandType): Anything that could be a SAR band

    Returns:
        bool: True if the band asked is a SAR band

    Examples:

        >>> from eoreader.bands import NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
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

    """
    is_valid = True
    try:
        SarBandNames(band)
    except ValueError:
        is_valid = False
    return is_valid


def is_sat_band(band: BandType) -> bool:
    """
    Returns True if is a satellite band (from both :code:`SarBandNames` or :code:`SpectralBandNames`)

    Args:
        band (BandType): Anything that could be a band

    Returns:
        bool: True if the band asked is a satellite band (Spectral or SAR)

    Examples:

        >>> from eoreader.bands import NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
        >>> is_sat_band(NDVI)
        False
        >>> is_sat_band(HH)
        True
        >>> is_sat_band(GREEN)
        True
        >>> is_sat_band(SLOPE)
        False
        >>> is_sat_band(CLOUDS)
        False

    """
    return is_sar_band(band) or is_spectral_band(band)


def is_clouds(clouds: BandType) -> bool:
    """
    Returns True if is a cloud band (from :code:`CloudBandNames`)

    Args:
        clouds (BandType): Anything that could be a cloud band

    Returns:
        bool: True if the band asked is a cloud band

    Examples:

        >>> from eoreader.bands import NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
        >>> is_clouds(NDVI)
        False
        >>> is_clouds(HH)
        False
        >>> is_clouds(GREEN)
        False
        >>> is_clouds(SLOPE)
        False
        >>> is_clouds(CLOUDS)
        True

    """
    is_valid = True
    try:
        CloudsBandNames(clouds)
    except ValueError:
        is_valid = False
    return is_valid


def is_dem(dem: BandType) -> bool:
    """
    Returns True if is a DEM band (from :code:`DemBandNames`)

    Args:
        clouds (BandType): Anything that could be a DEM band

    Returns:
        bool: True if the band asked is a DEM band

    Examples:

        >>> from eoreader.bands import NDVI, HH, GREEN, SLOPE, CLOUDS
        >>>
        >>> is_dem(NDVI)
        False
        >>> is_dem(HH)
        False
        >>> is_dem(GREEN)
        False
        >>> is_dem(SLOPE)
        True
        >>> is_dem(CLOUDS)
        False
    """
    is_valid = True
    try:
        DemBandNames(dem)
    except ValueError:
        is_valid = False
    return is_valid


def to_band(
    to_convert: Union[list[BandType], BandType], as_list: bool = True
) -> Union[list, BandNames]:
    """
    Convert a string (or real value) to any alias, band or index.

    You can pass the name or the value of the bands.

    Args:
        to_convert (Union[list, BandNames, str]): Values to convert into band objects
        as_list (bool): Return the result as a list

    Returns:
        list: Bands as BandNames

    Examples:

        >>> from eoreader.bands import RED, DEM, CLOUDS
        >>>
        >>> to_band(["NDVI", "GREEN", RED, "VH_DSPK", "SLOPE", DEM, "CLOUDS", CLOUDS])
        [<function NDVI at 0x00000154DDB12488>,
        <SpectralBandNames.GREEN: 'GREEN'>,
        <SpectralBandNames.RED: 'RED'>,
        <SarBandNames.VH_DSPK: 'VH_DSPK'>,
        <DemBandNames.SLOPE: 'SLOPE'>,
        <DemBandNames.DEM: 'DEM'>,
        <ClassifBandNames.CLOUDS: 'CLOUDS'>,
        <ClassifBandNames.CLOUDS: 'CLOUDS'>]

    """
    from sertit import types

    def convert_to_band(tc) -> BandNames:
        band_or_idx = None
        # Try legit types
        if isinstance(tc, str):
            # Try index
            if tc in get_all_index_names():
                from eoreader.bands import indices

                band_or_idx = getattr(indices, tc)
            else:
                try:
                    band_or_idx = SarBandNames.convert_from(tc)[0]
                except TypeError:
                    try:
                        band_or_idx = SpectralBandNames.convert_from(tc)[0]
                    except TypeError:
                        try:
                            band_or_idx = DemBandNames.convert_from(tc)[0]
                        except TypeError:
                            try:
                                band_or_idx = CloudsBandNames.convert_from(tc)[0]
                            except TypeError:
                                pass

        elif is_index(tc) or is_sat_band(tc) or is_dem(tc) or is_clouds(tc):
            band_or_idx = tc

        # Store it
        if band_or_idx:
            return band_or_idx
        else:
            if tc == "GREEN1":
                from sertit import logs

                logs.deprecation_warning(
                    "`GREEN1` is deprecated in favor of `GREEN_1`. `GREEN1` will be removed in a future release."
                )
                return GREEN1
            else:
                raise _ite(f"Unknown band or index: {tc}")

    if as_list:
        band_list = []
        to_convert = types.make_iterable(to_convert)

        for tc in to_convert:
            tc_band = convert_to_band(tc=tc)
            band_list.append(tc_band)
        return band_list
    else:
        if types.is_iterable(to_convert):
            raise _ite(f"Set as_list=True(default) for list arguments")
        return convert_to_band(to_convert)


def to_str(
    to_convert: Union[list[BandType], BandType], as_list: bool = True
) -> Union[list, str]:
    """
    Convert a string (or real value) to any alias, band or index.

    You can pass the name or the value of the bands.

    Args:
        to_convert (Union[list, BandNames, str]): Values to convert into str
        as_list (bool): Return the result as a list

    Returns:
        list: Bands as strings

    Examples:

        >>> from eoreader.bands import RED, DEM, CLOUDS
        >>>
        >>> to_str(["NDVI", "GREEN", RED, "VH_DSPK", "SLOPE", DEM, "CLOUDS", CLOUDS])
        ['NDVI', 'GREEN', 'RED', 'VH_DSPK', 'SLOPE', 'DEM', 'CLOUDS', 'CLOUDS']
    """
    from sertit import types

    if as_list:
        to_convert = types.make_iterable(to_convert)

        bands_str = []
        for tc in to_convert:
            if isinstance(tc, str):
                band_str = tc
            else:
                try:
                    band_str = tc.name
                except AttributeError:
                    band_str = tc.__name__

            bands_str.append(band_str)
        return bands_str
    else:
        if types.is_iterable(to_convert):
            raise _ite(f"Set as_list=True(default) for list arguments")
        try:
            band_str = tc.name
        except AttributeError:
            band_str = tc.__name__
        return band_str
