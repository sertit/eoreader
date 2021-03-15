"""
Set of usual optical index.

**Note**: The nodata is always considered to be set to 0.
If this changes, it will become mandatory to use the NODATA mask everywhere !

**Note 2**: This is easier to manage index as raw functions in a file rather than stored in a class
"""
# Index not snake case
# pylint: disable=C0103
import inspect
import logging
import re
import sys
from typing import Union, Callable

import numpy as np

from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

np.seterr(divide='ignore', invalid='ignore')

NODATA = 0


def _set_no_data(idx: np.ma.masked_array) -> np.ma.masked_array:
    """
    Set nodata to a masked array (replacing masked pixel values by the fill_value)
    Args:
        idx (np.ma.masked_array): Index

    Returns:
        np.ma.masked_array: Index with no data filled with correct values
    """
    # idx[idx.mask] = idx.fill_value
    idx[idx.mask] = np.ma.masked
    return idx


def _no_data_divide(band_1: Union[float, np.ma.masked_array], band_2: np.ma.masked_array) -> np.ma.masked_array:
    """
    Get the dicision taking into account the nodata between b1 and b2

    Args:
        band_1 (np.ma.masked_array): Band 1
        band_2 (np.ma.masked_array): Band 2

    Returns:
        np.ma.masked_array: Division between band 1 and band 2
    """
    return _set_no_data(np.divide(band_1, band_2))


def _norm_diff(band_1: np.ma.masked_array, band_2: np.ma.masked_array) -> np.ma.masked_array:
    """
    Get normalized difference index between band 1 and band 2:
    (band_1 - band_2)/(band_1 + band_2)

    Args:
        band_1 (np.ma.masked_array): Band 1
        band_2 (np.ma.masked_array): Band 2

    Returns:
        np.ma.masked_array: Normalized Difference between band 1 and band 2

    """
    return _no_data_divide(band_1 - band_2, band_1 + band_2)


def RGI(bands: dict) -> np.ma.masked_array:
    """
    Relative Greenness Index: https://www.indexdatabase.de/db/i-single.php?id=326

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _no_data_divide(bands[obn.RED], bands[obn.GREEN])


def NDVI(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Vegetation Index: https://www.indexdatabase.de/db/i-single.php?id=59

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NIR], bands[obn.RED])


def TCBRI(bands: dict) -> np.ma.masked_array:
    """
    Tasseled Cap Brightness:
    https://en.wikipedia.org/wiki/Tasseled_cap_transformation
    https://www.indexdatabase.de/db/r-single.php?id=723

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(0.3037 * bands[obn.BLUE] + 0.2793 * bands[obn.GREEN] + 0.4743 * bands[obn.RED] +
                        0.5585 * bands[obn.NIR] + 0.5082 * bands[obn.SWIR_1] + 0.1863 * bands[obn.SWIR_2])


def TCGRE(bands: dict) -> np.ma.masked_array:
    """
    Tasseled Cap Greenness:
    https://en.wikipedia.org/wiki/Tasseled_cap_transformation
    https://www.indexdatabase.de/db/r-single.php?id=723

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(- 0.2848 * bands[obn.BLUE] - 0.2435 * bands[obn.GREEN] - 0.5436 * bands[obn.RED] +
                        0.7243 * bands[obn.NIR] + 0.0840 * bands[obn.SWIR_1] - 0.1800 * bands[obn.SWIR_2])


def TCWET(bands: dict) -> np.ma.masked_array:
    """
    Tasseled Cap Wetness:
    https://en.wikipedia.org/wiki/Tasseled_cap_transformation
    https://www.indexdatabase.de/db/r-single.php?id=723

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(0.1509 * bands[obn.BLUE] + 0.1973 * bands[obn.GREEN] + 0.3279 * bands[obn.RED] +
                        0.3406 * bands[obn.NIR] - 0.7112 * bands[obn.SWIR_1] - 0.4572 * bands[obn.SWIR_2])


def NDRE2(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Red-Edge: https://www.indexdatabase.de/db/i-single.php?id=223
    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NIR], bands[obn.VRE_1])


def NDRE3(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Red-Edge: https://www.indexdatabase.de/db/i-single.php?id=223

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NIR], bands[obn.VRE_2])


def GLI(bands: dict) -> np.ma.masked_array:
    """
    Green leaf index: https://www.indexdatabase.de/db/i-single.php?id=375

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _no_data_divide(2 * (bands[obn.GREEN] - bands[obn.RED] - bands[obn.BLUE]),
                           2 * (bands[obn.GREEN] + bands[obn.RED] + bands[obn.BLUE]))


def GNDVI(bands: dict) -> np.ma.masked_array:
    """
    Green NDVI: https://www.indexdatabase.de/db/i-single.php?id=401

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NIR], bands[obn.GREEN])


def RI(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Red/Green Redness Index: https://www.indexdatabase.de/db/i-single.php?id=74

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.VRE_1], + bands[obn.GREEN])


def NDGRI(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Green/Red Index: https://www.indexdatabase.de/db/i-single.php?id=390

    Also known as NDGR.

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.GREEN], bands[obn.RED])


def CIG(bands: dict) -> np.ma.masked_array:
    """
    Chlorophyll Index Green: https://www.indexdatabase.de/db/i-single.php?id=128

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(np.divide(bands[obn.NIR], bands[obn.GREEN]) - 1)


def NDMI(bands: dict) -> np.ma.masked_array:
    """
    Normalized Difference Moisture Index: https://www.indexdatabase.de/db/i-single.php?id=56

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NIR], + bands[obn.SWIR_1])


def DSWI(bands: dict) -> np.ma.masked_array:
    """
    Disease water stress index: https://www.indexdatabase.de/db/i-single.php?id=106

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _no_data_divide(bands[obn.NIR] + bands[obn.GREEN], bands[obn.SWIR_1] + bands[obn.RED])


def LWCI(bands: dict) -> np.ma.masked_array:
    """
    Leaf Water Content Index: https://www.indexdatabase.de/db/i-single.php?id=129

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    LOGGER.warning("This index formula is suspect (constant, = -1). You should use another one.")
    return - _no_data_divide(np.log(1 - (bands[obn.NIR] - bands[obn.SWIR_1])),
                             np.log(1 - (bands[obn.NIR] - bands[obn.SWIR_1])))


def SRSWIR(bands: dict) -> np.ma.masked_array:
    """
    Simple Ratio SWIRI/SWIRII Clay Minerals: https://www.indexdatabase.de/db/i-single.php?id=204

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _no_data_divide(bands[obn.SWIR_1], bands[obn.SWIR_2])


def RDI(bands: dict) -> np.ma.masked_array:
    """
    Ratio Drought Index: https://www.indexdatabase.de/db/i-single.php?id=71

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _no_data_divide(bands[obn.SWIR_2], bands[obn.NNIR])


def NDWI(bands: dict) -> np.ma.masked_array:
    """
    Simple Ratio MIR/NIR Ratio Drought Index: https://www.indexdatabase.de/db/i-single.php?id=71

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.GREEN], bands[obn.NIR])


def BAI(bands: dict) -> np.ma.masked_array:
    """
    Burn Area Index: https://www.harrisgeospatial.com/docs/BackgroundBurnIndices.html

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index
    """
    return _no_data_divide(1, (0.1 - bands[obn.RED]) ** 2 + (0.06 - bands[obn.NIR]) ** 2)


def NBR(bands: dict) -> np.ma.masked_array:
    """
    Normalized Burn Ratio: https://www.indexdatabase.de/db/i-single.php?id=53

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.NNIR], bands[obn.SWIR_2])


def MNDWI(bands: dict) -> np.ma.masked_array:
    """
    Modified Normalised Difference Water Index : https://wiki.orfeo-toolbox.org/index.php/MNDWI

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _norm_diff(bands[obn.GREEN], bands[obn.SWIR_1])


def AWEInsh(bands: dict) -> np.ma.masked_array:
    """
    Automated Water Extraction Index not shadow: Feyisa et al. (2014)

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(4 * (bands[obn.GREEN] - bands[obn.SWIR_1]) - (0.25 * bands[obn.NIR] + 2.75 * bands[obn.SWIR_2]))


def AWEIsh(bands: dict) -> np.ma.masked_array:
    """
    Automated Water Extraction Index shadow: Feyisa et al. (2014)

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index

    """
    return _set_no_data(bands[obn.BLUE] + 2.5 * bands[obn.GREEN] -
                        1.5 * (bands[obn.NIR] + bands[obn.SWIR_1]) - 0.25 * bands[obn.SWIR_2])


def WI(bands: dict) -> np.ma.masked_array:
    """
    Water Index (2015): Fisher et al. (2016)

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index
    """
    return _set_no_data(1.7204 + 171 * bands[obn.GREEN] + 3 * bands[obn.RED] -
                        70 * bands[obn.NIR] - 45 * bands[obn.SWIR_1] - 71 * bands[obn.SWIR_2])


def AFRI_1_6(bands: dict) -> np.ma.masked_array:
    """
    Aerosol free vegetation index 1600: https://www.indexdatabase.de/db/i-single.php?id=393

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index
    """
    return _norm_diff(bands[obn.NIR], 0.66 * bands[obn.SWIR_1])


def AFRI_2_1(bands: dict) -> np.ma.masked_array:
    """
    Aerosol free vegetation index 2100: https://www.indexdatabase.de/db/i-single.php?id=395

    :warning: There is an error in the formula, go see the papers to get the right one (0.56 instead of 0.5):
    https://core.ac.uk/download/pdf/130673386.pdf

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index
    """
    return _norm_diff(bands[obn.NIR], 0.5 * bands[obn.SWIR_2])


def BSI(bands: dict) -> np.ma.masked_array:
    """
    Barren Soil Index:
    Rikimaru et al., 2002. Tropical forest cover density mapping.
    http://tropecol.com/pdf/open/PDF_43_1/43104.pdf

    BSI = ((Red+SWIR) – (NIR+Blue)) / ((Red+SWIR) + (NIR+Blue))

    Args:
        bands (dict): Bands as {band_name: numpy array}

    Returns:
        np.ma.masked_array: Computed index
    """
    return _norm_diff(bands[obn.RED] + bands[obn.SWIR_1], bands[obn.NIR] + bands[obn.BLUE])


def get_all_index_names() -> list:
    """
    Get all index names contained in this file

    ```python
    >>> from eoreader.bands import index
    >>> index.get_all_index_names()
    ['AFRI_1_6', 'AFRI_2_1', 'AWEInsh', 'AWEIsh', 'BAI', ..., 'WI']
    ```

    Returns:
        list: Index names

    """
    return [idx_fct.__name__ for idx_fct in get_all_index()]


def get_all_index() -> list:
    """
    Get all index functions contained in this file

    ```python
    >>> from eoreader.bands import index
    >>> index.get_all_index()
    [<function AFRI_1_6 at 0x00000118FFFB51E0>, ..., <function WI at 0x00000118FFFB5158>]
    ```

    Returns:
        list: Index functions

    """
    idx = []
    functions = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)

    for (name, fct) in functions:
        # Do not gather this fct nor np.divide
        if name[0].isupper():
            idx.append(fct)

    return idx


def get_needed_bands(index: Callable) -> list:
    """
    Gather all the needed bands for the specified index function

    ```python
    >>> index.get_needed_bands(index.NDVI)
    [<OpticalBandNames.NIR: 'NIR'>, <OpticalBandNames.RED: 'RED'>]
    ```
    Returns:
        list: Needed bands for the index function
    """
    # Get source code from this fct
    code = inspect.getsource(index)

    # Parse band's signature
    b_regex = r"obn\.\w+"

    return [getattr(obn, b.split('.')[-1]) for b in re.findall(b_regex, code)]


def get_all_needed_bands() -> dict:
    """
    Gather all the needed bands for all index functions

    ```python
    >>> index.get_all_needed_bands()
    {
        <function AFRI_1_6 at 0x00000261F6FF36A8>: [<OpticalBandNames.NIR: 'NIR'>, <OpticalBandNames.SWIR_2: 'SWIR_2'>],
        ...
        <function WI at 0x00000261F6FF3620>: [<OpticalBandNames.NIR: 'NIR'>, <OpticalBandNames.SWIR_1: 'SWIR_1'>]
    }

    >>> # Or written in a more readable fashion:
    >>> {idx.__name__: [band.value for band in bands] for idx, bands in index.get_all_needed_bands().items()}
    {
        'AFRI_1_6': ['NIR', 'SWIR_2'],
        ...,
        'WI': ['NIR', 'SWIR_1']
    }
    ```

    Returns:
        dict: Needed bands for all index functions

    """
    needed_bands = {}

    # Get all function from this file
    functions = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)

    for (name, function) in functions:
        # Do not gather this fct nor np.divide
        if name[0].isupper():
            needed_bands[function] = get_needed_bands(function)

    return needed_bands


NEEDED_BANDS = get_all_needed_bands()
