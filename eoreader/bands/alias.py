"""
Aliases for bands and index, created in order to import just this file and not obn, sbn and _idx.
You can import them as:
- `from eoreader.bands.alias import *` -> `GREEN`
- `from eoreader.bands import alias` -> `alias.GREEN`
"""
# Module name begins with _ to not be imported with *
import typing as _tp
from eoreader.bands.bands import OpticalBandNames as _obn, SarBandNames as _sbn
from eoreader.bands import index as _idx

# -- OPTICAL BANDS --
CA = _obn.CA
BLUE = _obn.BLUE
GREEN = _obn.GREEN
RED = _obn.RED
VRE_1 = _obn.VRE_1
VRE_2 = _obn.VRE_2
VRE_3 = _obn.VRE_3
NIR = _obn.NIR
NNIR = _obn.NNIR
WV = _obn.WV
FNIR = _obn.FNIR
CIRRUS = _obn.CIRRUS
SWIR_1 = _obn.SWIR_1
SWIR_2 = _obn.SWIR_2
MIR = _obn.MIR
TIR_1 = _obn.TIR_1
TIR_2 = _obn.TIR_2
PAN = _obn.PAN

# -- SAR BANDS --
VV = _sbn.VV
VV_DSPK = _sbn.VV_DSPK
HH = _sbn.HH
HH_DSPK = _sbn.HH_DSPK
VH = _sbn.VH
VH_DSPK = _sbn.VH_DSPK
HV = _sbn.HV
HV_DSPK = _sbn.HV_DSPK

# -- INDEX
RGI = _idx.RGI
NDVI = _idx.NDVI
TCBRI = _idx.TCBRI
TCGRE = _idx.TCGRE
TCWET = _idx.TCWET
NDRE2 = _idx.NDRE2
NDRE3 = _idx.NDRE3
GLI = _idx.GLI
GNDVI = _idx.GNDVI
RI = _idx.RI
NDGRI = _idx.NDGRI
CIG = _idx.CIG
PGR = _idx.PGR
NDMI = _idx.NDMI
DSWI = _idx.DSWI
LWCI = _idx.LWCI
SRSWIR = _idx.SRSWIR
RDI = _idx.RDI
NDWI = _idx.NDWI
BAI = _idx.BAI
NBR = _idx.NBR
MNDWI = _idx.MNDWI
AWEInsh = _idx.AWEInsh
AWEIsh = _idx.AWEIsh
WI = _idx.WI
AFRI_1_6 = _idx.AFRI_1_6
AFRI_2_1 = _idx.AFRI_2_1
BSI = _idx.BSI


def is_index(idx: _tp.Any) -> bool:
    """
    Returns True if is an index Callable from the index module

    Args:
        idx (Any): Sth that could be an index

    Returns:
        bool: True if the index asked is an index Callable (such as index.BSI)

    """
    return "index" in idx.__module__ and idx.__name__ in _idx.get_all_index()


def is_optical_band(band: _tp.Any) -> bool:
    """
    Returns True if is an optical band (obn.xxx)

    Args:
        band (Any): Sth that could be an optical band

    Returns:
        bool: True if the band asked is an optical band

    """
    return band in _obn


def is_sar_band(band: _tp.Any) -> bool:
    """
    Returns True if is a SAR band (sbn.xxx)

    Args:
        band (Any): Sth that could be a SAR band

    Returns:
        bool: True if the band asked is a SAR band

    """
    return band in _sbn


def is_band(band: _tp.Any) -> bool:
    """
    Returns True if is a SAR band (sbn.xxx)

    Args:
        band (Any): Sth that could be a SAR band

    Returns:
        bool: True if the band asked is a SAR band

    """
    return is_sar_band(band) or is_optical_band(band)
