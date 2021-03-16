import os

import pytest

from eoreader import utils
from eoreader.products.product import MERIT_DEM

from eoreader.bands.alias import *

def test_utils():
    # Root directory
    root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
    src_dir = os.path.join(root_dir, "eoreader")
    data_dir = os.path.join(src_dir, "data")
    assert utils.get_root_dir() == root_dir
    assert utils.get_src_dir() == src_dir
    assert utils.get_data_dir() == data_dir

    # DB dir
    assert os.path.isfile(MERIT_DEM)


def test_alias():
    # DEM
    assert not is_dem(NDVI)
    assert not is_dem(HH)
    assert not is_dem(GREEN)
    assert is_dem(SLOPE)

    # Index
    assert is_index(NDVI)
    assert not is_index(HH)
    assert not is_index(GREEN)
    assert not is_index(SLOPE)

    # Bands
    assert not is_band(NDVI)
    assert is_band(HH)
    assert is_band(GREEN)
    assert not is_band(SLOPE)

    # Other functions
    lst = to_band_or_idx(["NDVI", "GREEN", RED, "DESPK_VH", "SLOPE"])
    assert lst == [NDVI, GREEN, RED, VH_DSPK, SLOPE]
    with pytest.raises(InvalidTypeError):
        to_band_or_idx(["WRONG_BAND"])