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
Set of usual spectral indices.

**Note**: This is easier to manage indices as raw functions in a file rather than stored in a class
"""

import contextlib
import inspect
import logging
import re
import sys
from functools import wraps
from typing import Callable

import numpy as np
import spyndex
import xarray as xr
from sertit import rasters

from eoreader import EOREADER_NAME
from eoreader.bands.band_names import (
    BLUE,
    CA,
    GREEN,
    NIR,
    RED,
    SWIR_1,
    SWIR_2,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    SpectralBandNames,
)
from eoreader.bands.mappings import EOREADER_TO_SPYNDEX_DICT, SPYNDEX_TO_EOREADER_DICT

LOGGER = logging.getLogger(EOREADER_NAME)
np.seterr(divide="ignore", invalid="ignore")

DEPRECATED_SPECTRAL_INDICES = {
    "AFRI_1_6": "AFRI1600",
    "AFRI_2_1": "AFRI2100",
    "BSI": "BI",
    "NDGRI": "NGRDI",
    "NDRE1": "NDREI",
    "RGI": "RGRI",
    "WV_BI": "NHFD",
    "WI": "WI2015",
    "RDI": "DSI",
    "DSWI": "DSWI5",
    "GRI": "DSWI4",
    "WV_SI": "NDSIWV",
    "PANI": "BITM",
}

# Using NIR instead of NARROW_NIR to follow ASI approach
# (see: https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/27)
# Goal with this dict: to have as many indices as possible implemented in ASI
EOREADER_DERIVATIVES = {
    "NDRE2": ["NDREI", {"N": NIR, "RE1": VRE_2}],
    "NDRE3": ["NDREI", {"N": NIR, "RE1": VRE_3}],
    "NDMI21": ["NDMI", {"N": NIR, "S1": SWIR_2}],
    "NDMI2100": ["NDMI", {"N": NIR, "S1": SWIR_2}],
    "CI2": ["CIRE", {"N": VRE_2, "RE1": VRE_1}],
    "CI1": ["CIRE", {"N": VRE_3, "RE1": VRE_2}],
    # https://resources.maxar.com/optical-imagery/multispectral-reference-guide
    "WV_WI": ["NHFD", {"RE1": WV, "A": CA}],
    "WV_VI": ["NHFD", {"RE1": WV, "A": RED}],
    # https://www.indexdatabase.de/db/i-single.php?id=204
    "SRSWIR": ["DSI", {"S1": SWIR_1, "N": SWIR_2}],
    # https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/22
    "SBI": ["BIXS", {"G": RED, "R": NIR}],
}


def _idx_fct(function: Callable) -> Callable:
    """
    Decorator of index functions
    """

    @wraps(function)
    def _idx_fct_wrapper(bands: dict) -> xr.DataArray:
        """
        Index functions wrapper
        Args:
        bands (dict): Bands as {band_name: xr.DataArray}

        Returns:
            xr.DataArray: Computed index
        """
        out_np = function({key: val for key, val in bands.items()})

        # Take the first band as a template for xarray
        first_xda = list(bands.values())[0]
        out_xda = first_xda.copy(data=out_np)

        out = rasters.set_metadata(out_xda, first_xda, new_name=str(function.__name__))
        return out

    return _idx_fct_wrapper


def compute_index(index: str, bands: dict, **kwargs) -> xr.DataArray:
    """

    Args:
        index (str): Index name (as a string)
        bands (dict): Band dictionary
        **kwargs: Kwargs

    Returns:
        xr.DataArray: Computed index
    """

    def _compute_params(_bands, **_kwargs):
        prms = {}
        for key, value in _bands.items():
            with contextlib.suppress(KeyError):
                prms[EOREADER_TO_SPYNDEX_DICT[key]] = value.data
        prms.update(_kwargs)

        return prms

    if hasattr(spyndex.indices, index):
        parameters = _compute_params(bands, **kwargs)

        if index == "SAVI":
            parameters["L"] = 0.5
        elif index == "EVI":
            parameters["g"] = 2.5
            parameters["C1"] = 6.0
            parameters["C2"] = 7.5
            parameters["L"] = 1.0

        index_arr = spyndex.computeIndex(index, parameters)

    elif index in DEPRECATED_SPECTRAL_INDICES:
        index_arr = spyndex.computeIndex(
            DEPRECATED_SPECTRAL_INDICES[index], _compute_params(bands, **kwargs)
        )
    elif index in EOREADER_DERIVATIVES:
        idx_name = EOREADER_DERIVATIVES[index][0]
        params = {
            key: bands[value].data
            for key, value in EOREADER_DERIVATIVES[index][1].items()
        }
        index_arr = spyndex.computeIndex(idx_name, params)
    else:
        index_arr = eval(index)(bands)

    # TODO: check if metadata is kept with spyndex

    # Take the first band as a template for xarray
    first_xda = list(bands.values())[0]
    out_xda = first_xda.copy(data=index_arr)

    return rasters.set_metadata(out_xda, first_xda, new_name=index)


@_idx_fct
def TCBRI(bands: dict) -> xr.DataArray:
    """
    Tasseled Cap Brightness:

    - `Wikipedia <https://en.wikipedia.org/wiki/Tasseled_cap_transformation>`_
    - `Index Database <https://www.indexdatabase.de/db/r-single.php?id=723>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (
        0.3037 * bands[BLUE]
        + 0.2793 * bands[GREEN]
        + 0.4743 * bands[RED]
        + 0.5585 * bands[NIR]
        + 0.5082 * bands[SWIR_1]
        + 0.1863 * bands[SWIR_2]
    )


@_idx_fct
def TCGRE(bands: dict) -> xr.DataArray:
    """
    Tasseled Cap Greenness:

    - `Wikipedia <https://en.wikipedia.org/wiki/Tasseled_cap_transformation>`_
    - `Index Database <https://www.indexdatabase.de/db/r-single.php?id=723>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (
        -0.2848 * bands[BLUE]
        - 0.2435 * bands[GREEN]
        - 0.5436 * bands[RED]
        + 0.7243 * bands[NIR]
        + 0.0840 * bands[SWIR_1]
        - 0.1800 * bands[SWIR_2]
    )


@_idx_fct
def TCWET(bands: dict) -> xr.DataArray:
    """
    Tasseled Cap Wetness:

    - `Wikipedia <https://en.wikipedia.org/wiki/Tasseled_cap_transformation>`_
    - `Index Database <https://www.indexdatabase.de/db/r-single.php?id=723>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (
        0.1509 * bands[BLUE]
        + 0.1973 * bands[GREEN]
        + 0.3279 * bands[RED]
        + 0.3406 * bands[NIR]
        - 0.7112 * bands[SWIR_1]
        - 0.4572 * bands[SWIR_2]
    )


@_idx_fct
def SCI(bands: dict) -> xr.DataArray:
    """
    `Soil Cuirass Index <https://hal.archives-ouvertes.fr/hal-03207299/document>`_ (p.4)

    It aims is to dissociate vegetated coverings from mineralized surfaces
    *Okaingni et al. 2010; Stephane et al. 2016*

    :code:`SCI = 3*GREEN - RED - 100`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return 3 * bands[GREEN] - bands[RED] - 100


def get_all_index_names() -> list:
    """
    Get all index names contained in this file

    .. code-block:: python

        >>> from eoreader.bands import index
        >>> index.get_all_index_names()
        ['AFRI_1_6', 'AFRI_2_1', 'AWEInsh', 'AWEIsh', 'BAI', ..., 'WI']

    Returns:
        list: Index names

    """
    return get_spyndex_indices() + get_eoreader_indices()


def get_eoreader_indices() -> list:
    """
    Get list of all EOReader indices

    Returns:
        list: list of all EOReader indices
    """
    eoreader_indices = []

    functions = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)

    for name, fct in functions:
        # Do not gather this fct nor da.true_divide
        if name[0].isupper():
            eoreader_indices.append(fct.__name__)

    # Add aliases
    for eoreader_idx, spyndex_idx in DEPRECATED_SPECTRAL_INDICES.items():
        if hasattr(spyndex.indices, spyndex_idx):
            eoreader_indices.append(eoreader_idx)

    # Add derivatives
    for index, deriv_list in EOREADER_DERIVATIVES.items():
        if hasattr(spyndex.indices, deriv_list[0]):
            eoreader_indices.append(index)

    return eoreader_indices


def get_spyndex_indices() -> list:
    """
    Get list of all Spyndex indices

    Returns:
        list: list of all Spyndex indices
    """
    return list(spyndex.indices)


def is_eoreader_idx(index: str) -> bool:
    """
    Yes if the string is an EOReader index

    Args:
        index (str): String to test

    Returns:
        bool: True if the string is an EOReader index
    """
    return index in get_eoreader_indices()


def is_spyndex_idx(index: str) -> bool:
    """
    Yes if the string is a Spyndex index

    Args:
        index (str): String to test

    Returns:
        bool: True if the string is a Spyndex index
    """
    return index in get_spyndex_indices()


# Check that no EOReader index name shadows Spyndex indices
assert not any(is_spyndex_idx(alias) for alias in DEPRECATED_SPECTRAL_INDICES)
assert not any(is_spyndex_idx(alias) for alias in EOREADER_DERIVATIVES)


def get_needed_bands(index: str) -> list:
    """
    Gather all the needed bands for the specified index function

    .. code-block:: python

        >>> index.get_needed_bands(NDVI)
        [<SpectralBandNames.NIR: 'NIR'>, <SpectralBandNames.RED: 'RED'>]

    Returns:
        list: Needed bands for the index function
    """
    if is_eoreader_idx(index):
        if index in EOREADER_DERIVATIVES:
            return list(EOREADER_DERIVATIVES[index][1].values())
        elif index in DEPRECATED_SPECTRAL_INDICES:
            # Don't need gamma etc.
            return [
                SPYNDEX_TO_EOREADER_DICT.get(band)
                for band in getattr(
                    spyndex.indices, DEPRECATED_SPECTRAL_INDICES[index]
                ).bands
            ]
        else:
            # Get source code from this fct
            code = inspect.getsource(eval(index))

            # Parse band's signature
            b_regex = r"spb\.\w+"

            return [
                getattr(SpectralBandNames, b.split(".")[-1])
                for b in re.findall(b_regex, code)
            ]
    elif is_spyndex_idx(index):
        # Don't need gamma etc.
        return [
            SPYNDEX_TO_EOREADER_DICT.get(band)
            for band in getattr(spyndex.indices, index).bands
            if SPYNDEX_TO_EOREADER_DICT.get(band) is not None
        ]
    else:
        raise NotImplementedError(
            f"Non existing index, please chose a spectral indice among {get_all_index_names()}"
        )


def get_all_needed_bands() -> dict:
    """
    Gather all the needed bands for all index functions

    .. code-block:: python

        >>> index.get_all_needed_bands()
        {
            <function AFRI_1_6 at 0x00000261F6FF36A8>: [<SpectralBandNames.NIR: 'NIR'>, <SpectralBandNames.SWIR_2: 'SWIR_2'>],
            ...
            <function WI at 0x00000261F6FF3620>: [<SpectralBandNames.NIR: 'NIR'>, <SpectralBandNames.SWIR_1: 'SWIR_1'>]
        }

        >>> # Or written in a more readable fashion:
        >>> {idx.__name__: [band.value for band in bands] for idx, bands in index.get_all_needed_bands().items()}
        {
            'AFRI_1_6': ['NIR', 'SWIR_2'],
            ...,
            'WI': ['NIR', 'SWIR_1']
        }

    Returns:
        dict: Needed bands for all index functions

    """
    return {index: get_needed_bands(index) for index in get_all_index_names()}


def is_index(index) -> bool:
    """
    Returns True if is an index function from the :code:`bands.index` module

    .. code-block:: python

        >>> from eoreader.bands import *
        >>> is_index(NDVI)
        True
        >>> is_index(HH)
        False
        >>> is_index(GREEN)
        False
        >>> is_index(SLOPE)
        False
        >>> is_index(CLOUDS)
        False

    Args:
        index (Any): Anything that could be an index

    Returns:
        bool: True if the index asked is an index function (such as :code:`index.NDVI`)

    """
    return str(index) in get_all_index_names()


NEEDED_BANDS = get_all_needed_bands()

# Set all indices
for _idx in get_all_index_names():
    vars()[_idx] = _idx
    # TODO: set another thing than str ? Create an IndexName object ?
