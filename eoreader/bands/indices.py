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
Set of usual spectral indices.

**Note**: This is easier to manage indices as raw functions in a file rather than stored in a class
"""
# Index not snake case
# pylint: disable=C0103
import inspect
import logging
import re
import sys
from functools import wraps
from typing import Callable

import numpy as np
import xarray as xr
from sertit import files, rasters

from eoreader.bands.spectral_bands import SpectralBandNames as spb
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
np.seterr(divide="ignore", invalid="ignore")


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
        # WARNING: for performance issues, use numpy arrays here to speed up computation !
        out_np = function({key: val.data for key, val in bands.items()})

        # Take the first band as a template for xarray
        first_xda = list(bands.values())[0]
        out_xda = first_xda.copy(data=out_np)

        out = rasters.set_metadata(out_xda, first_xda, new_name=str(function.__name__))
        return out

    return _idx_fct_wrapper


def _norm_diff(band_1: xr.DataArray, band_2: xr.DataArray) -> xr.DataArray:
    """
    Get normalized difference index between band 1 and band 2:
    (band_1 - band_2)/(band_1 + band_2)

    Args:
        band_1 (xr.DataArray): Band 1
        band_2 (xr.DataArray): Band 2

    Returns:
        xr.DataArray: Normalized Difference between band 1 and band 2
    """
    norm = (band_1 - band_2) / (band_1 + band_2)
    return norm


@_idx_fct
def RGI(bands: dict) -> xr.DataArray:
    """
    `Relative Greenness Index <https://www.indexdatabase.de/db/i-single.php?id=326>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.RED] / bands[spb.GREEN]


@_idx_fct
def GRI(bands: dict) -> xr.DataArray:
    """
    Green-to-Red ratio Index

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.GREEN] / bands[spb.RED]


@_idx_fct
def NDVI(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference Vegetation Index <https://www.indexdatabase.de/db/i-single.php?id=58>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NIR], bands[spb.RED])


@_idx_fct
def SAVI(bands: dict) -> xr.DataArray:
    """
    `Soil Adjusted Vegetation Index <https://www.indexdatabase.de/db/i-single.php?id=87>`_ with L=0.5

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    coeff = 0.5
    return (
        (1 + coeff)
        * (bands[spb.NIR] - bands[spb.RED])
        / (bands[spb.NIR] + bands[spb.RED] + coeff)
    )


@_idx_fct
def OSAVI(bands: dict) -> xr.DataArray:
    """
    `Optimized Soil Adjusted Vegetation Index <https://www.indexdatabase.de/db/i-single.php?id=63>`_ with L=0.16

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    coeff = 0.16
    return (
        (1 + coeff)
        * (bands[spb.NIR] - bands[spb.RED])
        / (bands[spb.NIR] + bands[spb.RED] + coeff)
    )


@_idx_fct
def VARI(bands: dict) -> xr.DataArray:
    """
    `Visible Atmospherically Resistant Index (Green) <https://www.indexdatabase.de/db/i-single.php?id=356>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (bands[spb.GREEN] - bands[spb.RED]) / (
        bands[spb.GREEN] + bands[spb.RED] - bands[spb.BLUE]
    )


@_idx_fct
def EVI(bands: dict) -> xr.DataArray:
    """
    `Enhanced Vegetation Index <https://www.indexdatabase.de/db/i-single.php?id=16>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (
        2.5
        * (bands[spb.NIR] - bands[spb.RED])
        / (bands[spb.NIR] + 6 * bands[spb.RED] - 7.5 * bands[spb.BLUE] + 1)
    )


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
        0.3037 * bands[spb.BLUE]
        + 0.2793 * bands[spb.GREEN]
        + 0.4743 * bands[spb.RED]
        + 0.5585 * bands[spb.NIR]
        + 0.5082 * bands[spb.SWIR_1]
        + 0.1863 * bands[spb.SWIR_2]
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
        -0.2848 * bands[spb.BLUE]
        - 0.2435 * bands[spb.GREEN]
        - 0.5436 * bands[spb.RED]
        + 0.7243 * bands[spb.NIR]
        + 0.0840 * bands[spb.SWIR_1]
        - 0.1800 * bands[spb.SWIR_2]
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
        0.1509 * bands[spb.BLUE]
        + 0.1973 * bands[spb.GREEN]
        + 0.3279 * bands[spb.RED]
        + 0.3406 * bands[spb.NIR]
        - 0.7112 * bands[spb.SWIR_1]
        - 0.4572 * bands[spb.SWIR_2]
    )


@_idx_fct
def NDRE2(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference Red-Edge <https://www.indexdatabase.de/db/i-single.php?id=223>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NARROW_NIR], bands[spb.VRE_1])


@_idx_fct
def NDRE3(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference Red-Edge <https://www.indexdatabase.de/db/i-single.php?id=223>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NARROW_NIR], bands[spb.VRE_2])


@_idx_fct
def CI1(bands: dict) -> xr.DataArray:
    """
    Chlorophyll Index RedEdge VRE_3/VRE_2

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.VRE_3] / bands[spb.VRE_2] - 1


@_idx_fct
def CI2(bands: dict) -> xr.DataArray:
    """
    Chlorophyll Index RedEdge VRE_2/VRE_1

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.VRE_2] / bands[spb.VRE_1] - 1


@_idx_fct
def GLI(bands: dict) -> xr.DataArray:
    """
    `Green leaf index <https://www.indexdatabase.de/db/i-single.php?id=375>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (2 * bands[spb.GREEN] - bands[spb.RED] - bands[spb.BLUE]) / (
        2 * bands[spb.GREEN] + bands[spb.RED] + bands[spb.BLUE]
    )


@_idx_fct
def GNDVI(bands: dict) -> xr.DataArray:
    """
    `Green NDVI <https://www.indexdatabase.de/db/i-single.php?id=401>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NIR], bands[spb.GREEN])


@_idx_fct
def RI(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference RED/GREEN Redness Index <https://www.indexdatabase.de/db/i-single.php?id=74>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.VRE_1], bands[spb.GREEN])


@_idx_fct
def NDGRI(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference GREEN/RED Index <https://www.indexdatabase.de/db/i-single.php?id=390>`_

    Also known as NDGR.

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.GREEN], bands[spb.RED])


@_idx_fct
def CIG(bands: dict) -> xr.DataArray:
    """
    `Chlorophyll Index Green <https://www.indexdatabase.de/db/i-single.php?id=128>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (bands[spb.NIR] / bands[spb.GREEN]) - 1


@_idx_fct
def NDMI(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference Moisture Index <https://www.indexdatabase.de/db/i-single.php?id=56>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NARROW_NIR], bands[spb.SWIR_1])


@_idx_fct
def NDMI21(bands: dict) -> xr.DataArray:
    """
    Normalized Difference Moisture Index (with SWIR_21)

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NARROW_NIR], bands[spb.SWIR_2])


@_idx_fct
def DSWI(bands: dict) -> xr.DataArray:
    """
    `Disease water stress index <https://www.indexdatabase.de/db/i-single.php?id=106>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (bands[spb.NIR] + bands[spb.GREEN]) / (bands[spb.SWIR_1] + bands[spb.RED])


@_idx_fct
def SRSWIR(bands: dict) -> xr.DataArray:
    """
    `Simple Ratio SWIR_1/SWIR_2 Clay Minerals <https://www.indexdatabase.de/db/i-single.php?id=204>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.SWIR_1] / bands[spb.SWIR_2]


@_idx_fct
def RDI(bands: dict) -> xr.DataArray:
    """
    `Ratio Drought Index <https://www.indexdatabase.de/db/i-single.php?id=71>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return bands[spb.SWIR_2] / bands[spb.NARROW_NIR]


@_idx_fct
def NDWI(bands: dict) -> xr.DataArray:
    """
    `Normalized Difference Water Index <https://pro.arcgis.com/fr/pro-app/2.7/arcpy/image-analyst/ndwi.htm>`_
    (GREEN Version)

    :code:`NDWI = (GREEN - NIR) / (GREEN + NIR)`

    For the SWIR version, see the NDMI.

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.GREEN], bands[spb.NIR])


@_idx_fct
def BAI(bands: dict) -> xr.DataArray:
    """
    `Burn Area Index <https://www.harrisgeospatial.com/docs/BackgroundBurnIndices.html>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return 1.0 / ((0.1 - bands[spb.RED]) ** 2 + (0.06 - bands[spb.NIR]) ** 2)


@_idx_fct
def BAIS2(bands: dict) -> xr.DataArray:
    """
    `Burn Area Index for Sentinel-2
    <https://www.researchgate.net/publication/323964124_BAIS2_Burned_Area_Index_for_Sentinel-2>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    # (1-((B06*B07*B8A)/B04)**0.5)*((B12-B8A)/((B12+B8A)**0.5)+1);
    a = ((bands[spb.VRE_2] * bands[spb.VRE_3] * bands[spb.NIR]) / bands[spb.RED]) ** 0.5
    b = (bands[spb.SWIR_2] - bands[spb.NIR]) / (
        (bands[spb.SWIR_2] + bands[spb.NIR]) ** 0.5
    )
    return (1 - a) * (1 + b)


@_idx_fct
def NBR(bands: dict) -> xr.DataArray:
    """
    `Normalized Burn Ratio <https://www.indexdatabase.de/db/i-single.php?id=53>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.NARROW_NIR], bands[spb.SWIR_2])


@_idx_fct
def MNDWI(bands: dict) -> xr.DataArray:
    """
    `Modified Normalised Difference Water Index <https://wiki.orfeo-toolbox.org/index.php/MNDWI>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return _norm_diff(bands[spb.GREEN], bands[spb.SWIR_1])


@_idx_fct
def AWEInsh(bands: dict) -> xr.DataArray:
    """
    Automated Water Extraction Index not shadow: Feyisa et al. (2014)

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return 4 * (bands[spb.GREEN] - bands[spb.SWIR_1]) - (
        0.25 * bands[spb.NIR] + 2.75 * bands[spb.SWIR_2]
    )


@_idx_fct
def AWEIsh(bands: dict) -> xr.DataArray:
    """
    Automated Water Extraction Index shadow: Feyisa et al. (2014)

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index

    """
    return (
        bands[spb.BLUE]
        + 2.5 * bands[spb.GREEN]
        - 1.5 * (bands[spb.NIR] + bands[spb.SWIR_1])
        - 0.25 * bands[spb.SWIR_2]
    )


@_idx_fct
def WI(bands: dict) -> xr.DataArray:
    """
    Water Index (2015): Fisher et al. (2016)

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return (
        1.7204
        + 171 * bands[spb.GREEN]
        + 3 * bands[spb.RED]
        - 70 * bands[spb.NIR]
        - 45 * bands[spb.SWIR_1]
        - 71 * bands[spb.SWIR_2]
    )


@_idx_fct
def AFRI_1_6(bands: dict) -> xr.DataArray:
    """
    `Aerosol free vegetation index 1600 <https://www.indexdatabase.de/db/i-single.php?id=393>`_

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.NARROW_NIR], 0.66 * bands[spb.SWIR_1])


@_idx_fct
def AFRI_2_1(bands: dict) -> xr.DataArray:
    """
    `Aerosol free vegetation index 2100 <https://www.indexdatabase.de/db/i-single.php?id=395>`_

    .. WARNING::
        There is an error in the formula, go see the papers to get the right one (0.56 instead of 0.5):
        https://core.ac.uk/download/pdf/130673386.pdf

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.NARROW_NIR], 0.5 * bands[spb.SWIR_2])


@_idx_fct
def BSI(bands: dict) -> xr.DataArray:
    """
    `Barren Soil Index <http://tropecol.com/pdf/open/PDF_43_1/43104.pdf>`_
    Rikimaru et al., 2002. Tropical forest cover density mapping.


    :code:`BSI = ((RED+SWIR) – (NIR+BLUE)) / ((RED+SWIR) + (NIR+BLUE))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(
        bands[spb.RED] + bands[spb.SWIR_1], bands[spb.NIR] + bands[spb.BLUE]
    )


# WorldView index (without the ones with SWIR)
# https://resources.maxar.com/optical-imagery/multispectral-reference-guide


@_idx_fct
def WV_WI(bands: dict) -> xr.DataArray:
    """
    `WorldView-Water (WV-WI) <https://resources.maxar.com/optical-imagery/multispectral-reference-guide>`_

    Useful for detecting standing, flowing water, or shadow in VNIR imagery

    :code:`WV_WI = ((B8-B1)/(B8+B1))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.WV], bands[spb.CA])


@_idx_fct
def WV_VI(bands: dict) -> xr.DataArray:
    """
    `WorldView-Vegetation (WV-VI) <https://resources.maxar.com/optical-imagery/multispectral-reference-guide>`_

    Useful for detecting vegetation and assessing vegetation health

    :code:`WV_VI = ((B8-B5)/(B8+B5))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.WV], bands[spb.RED])


@_idx_fct
def WV_SI(bands: dict) -> xr.DataArray:
    """
    `WorldView-Soil (WV-SI) <https://resources.maxar.com/optical-imagery/multispectral-reference-guide>`_

    Useful for detecting and differentiating exposed soil

    :code:`WV_SI = ((B4-B3)/(B4+B3))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.YELLOW], bands[spb.GREEN])


@_idx_fct
def WV_BI(bands: dict) -> xr.DataArray:
    """
    `WorldView-Built-up (WV-BI) <https://resources.maxar.com/optical-imagery/multispectral-reference-guide>`_

    Useful for detecting impervious surfaces such as buildings and roads

    :code:`WV_BI = ((B6-B1)/(B6+B1))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.VRE_1], bands[spb.CA])


@_idx_fct
def SI(bands: dict) -> xr.DataArray:
    """
    Shadow Index

    Replacing maxima by percentile_98 in order to discard potential outliers

    :code:`SI = sqrt((perc_98(GREEN) - GREEN)*(perc_98(RED) - RED))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    green = np.nanpercentile(bands[spb.GREEN], 99) - bands[spb.GREEN]
    green = np.where(green < 0, 0, green)
    red = np.nanpercentile(bands[spb.RED], 99) - bands[spb.RED]
    red = np.where(red < 0, 0, red)
    return np.sqrt(green * red)


@_idx_fct
def GVMI(bands: dict) -> xr.DataArray:
    """
    `Global Vegetation Moisture Index <https://www.indexdatabase.de/db/i-single.php?id=372>`_

    :code:`GVMI = norm_diff(NIR+0.1), SWIR_2 + 0.02))`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return _norm_diff(bands[spb.NARROW_NIR] + 0.1, bands[spb.SWIR_2] + 0.02)


@_idx_fct
def SBI(bands: dict) -> xr.DataArray:
    """
    `Soil Brightness Index <https://hal.archives-ouvertes.fr/hal-03207299/document>`_ (p.4)

    The role of the brightness index is to identify the reflectance of soil
    and to highlight the vegetal cover of bare areas.
    *Bannari et al. 1996; Soufiane Maimouni and Bannari 2011*

    :code:`SBI = sqrt(RED**2 + NIR**2)`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return np.sqrt(bands[spb.RED] ** 2 + bands[spb.NIR] ** 2)


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
    return 3 * bands[spb.GREEN] - bands[spb.RED] - 100


@_idx_fct
def PANI(bands: dict) -> xr.DataArray:
    """
    Panchromatic mocking index

    :code:`PAN = sqrt(RED**2 + GREEN**2 + BLUE**2)`

    Args:
        bands (dict): Bands as {band_name: xr.DataArray}

    Returns:
        xr.DataArray: Computed index
    """
    return np.sqrt(bands[spb.RED] ** 2 + bands[spb.GREEN] ** 2 + bands[spb.BLUE] ** 2)


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
    return [idx_fct.__name__ for idx_fct in get_all_indices()]


def get_all_indices() -> list:
    """
    Get all index functions contained in this file

    .. code-block:: python

        >>> from eoreader.bands import index
        >>> index.get_all_indices()
        [<function AFRI_1_6 at 0x00000118FFFB51E0>, ..., <function WI at 0x00000118FFFB5158>]

    Returns:
        list: Index functions

    """
    idx = []
    functions = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)

    for (name, fct) in functions:
        # Do not gather this fct nor da.true_divide
        if name[0].isupper():
            idx.append(fct)

    return idx


def get_needed_bands(index: Callable) -> list:
    """
    Gather all the needed bands for the specified index function

    .. code-block:: python

        >>> index.get_needed_bands(NDVI)
        [<SpectralBandNames.NIR: 'NIR'>, <SpectralBandNames.RED: 'RED'>]

    Returns:
        list: Needed bands for the index function
    """
    # Get source code from this fct
    code = inspect.getsource(index)

    # Parse band's signature
    b_regex = r"spb\.\w+"

    return [getattr(spb, b.split(".")[-1]) for b in re.findall(b_regex, code)]


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
    needed_bands = {}

    # Get all function from this file
    functions = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)

    for (name, function) in functions:
        # Do not gather this fct nor da.true_divide
        if name[0].isupper():
            needed_bands[function] = get_needed_bands(function)

    return needed_bands


def is_index(idx) -> bool:
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
        idx (Any): Anything that could be an index

    Returns:
        bool: True if the index asked is an index function (such as :code:`index.NDVI`)

    """
    if isinstance(idx, str):
        is_idx = idx in get_all_index_names()
    else:
        is_idx = (
            files.get_filename(__file__) in idx.__module__
            and idx.__name__ in get_all_index_names()
        )
    return is_idx


NEEDED_BANDS = get_all_needed_bands()
