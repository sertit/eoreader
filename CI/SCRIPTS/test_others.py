import os

import pytest
import pandas as pd
from lxml import etree

from .scripts_utils import OPT_PATH, READER
from eoreader import utils
from eoreader.bands.bands import SarBandNames, OpticalBands
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


def test_products():
    # Get paths
    prod1_path = os.path.join(OPT_PATH, "LC08_L1TP_200030_20201220_20210310_02_T1")  # Newer
    prod2_path = os.path.join(OPT_PATH, "LM03_L1GS_033028_19820906_20180414_01_T2")  # Older

    # Open porods
    prod1 = READER.open(prod1_path)
    prod2 = READER.open(prod2_path)

    assert prod1 == prod1
    assert prod1 >= prod1
    assert prod1 <= prod1
    assert prod1 > prod2
    assert prod2 < prod1
    assert prod1 != prod2

    # Read the LANDSAT metdata the two ways
    mtd_xml, nmsp = prod1.read_mtd(force_pd=False)
    mtd_pd = prod1.read_mtd(force_pd=True)
    assert isinstance(mtd_pd, pd.DataFrame)
    assert isinstance(mtd_xml, etree._Element)
    assert nmsp == ""


def test_bands():
    # SAR
    assert SarBandNames.from_list(["VV", "VH"]) == [VV, VH]
    assert SarBandNames.to_value_list([HV_DSPK, VV]) == ['DESPK_HV', 'VV']
    assert SarBandNames.to_value_list() == SarBandNames.list_values()
    assert SarBandNames.corresponding_speckle(SarBandNames.VV) == VV
    assert SarBandNames.corresponding_speckle(SarBandNames.VV_DSPK) == VV

    # OPTIC
    map_dic = {
        CA: '01',
        BLUE: '02',
        GREEN: '03',
        RED: '04',
        VRE_1: '05',
        VRE_2: '06',
        VRE_3: '07',
        NIR: '08',
        NNIR: '8A',
        WV: '09',
        SWIR_1: '11',
        SWIR_2: '12'
    }
    ob = OpticalBands()
    ob.map_bands(map_dic)

    for key, val in map_dic.items():
        assert key in ob._band_map
        assert ob._band_map[key] == map_dic[key]

    with pytest.raises(InvalidTypeError):
        ob.map_bands({VV: "wrong_val"})
