"""Script testing EOReader satellites in a push routine"""

import logging
import os
import tempfile
from pathlib import Path

import pytest
import xarray as xr
from lxml import etree
from sertit import AnyPath, path, types

from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    dask_env,
    get_ci_db_dir,
    get_db_dir,
    get_db_dir_on_disk,
    opt_path,
    reduce_verbosity,
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    F1,
    F2,
    HH,
    HH_DSPK,
    HILLSHADE,
    NARROW_NIR,
    NDVI,
    NIR,
    PAN,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SLOPE,
    SWIR_2,
    TIR_1,
    VV,
    VV_DSPK,
    Oa01,
)
from eoreader.env_vars import (
    DEM_PATH,
    S3_DB_URL_ROOT,
    SAR_DEF_PIXEL_SIZE,
    TEST_USING_S3_DB,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import S2Product, SlstrRadAdjust
from eoreader.products.product import Product, SensorType
from eoreader.reader import CheckMethod

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]
WRITE_ON_DISK = False

reduce_verbosity()


def set_dem(dem_path):
    """Set DEM"""
    if dem_path:
        dem_path = AnyPath(dem_path)
        if not dem_path.is_file():
            raise FileNotFoundError(f"Not existing DEM: {dem_path}")
        os.environ[DEM_PATH] = str(dem_path)
    else:
        if os.environ.get(TEST_USING_S3_DB) not in ("Y", "YES", "TRUE", "T", "1"):
            try:
                merit_dem = get_db_dir().joinpath(*MERIT_DEM_SUB_DIR_PATH)
                # eudem_path = os.path.join(utils.get_db_dir(), 'GLOBAL', "EUDEM_v2", "eudem_wgs84.tif")
                os.environ[DEM_PATH] = str(merit_dem)
            except NotADirectoryError as ex:
                LOGGER.debug("Non available default DEM: %s", ex)
                pass
        else:
            if S3_DB_URL_ROOT not in os.environ:
                raise Exception(
                    f"You must specify the S3 db root using env variable {S3_DB_URL_ROOT} if you activate S3_DB"
                )
            merit_dem = "/".join(
                [os.environ.get(S3_DB_URL_ROOT), *MERIT_DEM_SUB_DIR_PATH]
            )
            os.environ[DEM_PATH] = merit_dem
            LOGGER.info(
                f"Using DEM provided through Unistra S3 ({os.environ[DEM_PATH]})"
            )


def _test_core_optical(
    pattern: str, tmpdir: Path, dem_path=None, debug=WRITE_ON_DISK, **kwargs
):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [
        PAN,
        RED,
        NIR,
        Oa01,
        TIR_1,
        F1,
        F2,
        SWIR_2,
        HILLSHADE,
        CLOUDS,
        ALL_CLOUDS,
        NDVI,
    ]
    _test_core(
        pattern,
        [opt_path(), get_ci_db_dir().joinpath("more_optical")],
        possible_bands,
        tmpdir,
        dem_path,
        debug,
        **kwargs,
    )


def _test_core_sar(
    pattern: str, tmpdir: Path, dem_path=None, debug=WRITE_ON_DISK, **kwargs
):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE]
    _test_core(
        pattern,
        get_ci_db_dir().joinpath("all_sar"),
        possible_bands,
        dem_path,
        debug,
        **kwargs,
    )


def _test_core(
    pattern: str,
    prod_dirs: str | list,
    possible_bands: list,
    tmpdir: Path,
    dem_path=None,
    debug=WRITE_ON_DISK,
    **kwargs,
):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dirs (str | list): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    set_dem(dem_path)

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        prod_dirs = types.make_iterable(prod_dirs)

        pattern_paths = []
        for prod_dir in prod_dirs:
            try:
                pattern_paths += path.get_file_in_dir(
                    prod_dir, pattern, exact_name=True, get_list=True
                )
            except FileNotFoundError:
                continue

        for pattern_path in pattern_paths:
            LOGGER.info(
                f"%s on drive %s ({CI_EOREADER_S3}: %s)",
                pattern_path.name,
                pattern_path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Open product and set output
            LOGGER.info("Checking opening solutions")
            LOGGER.info("MTD")
            prod: Product = READER.open(
                pattern_path, method=CheckMethod.MTD, remove_tmp=not debug
            )

            # Log name
            assert prod is not None
            assert prod.name is not None
            LOGGER.info(f"Product name: {prod.name}")

            with tempfile.TemporaryDirectory() as tmp_dir:
                if WRITE_ON_DISK:
                    tmp_dir = os.path.join(tmpdir, prod.condensed_name)
                output = tmp_dir
                is_zip = "_ZIP" if prod.is_archived else ""
                prod.output = os.path.join(output, f"{prod.condensed_name}{is_zip}")

                # Manage S3 pixel_size to speed up processes
                if prod.sensor_type == SensorType.SAR:
                    pixel_size = 1000.0
                    os.environ[SAR_DEF_PIXEL_SIZE] = str(pixel_size)
                else:
                    pixel_size = prod.pixel_size * 50

                # Geometric data
                LOGGER.info("Checking footprint")
                footprint = prod.footprint()  # noqa

                LOGGER.info("Checking extent")
                extent = prod.extent()  # noqa

                # BAND TESTS
                LOGGER.info("Get stacking bands")
                stack_bands = [band for band in possible_bands if prod.has_band(band)]
                first_band = stack_bands[0]

                # Get stack bands
                LOGGER.info("Checking load and stack")
                # Stack data
                curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
                stack = prod.stack(
                    stack_bands,
                    pixel_size=pixel_size,
                    stack_path=curr_path,
                    clean_optical="clean",
                    **kwargs,
                )

                # Load a band with the size option
                LOGGER.info("Checking load with size keyword")
                band_arr = prod.load(  # noqa
                    first_band,
                    size=(stack.rio.width, stack.rio.height),
                    clean_optical="clean",
                    **kwargs,
                )[first_band]

                # Load a band with the size option
                # This is too heavy for CI :'(
                # LOGGER.info("Checking load with window")
                # band_arr = prod.load(  # noqa
                #     first_band,
                #     pixel_size=prod.pixel_size,
                #     window=Window(col_off=0, row_off=0, width=100, height=100),
                #     **kwargs,
                # )[first_band]

                # CLOUDS: just try to load them without testing it
                LOGGER.info("Loading clouds")
                cloud_bands = [CLOUDS, ALL_CLOUDS, RAW_CLOUDS, CIRRUS, SHADOWS]
                ok_clouds = [cloud for cloud in cloud_bands if prod.has_band(cloud)]
                prod.load(ok_clouds, size=(stack.rio.width, stack.rio.height))  # noqa

                # Check if no error
                LOGGER.info("get_default_band_path")
                prod.get_default_band_path()  # noqa

                LOGGER.info("get_existing_band_paths")
                prod.get_existing_band_paths()  # noqa

                # Check if possible to load narrow nir, without checking result
                if isinstance(prod, S2Product) and not prod._processing_baseline < 4.0:
                    prod.load(NARROW_NIR)

                # CRS
                LOGGER.info("Checking CRS")
                assert prod.crs().is_projected

                # MTD
                LOGGER.info("Checking Mtd")
                mtd_xml, nmsp = prod.read_mtd()
                assert isinstance(mtd_xml, etree._Element)
                assert isinstance(nmsp, dict)

                # Clean temp
                if not debug:
                    LOGGER.info("Cleaning tmp")
                    prod.clean_tmp()
                    assert len(list(prod._tmp_process.glob("*"))) == 0


def test_s1_slc(capfd, eoreader_tests_path):
    @dask_env
    def test_s1_slc_core():
        """Function testing the support of Sentinel-1 constellation"""
        try:
            _test_core_sar("*S1*_IW_SLC*.SAFE", tmpdir=eoreader_tests_path.tmpdir)
        except RuntimeError:
            # Sometimes SNAP kills the process when out of memory: assert OK in this case
            out, err = capfd.readouterr()
            assert "90%" in out
            LOGGER.warning("SNAP killed the process!")

    test_s1_slc_core()


def test_s1_slc_zip(capfd, eoreader_tests_path):
    @dask_env
    def test_s1_slc_zip_core():
        """Function testing the support of Sentinel-1 constellation"""
        try:
            _test_core_sar("*S1*_IW_SLC*.zip", tmpdir=eoreader_tests_path.tmpdir)
        except RuntimeError:
            # Sometimes SNAP kills the process when out of memory: assert OK in this case
            out, err = capfd.readouterr()
            assert "90%" in out
            LOGGER.warning("SNAP killed the process!")

    test_s1_slc_zip_core()


test_optical_constellations_cases = [
    pytest.param("*VENUS*", {}, id="venus"),
    pytest.param("*S2*_MSI*T30*", {}, id="s2"),
    pytest.param("*SENTINEL2*", {}, id="s2_theia"),
    pytest.param("*S3*_OL_1_*", {}, id="s3_olci"),
    pytest.param("*S3*_SL_1_*", {SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP}, id="s3_slstr"),
    pytest.param("*LC09*", {}, id="l9"),
    pytest.param("*LC08*", {}, id="l8"),
    pytest.param("*LE07*", {}, id="l7"),
    pytest.param("*LT05*", {}, id="l5_tm"),
    pytest.param("*LT04*", {}, id="l4_tm"),
    pytest.param("*LM05*", {}, id="l5_mss"),
    pytest.param("*LM04*", {}, id="l4_mss"),
    pytest.param("*LM03*", {}, id="l3_mss"),
    pytest.param("*LM02*", {}, id="l2_mss"),
    pytest.param("*LM01*", {}, id="l1_mss"),
    pytest.param("*HLS*", {}, id="hls"),
    pytest.param("*_psscene_", {}, id="pla_psscene"),
    pytest.param("*_psorthotile_*", {}, id="pla_psorthotile"),
    pytest.param("*202*1014*", {}, id="pla"),
    pytest.param("*202*245e*", {}, id="pla_2"),
    pytest.param("*ssc*", {}, id="sky"),
    pytest.param("*_skysatscene_*", {}, id="sky_skysatscene"),
    pytest.param("*_RE4_*", {}, id="re"),
    pytest.param("*IMG_PHR*", {}, id="pld"),
    pytest.param("*IMG_*_PNEO*", {}, id="pneo"),
    pytest.param("*SP04*", {}, id="spot4"),
    pytest.param("*SP05*", {}, id="spot5"),
    pytest.param("*SPVIEW*", {}, id="spot5_old"),
    pytest.param("*IMG_SPOT6*", {}, id="spot6"),
    pytest.param(
        "*IMG_SPOT7*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="spot7",
    ),
    pytest.param(
        "*055670633040_01_P001_MUL*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="wv02_wv03_mul",
    ),
    pytest.param("*P001_PSH*", {}, id="wv02_wv03_psh"),
    pytest.param("*050246698010_01_P001_MUL*", {}, id="wv_legion"),
    pytest.param(
        "*VIS1*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="vs1",
    ),
    pytest.param(
        "*0001_01*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="sv1",
    ),
    pytest.param(
        "*DE2_*L1C*",
        {},
        id="gs2_l1c",
    ),
    pytest.param(
        "*Turkey*",
        {},
        id="gs2_l1c_2",
    ),
    pytest.param(
        "*DE2_*L1B*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="gs2_l1b",
    ),
]


@dask_env
@pytest.mark.parametrize("pattern, kwargs", test_optical_constellations_cases)
def test_optical_constellations(pattern, kwargs, eoreader_tests_path):
    _test_core_optical(pattern, eoreader_tests_path.tmpdir, **kwargs)


test_sar_constellations_cases = [
    pytest.param("*S1*_S4_SLC*.SAFE", {}, id="s1_slc_sm"),
    pytest.param("*S1*_IW_GRDH*.SAFE", {}, id="s1_grdh"),
    pytest.param("*S1*_IW_GRDH*.zip", {}, id="s1_grdh_zip"),
    pytest.param("*S1*_RTC*", {}, id="s1_rtc"),
    pytest.param("*csk_*", {}, id="csk"),
    pytest.param("*CSG_*", {}, id="csg"),
    pytest.param("*TSX*", {}, id="tsx"),
    pytest.param("*PAZ*", {}, id="paz"),
    pytest.param("*TDX*", {}, id="tdx"),
    pytest.param("*RS2_*", {}, id="rs2"),
    pytest.param("*RCM*", {}, id="rcm"),
    pytest.param("*SLH_*", {}, id="iceye"),
    pytest.param("*SAO*", {}, id="saocom"),
    pytest.param("*CAPELLA*", {}, id="capella"),
    pytest.param("*UMBRA*", {}, id="umbra"),
]


@dask_env
@pytest.mark.parametrize("pattern, kwargs", test_sar_constellations_cases)
def test_sar_constellations(pattern, kwargs, eoreader_tests_path):
    _test_core_sar(pattern, eoreader_tests_path.tmpdir, **kwargs)
