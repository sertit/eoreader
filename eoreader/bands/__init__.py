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
from eoreader.bands.bands import Band, BandMap, BandNames

__all__ = ["Band", "BandMap", "BandNames"]

from eoreader.bands.cloud_bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    RAW_CLOUDS,
    SHADOWS,
    CloudsBandNames,
    is_clouds,
)

__all__ += [
    "CloudsBandNames",
    "RAW_CLOUDS",
    "CLOUDS",
    "SHADOWS",
    "CIRRUS",
    "ALL_CLOUDS",
    "is_clouds",
]

from eoreader.bands.dem_bands import DEM, HILLSHADE, SLOPE, DemBandNames, is_dem

__all__ += ["DemBandNames", "DEM", "SLOPE", "HILLSHADE", "is_dem"]

from eoreader.bands.indices import (
    AFRI_1_6,
    AFRI_2_1,
    BAI,
    BAIS2,
    BSI,
    CI1,
    CI2,
    CIG,
    DSWI,
    EVI,
    GLI,
    GNDVI,
    GRI,
    GVMI,
    MNDWI,
    NBR,
    NDGRI,
    NDMI,
    NDMI21,
    NDRE2,
    NDRE3,
    NDVI,
    NDWI,
    OSAVI,
    PANI,
    RDI,
    RGI,
    RI,
    SAVI,
    SBI,
    SCI,
    SI,
    SRSWIR,
    TCBRI,
    TCGRE,
    TCWET,
    VARI,
    WI,
    WV_BI,
    WV_SI,
    WV_VI,
    WV_WI,
    AWEInsh,
    AWEIsh,
    get_all_index_names,
    get_all_indices,
    get_all_needed_bands,
    get_needed_bands,
    is_index,
)

__all__ += [
    "get_all_index_names",
    "get_all_indices",
    "get_needed_bands",
    "get_all_needed_bands",
    "is_index",
    "AFRI_1_6",
    "AFRI_2_1",
    "AWEInsh",
    "AWEIsh",
    "BAI",
    "BAIS2",
    "BSI",
    "CI1",
    "CI2",
    "CIG",
    "DSWI",
    "EVI",
    "GLI",
    "GNDVI",
    "GRI",
    "GVMI",
    "MNDWI",
    "NBR",
    "NDGRI",
    "NDMI",
    "NDMI21",
    "NDRE2",
    "NDRE3",
    "NDVI",
    "NDWI",
    "OSAVI",
    "PANI",
    "RDI",
    "RGI",
    "RI",
    "SAVI",
    "SBI",
    "SCI",
    "SI",
    "SRSWIR",
    "TCBRI",
    "TCGRE",
    "TCWET",
    "VARI",
    "WI",
    "WV_BI",
    "WV_SI",
    "WV_VI",
    "WV_WI",
]

from eoreader.bands.sar_bands import (
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
    SarBand,
    SarBandMap,
    SarBandNames,
    is_sar_band,
)

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
    "is_sar_band",
]

from eoreader.bands.spectral_bands import (
    BLUE,
    CA,
    F1,
    F2,
    GREEN,
    GREEN1,
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
    SpectralBand,
    SpectralBandMap,
    SpectralBandNames,
    is_spectral_band,
)

__all__ += [
    "SpectralBand",
    "SpectralBandMap",
    "SpectralBandNames",
    "CA",
    "BLUE",
    "GREEN",
    "GREEN1",
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
    "is_spectral_band",
]

__all__ += ["is_sat_band", "to_band", "to_str"]

from eoreader.exceptions import InvalidTypeError as _ite


def is_sat_band(band) -> bool:
    """
    Returns True if is a band (from both :code:`SarBandNames` or :code:`SpectralBandNames`)

    .. code-block:: python

        >>> from eoreader.bands import *
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

    Args:
        band (Any): Anything that could be a band

    Returns:
        bool: True if the band asked is a band

    """
    return is_sar_band(band) or is_spectral_band(band)


def to_band(to_convert: list) -> list:
    """
    Convert a string (or real value) to any alias, band or index.

    You can pass the name or the value of the bands.

    .. code-block:: python

        >>> to_band(["NDVI", "GREEN", RED, "VH_DSPK", "SLOPE", DEM, "CLOUDS", CLOUDS])
        [<function NDVI at 0x00000154DDB12488>,
        <SpectralBandNames.GREEN: 'GREEN'>,
        <SpectralBandNames.RED: 'RED'>,
        <SarBandNames.VH_DSPK: 'VH_DSPK'>,
        <DemBandNames.SLOPE: 'SLOPE'>,
        <DemBandNames.DEM: 'DEM'>,
        <ClassifBandNames.CLOUDS: 'CLOUDS'>,
        <ClassifBandNames.CLOUDS: 'CLOUDS'>]

    Args:
        to_convert (list): Values to convert into band objects

    Returns:
        list: converted values

    """
    if not isinstance(to_convert, list):
        to_convert = [to_convert]

    bands = []
    for tc in to_convert:
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
            bands.append(band_or_idx)
        else:
            raise _ite(f"Unknown band or index: {tc}")

    return bands


def to_str(to_convert: list) -> list:
    """
    Convert a string (or real value) to any alias, band or index.

    You can pass the name or the value of the bands.

    .. code-block:: python

        >>> to_str(["NDVI", "GREEN", RED, "VH_DSPK", "SLOPE", DEM, "CLOUDS", CLOUDS])
        ['NDVI', 'GREEN', 'RED', 'VH_DSPK', 'SLOPE', 'DEM', 'CLOUDS', 'CLOUDS']

    Args:
        to_convert (list): Values to convert into str

    Returns:
        list: str bands
    """
    if not isinstance(to_convert, list):
        to_convert = [to_convert]

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
