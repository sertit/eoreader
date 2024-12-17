"""Other tests."""

import os
import sys
import tempfile

import numpy as np
import pytest
import rasterio
import tempenv
import xarray as xr
from rasterio.windows import Window
from sertit import AnyPath, path, unistra

from ci.scripts_utils import (
    READER,
    dask_env,
    get_db_dir,
    get_db_dir_on_disk,
    opt_path,
    others_path,
    reduce_verbosity,
    s3_env,
    sar_path,
)
from eoreader import utils
from eoreader.bands import (
    AFRI_1_6,
    BLUE,
    CA,
    CLOUDS,
    DEM,
    GREEN,
    GREEN1,
    HH,
    HILLSHADE,
    HV,
    HV_DSPK,
    NARROW_NIR,
    NDVI,
    NIR,
    RED,
    SLOPE,
    SWIR_1,
    SWIR_2,
    VH,
    VH_DSPK,
    VRE_1,
    VRE_2,
    VRE_3,
    VV,
    VV_DSPK,
    WV,
    SarBandMap,
    SarBandNames,
    SpectralBandMap,
    is_clouds,
    is_dem,
    is_index,
    is_sat_band,
    to_band,
)
from eoreader.env_vars import DEM_PATH, S3_DB_URL_ROOT
from eoreader.exceptions import InvalidTypeError
from eoreader.products import SensorType
from eoreader.reader import Constellation

reduce_verbosity()


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
    assert not is_sat_band(NDVI)
    assert is_sat_band(HH)
    assert is_sat_band(GREEN)
    assert not is_sat_band(SLOPE)
    assert not is_sat_band(CLOUDS)

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
@dask_env
def test_products():
    # Get paths
    prod1_path = opt_path().joinpath(
        "LC08_L1GT_023030_20200518_20200527_01_T2"
    )  # Newer
    prod2_path = opt_path().joinpath(
        "LM03_L1GS_033028_19820906_20180414_01_T2"
    )  # Older

    # Open prods
    prod1 = READER.open(prod1_path, remove_tmp=True)
    prod2 = READER.open(prod2_path, remove_tmp=True)

    assert prod1 == prod1
    assert prod1 >= prod1
    assert prod1 <= prod1
    assert prod1 > prod2
    assert prod2 < prod1
    assert prod1 != prod2

    # Test bands
    assert prod1.has_band(BLUE)
    assert prod1.has_bands(BLUE)
    assert prod1.has_bands([BLUE, RED, GREEN])
    with pytest.raises(AssertionError):
        assert prod1.has_band(VV)
    with pytest.raises(AssertionError):
        assert prod1.has_bands(VV)
    with pytest.raises(AssertionError):
        assert prod1.has_bands([VV, RED, GREEN])

    # Test without a DEM set:
    old_dem = None
    if DEM_PATH in os.environ:
        old_dem = os.environ.pop(DEM_PATH)
    with pytest.raises(ValueError):
        prod1.load([DEM])
    with pytest.raises(FileNotFoundError):
        os.environ[DEM_PATH] = "fczergg"
        prod1.load([DEM])

    # Reset DEM
    if old_dem != os.environ[DEM_PATH]:
        if not old_dem:
            del os.environ[DEM_PATH]
        else:
            os.environ[DEM_PATH] = old_dem

    # Test invalid band
    with pytest.raises(InvalidTypeError):
        prod1.load("TEST")

    # Test stack as int
    with tempfile.TemporaryDirectory() as tmp_dir:
        stack_path = os.path.join(tmp_dir, "stack.tif")
        stack = prod1.stack(
            [BLUE, RED],
            window=Window(col_off=0, row_off=0, width=100, height=100),
            save_as_int=True,
            stack_path=stack_path,
        )
        with rasterio.open(stack_path) as ds:
            assert ds.dtypes[0] == "uint16"
            assert stack.dtype == "float32"

    # SAR
    sar = sar_path().joinpath("SC_124020")
    with pytest.raises(AssertionError):
        sar_prod = READER.open(sar, remove_tmp=True)
        if sar_prod.sensor_type == SensorType.SAR:
            sar_prod.load(HILLSHADE)


@s3_env
@dask_env
def test_dems():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1GT_023030_20200518_20200527_01_T2")

    dem = str(
        get_db_dir().joinpath(
            "GLOBAL",
            "EUDEM_v2",
            "eudem_wgs84.tif",
        )
    )

    # Test two different DEM source
    slope_dem = str(
        get_db_dir().joinpath(
            "GLOBAL",
            "MERIT_Hydrologically_Adjusted_Elevations",
            "MERIT_DEM.vrt",
        )
    )

    hillshade_dem = str(
        get_db_dir().joinpath(
            "GLOBAL",
            "COPDEM_30m",
            "COPDEM_30m.vrt",
        )
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Open prods
        prod = READER.open(prod_path, output_path=tmp_dir)

        with tempenv.TemporaryEnvironment({DEM_PATH: dem}):
            prod.output = os.path.join(tmp_dir, prod.condensed_name)
            prod.load(
                [DEM, SLOPE, HILLSHADE],
                size=(100, 100),
                window=Window(col_off=0, row_off=0, width=100, height=100),
                **{"slope_dem": slope_dem, "hillshade_dem": hillshade_dem},
            )

        assert next(prod.output.glob(f"**/*DEM_{path.get_filename(dem)}.vrt")).is_file()
        assert next(
            prod.output.glob(f"**/*DEM_{path.get_filename(slope_dem)}.vrt")
        ).is_file()
        assert next(
            prod.output.glob(f"**/*DEM_{path.get_filename(hillshade_dem)}.vrt")
        ).is_file()
        assert next(
            prod.output.glob(f"**/*SLOPE_{path.get_filename(slope_dem)}.tif")
        ).is_file()
        assert next(
            prod.output.glob(f"**/*HILLSHADE_{path.get_filename(hillshade_dem)}.tif")
        ).is_file()

        with pytest.raises(StopIteration):
            next(prod.output.glob(f"**/*SLOPE_{path.get_filename(hillshade_dem)}.tif"))
        with pytest.raises(StopIteration):
            next(prod.output.glob(f"**/*HILLSHADE_{path.get_filename(slope_dem)}.tif"))
        with pytest.raises(StopIteration):
            next(prod.output.glob(f"**/*HILLSHADE_{path.get_filename(dem)}.tif"))


@pytest.mark.skipif(
    S3_DB_URL_ROOT not in os.environ or sys.platform == "win32",
    reason="S3 DB not set or Rasterio bugs with http urls",
)
@s3_env
@dask_env
def test_dems_https():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1GT_023030_20200518_20200527_01_T2")

    # Open prods
    prod = READER.open(prod_path, remove_tmp=True)

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
            [DEM],
            pixel_size=30,
            window=Window(col_off=0, row_off=0, width=100, height=100),
        )  # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
    with tempenv.TemporaryEnvironment({DEM_PATH: remote_path}):  # Remote DEM
        dem_remote = prod.load(
            [DEM],
            pixel_size=30,
            window=Window(col_off=0, row_off=0, width=100, height=100),
        )

    xr.testing.assert_equal(dem_local[DEM], dem_remote[DEM])


def test_dems_S3():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1GT_023030_20200518_20200527_01_T2")

    # Open prods
    prod = READER.open(prod_path, remove_tmp=True)

    # Test two different DEM source
    dem_sub_dir_path = [
        "GLOBAL",
        "MERIT_Hydrologically_Adjusted_Elevations",
        "MERIT_DEM.vrt",
    ]
    local_path = str(get_db_dir_on_disk().joinpath(*dem_sub_dir_path))

    # ON S3
    with unistra.unistra_s3():
        s3_path = str(AnyPath("s3://sertit-geodatastore").joinpath(*dem_sub_dir_path))

        # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
        with tempenv.TemporaryEnvironment({DEM_PATH: local_path}):  # Local DEM
            dem_local = prod.load(
                [DEM],
                pixel_size=30,
                window=Window(col_off=0, row_off=0, width=100, height=100),
            )  # Loading same DEM from two different sources (one hosted locally and the other hosted on S3 compatible storage)
        with tempenv.TemporaryEnvironment({DEM_PATH: s3_path}):  # S3 DEM
            dem_s3 = prod.load(
                [DEM],
                pixel_size=30,
                window=Window(col_off=0, row_off=0, width=100, height=100),
            )

        xr.testing.assert_equal(dem_local[DEM], dem_s3[DEM])


def test_bands():
    # SAR
    assert SarBandNames.from_list(["VV", "VH"]) == [VV, VH]
    assert SarBandNames.from_list("VV") == [VV]
    assert SarBandNames.to_value_list([HV_DSPK, VV]) == ["HV_DSPK", "VV"]
    assert SarBandNames.to_value_list(["HV"]) == ["HV"]
    assert SarBandNames.to_value_list() == SarBandNames.list_values()
    assert SarBandNames.corresponding_speckle(VV) == VV
    assert SarBandNames.corresponding_speckle(VV_DSPK) == VV
    assert SarBandNames.corresponding_despeckle(HV) == HV_DSPK
    assert SarBandNames.corresponding_despeckle(HV_DSPK) == HV_DSPK

    map_dic = {VV: "VV", VH: None, HV: None, HH: None}
    sb = SarBandMap()
    sb.map_bands(map_dic)

    for key, _ in map_dic.items():
        assert key in sb._band_map
        assert sb._band_map[key].id == map_dic[key]

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
    ob = SpectralBandMap()
    ob.map_bands(map_dic)

    for key, _ in map_dic.items():
        assert key in ob._band_map
        assert ob._band_map[key].id == map_dic[key]

    with pytest.raises(InvalidTypeError):
        ob.map_bands({VV: "wrong_val"})


@s3_env
def test_reader_methods():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1GT_023030_20200518_20200527_01_T2")

    # NAME
    READER.valid_name(prod_path, Constellation.L8)
    READER.valid_name(prod_path, "L8")
    READER.valid_name(prod_path, "Landsat-8")
    READER.valid_name(prod_path, Constellation.L8.name)
    READER.valid_name(prod_path, Constellation.L8.value)

    # MTD
    READER.valid_mtd(prod_path, Constellation.L8)
    READER.valid_mtd(prod_path, "L8")
    READER.valid_mtd(prod_path, "Landsat-8")
    READER.valid_mtd(prod_path, Constellation.L8.name)
    READER.valid_mtd(prod_path, Constellation.L8.value)


@s3_env
def test_windowed_reading():
    # Get paths
    prod_path = opt_path().joinpath("LC08_L1TP_200030_20201220_20210310_02_T1.tar")
    window_path = others_path().joinpath(
        "20201220T104856_L8_200030_OLI_TIRS_window.geojson"
    )

    # Open with a window
    prod = READER.open(prod_path, remove_tmp=True)
    red_raw = prod.load(RED, window=window_path, clean_optical="raw")[RED]
    red_nodata = prod.load(RED, window=window_path, clean_optical="nodata")[RED]
    red_clean = prod.load(RED, window=window_path, clean_optical="clean")[RED]

    assert red_raw.shape == red_nodata.shape == red_clean.shape

    # The arrays should be equal (outside nodata)
    np.testing.assert_array_equal(red_raw.data, red_nodata.data)

    # The arrays shouldn't be equal (some cleaning is done)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(red_raw.data, red_clean.data)


def test_deprecation():
    """Test deprecation warning"""

    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    prod_green1 = READER.open(
        opt_stack,
        custom=True,
        sensor_type=SensorType.OPTICAL,
        pixel_size=2.0,
        band_map={GREEN1: 1, RED: 2, BLUE: 3, NIR: 4, SWIR_1: 5},
        remove_tmp=True,
    )
    window = Window(200, 500, 200, 500)

    # Check deprecation for GREEN1
    with pytest.deprecated_call():
        to_band("GREEN1")
    with pytest.deprecated_call():
        prod_green1.load("GREEN1", window=window)
    with pytest.deprecated_call():
        prod_green1.load(GREEN1, window=window)

    # Check deprecation for deprecated spectral indices
    with pytest.deprecated_call():
        prod_green1.load(AFRI_1_6, window=window)

    # Check deprecation for resolution keyword
    with pytest.deprecated_call():
        prod_green1.load(SWIR_1, resolution=2.0, window=window)


def test_constellations():
    real_const = Constellation.get_real_constellations()
    assert Constellation.SPOT45 not in real_const
    assert Constellation.MAXAR not in real_const
    assert Constellation.CUSTOM not in real_const
    assert Constellation.S2_E84 not in real_const
    assert Constellation.S2_MPC not in real_const
    assert Constellation.S2_SIN not in real_const
    assert Constellation.S1_RTC_ASF not in real_const
    assert Constellation.S1_RTC_MPC not in real_const

    assert Constellation.is_real_constellation(Constellation.S2)
    assert not Constellation.is_real_constellation(Constellation.MAXAR)
    assert not Constellation.is_real_constellation(Constellation.S1_RTC_ASF)
