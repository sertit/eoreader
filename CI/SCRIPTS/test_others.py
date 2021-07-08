import os
import sys

import pandas as pd
import pytest
import tempenv
import xarray as xr
from cloudpathlib import AnyPath, S3Client
from lxml import etree

from eoreader import utils
from eoreader.bands.alias import *
from eoreader.bands.bands import OpticalBands, SarBandNames
from eoreader.env_vars import DEM_PATH, S3_DB_URL_ROOT

from .scripts_utils import (
    AWS_ACCESS_KEY_ID,
    AWS_S3_ENDPOINT,
    AWS_SECRET_ACCESS_KEY,
    READER,
    get_db_dir,
    opt_path,
    s3_env,
)


@pytest.mark.xfail
def test_utils():
    root_dir = AnyPath(__file__).parent.parent.parent
    # Root directory
    src_dir = root_dir.joinpath("eoreader")
    data_dir = src_dir.joinpath("data")
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


@s3_env
def test_products():
    # Get paths
    prod1_path = opt_path().joinpath(
        "LC08_L1TP_200030_20201220_20210310_02_T1"
    )  # Newer
    prod2_path = opt_path().joinpath(
        "LM03_L1GS_033028_19820906_20180414_01_T2"
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


@pytest.mark.skipif(
    S3_DB_URL_ROOT not in os.environ or sys.platform == "win32",
    reason="S3 DB not set or Rasterio bugs with http urls",
)
def test_dems_https():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1TP_200030_20201220_20210310_02_T1")

    # Open prods
    prod = READER.open(prod_path)

    # Test two different DEM source
    dem_sub_dir_path = [
        "GLOBAL",
        "MERIT_Hydrologically_Adjusted_Elevations",
        "MERIT_DEM.vrt",
    ]
    local_path = str(get_db_dir().joinpath(*dem_sub_dir_path))
    remote_path = "/".join([os.environ.get(S3_DB_URL_ROOT, ""), *dem_sub_dir_path])

    # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
    with tempenv.TemporaryEnvironment({DEM_PATH: local_path}):  # Local DEM
        dem_local = prod.load(
            [DEM], resolution=30
        )  # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
    with tempenv.TemporaryEnvironment({DEM_PATH: remote_path}):  # Remote DEM
        dem_remote = prod.load([DEM], resolution=30)

    xr.testing.assert_equal(dem_local[DEM], dem_remote[DEM])


@s3_env
@pytest.mark.skipif(
    AWS_ACCESS_KEY_ID not in os.environ,
    reason="AWS S3 Compatible Storage IDs not set",
)
def test_dems_S3():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1TP_200030_20201220_20210310_02_T1")

    # Open prods
    prod = READER.open(prod_path)

    # Test two different DEM source
    dem_sub_dir_path = [
        "GLOBAL",
        "MERIT_Hydrologically_Adjusted_Elevations",
        "MERIT_DEM.vrt",
    ]
    local_path = str(get_db_dir().joinpath(*dem_sub_dir_path))

    # ON S3
    client = S3Client(
        endpoint_url=f"https://{AWS_S3_ENDPOINT}",
        aws_access_key_id=os.getenv(AWS_ACCESS_KEY_ID),
        aws_secret_access_key=os.getenv(AWS_SECRET_ACCESS_KEY),
    )
    client.set_as_default_client()
    s3_path = str(AnyPath("s3://sertit-geodatastore").joinpath(*dem_sub_dir_path))

    # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
    with tempenv.TemporaryEnvironment({DEM_PATH: local_path}):  # Local DEM
        dem_local = prod.load(
            [DEM], resolution=30
        )  # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
    with tempenv.TemporaryEnvironment({DEM_PATH: s3_path}):  # S3 DEM
        dem_s3 = prod.load([DEM], resolution=30)

    xr.testing.assert_equal(dem_local[DEM], dem_s3[DEM])


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
