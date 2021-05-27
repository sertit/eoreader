import os

import pandas as pd
import pytest
import xarray as xr
from lxml import etree

from eoreader import utils
from eoreader.bands.alias import *
from eoreader.bands.bands import OpticalBands, SarBandNames
from eoreader.env_vars import DEM_PATH

from .scripts_utils import OPT_PATH, READER


@pytest.mark.xfail
def test_utils():
    root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
    # Root directory
    src_dir = os.path.join(root_dir, "eoreader")
    data_dir = os.path.join(src_dir, "data")
    assert utils.get_root_dir() == root_dir
    assert utils.get_src_dir() == src_dir
    assert utils.get_data_dir() == data_dir


def test_alias():
    # DEM
    assert not is_dem(NDVI)
    assert not is_dem(HH)
    assert not is_dem(GREEN)
    assert is_dem(SLOPE)
    assert not is_dem(CLOUDS)

    # Index
    assert is_index(NDVI)
    assert not is_index(HH)
    assert not is_index(GREEN)
    assert not is_index(SLOPE)
    assert not is_index(CLOUDS)

    # Bands
    assert not is_band(NDVI)
    assert is_band(HH)
    assert is_band(GREEN)
    assert not is_band(SLOPE)
    assert not is_band(CLOUDS)

    # Clouds
    assert not is_clouds(NDVI)
    assert not is_clouds(HH)
    assert not is_clouds(GREEN)
    assert not is_clouds(SLOPE)
    assert is_clouds(CLOUDS)

    # Other functions
    lst = to_band(["NDVI", "GREEN", RED, "VH_DSPK", "SLOPE", DEM, "CLOUDS", CLOUDS])
    assert lst == [NDVI, GREEN, RED, VH_DSPK, SLOPE, DEM, CLOUDS, CLOUDS]
    with pytest.raises(InvalidTypeError):
        to_band(["WRONG_BAND"])


def test_products():
    # Get paths
    prod1_path = os.path.join(
        OPT_PATH, "LC08_L1TP_200030_20201220_20210310_02_T1"
    )  # Newer
    prod2_path = os.path.join(
        OPT_PATH, "LM03_L1GS_033028_19820906_20180414_01_T2"
    )  # Older

    # Open prods
    prod1 = READER.open(prod1_path)
    prod2 = READER.open(prod2_path)

    assert prod1 == prod1
    assert prod1 >= prod1
    assert prod1 <= prod1
    assert prod1 > prod2
    assert prod2 < prod1
    assert prod1 != prod2

    # Read the LANDSAT metadata the two ways
    mtd_xml, nmsp = prod1.read_mtd(force_pd=False)
    mtd_pd = prod1.read_mtd(force_pd=True)
    assert isinstance(mtd_pd, pd.DataFrame)
    assert isinstance(mtd_xml, etree._Element)
    assert nmsp == {}

    # Check size
    green = prod1.load([GREEN], resolution=300)
    green2 = prod1.load([GREEN], size=(green[GREEN].rio.width, green[GREEN].rio.height))

    xr.testing.assert_equal(green[GREEN], green2[GREEN])

    # Test without a DEM set:
    old_dem = None
    if DEM_PATH in os.environ:
        old_dem = os.environ.pop(DEM_PATH)
    with pytest.raises(ValueError):
        prod1.load([DEM])
    with pytest.raises(FileNotFoundError):
        os.environ[DEM_PATH] = "fczergg"
        prod1.load([DEM])

    if old_dem is not None:
        os.environ[DEM_PATH] = old_dem


def test_bands():
    # SAR
    assert SarBandNames.from_list(["VV", "VH"]) == [VV, VH]
    assert SarBandNames.to_value_list([HV_DSPK, VV]) == ["HV_DSPK", "VV"]
    assert SarBandNames.to_value_list() == SarBandNames.list_values()
    assert SarBandNames.corresponding_speckle(SarBandNames.VV) == VV
    assert SarBandNames.corresponding_speckle(SarBandNames.VV_DSPK) == VV

    # OPTIC
    map_dic = {
        CA: "01",
        BLUE: "02",
        GREEN: "03",
        RED: "04",
        VRE_1: "05",
        VRE_2: "06",
        VRE_3: "07",
        NIR: "08",
        NARROW_NIR: "8A",
        WV: "09",
        SWIR_1: "11",
        SWIR_2: "12",
    }
    ob = OpticalBands()
    ob.map_bands(map_dic)

    for key, val in map_dic.items():
        assert key in ob._band_map
        assert ob._band_map[key] == map_dic[key]

    with pytest.raises(InvalidTypeError):
        ob.map_bands({VV: "wrong_val"})
