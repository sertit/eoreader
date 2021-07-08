""" Script testing EOReader satellites in a push routine """
import logging
import os
import tempfile

import xarray as xr
from cloudpathlib import AnyPath

from eoreader.bands.alias import *
from eoreader.env_vars import (
    CI_EOREADER_BAND_FOLDER,
    DEM_PATH,
    S3_DB_URL_ROOT,
    S3_DEF_RES,
    SAR_DEF_RES,
    TEST_USING_S3_DB,
)
from eoreader.products.product import Product, SensorType
from eoreader.reader import CheckMethod, Platform
from eoreader.utils import EOREADER_NAME
from sertit import ci, files, logs, vectors

from .scripts_utils import (
    CI_EOREADER_S3,
    READER,
    assert_geom_almost_equal,
    get_ci_data_dir,
    get_db_dir,
    opt_path,
    s3_env,
    sar_path,
)

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]
if os.environ.get(TEST_USING_S3_DB) not in ("Y", "YES", "TRUE", "T"):
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
    merit_dem = "/".join([os.environ.get(S3_DB_URL_ROOT), *MERIT_DEM_SUB_DIR_PATH])
    os.environ[DEM_PATH] = merit_dem
    LOGGER.info(f"Using DEM provided through Unistra S3 ({os.environ[DEM_PATH]})")


def remove_dem(prod):
    """Remove DEM from product output"""
    to_del = [
        prod.output.joinpath(f"{prod.condensed_name}_DEM.tif"),
        prod.output.joinpath(f"{prod.condensed_name}_HILLSHADE.tif"),
        prod.output.joinpath(f"{prod.condensed_name}_SLOPE.tif"),
    ]
    for to_d in to_del:
        files.remove(to_d)


def test_invalid():
    wrong_path = "dzfdzef"
    assert READER.open(wrong_path) is None
    assert not READER.valid_name(wrong_path, "S2")


def _test_core_optical(pattern: str, debug=False):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [RED, SWIR_2, HILLSHADE, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, debug)


def _test_core_sar(pattern: str, debug=False):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, sar_path(), possible_bands, debug)


def _test_core(pattern: str, prod_dir: str, possible_bands: list, debug=False):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    with xr.set_options(warn_for_unclosed_files=debug):

        # Init logger
        logs.init_logger(LOGGER)
        logging.getLogger("boto3").setLevel(
            logging.WARNING
        )  # BOTO has way too much verbosity
        logging.getLogger("botocore").setLevel(
            logging.WARNING
        )  # BOTO has way too much verbosity

        # DATA paths
        pattern_paths = files.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for path in pattern_paths:
            # WORKAROUND
            if str(path).endswith("/"):
                path = AnyPath(str(path)[:-1])

            LOGGER.info(
                "%s on drive %s (CI_EOREADER_S3: %s)",
                path.name,
                path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Open product and set output
            prod: Product = READER.open(
                path, method=CheckMethod.MTD, remove_tmp=not debug
            )
            prod_name = READER.open(path, method=CheckMethod.NAME)
            prod_both = READER.open(path, method=CheckMethod.BOTH)
            assert prod is not None
            assert prod == prod_name
            assert prod == prod_both

            # Discard the case where an invalid file/directory is in the CI folder
            if prod is not None:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # tmp_dir = os.path.join("/opt", "project", "EOREADER_OUTPUT")
                    prod.output = tmp_dir

                    # Env var
                    if (
                        prod.platform == Platform.S3
                        or prod.sensor_type == SensorType.SAR
                    ):
                        os.environ[CI_EOREADER_BAND_FOLDER] = str(
                            get_ci_data_dir().joinpath(prod.condensed_name)
                        )
                    else:
                        if CI_EOREADER_BAND_FOLDER in os.environ:
                            os.environ.pop(CI_EOREADER_BAND_FOLDER)

                    # Manage S3 resolution to speed up processes
                    if prod.sensor_type == SensorType.SAR:
                        res = 1000.0
                        os.environ[SAR_DEF_RES] = str(res)
                    else:
                        res = prod.resolution * 50
                        os.environ[S3_DEF_RES] = str(res)

                    # Extent
                    LOGGER.info("Checking extent")
                    extent = prod.extent()
                    extent_path = get_ci_data_dir().joinpath(
                        prod.condensed_name, "extent.geojson"
                    )
                    if not extent_path.is_file():
                        os.makedirs(
                            get_ci_data_dir().joinpath(prod.condensed_name),
                            exist_ok=True,
                        )
                        extent.to_file(extent_path, driver="GeoJSON")

                    try:
                        ci.assert_geom_equal(extent, vectors.read(extent_path))
                    except AssertionError:
                        assert_geom_almost_equal(
                            extent, vectors.read(extent_path)
                        )  # TODO: WHY ???

                    # Footprint
                    LOGGER.info("Checking footprint")
                    footprint = prod.footprint()
                    footprint_path = get_ci_data_dir().joinpath(
                        prod.condensed_name, "footprint.geojson"
                    )
                    if not footprint_path.is_file():
                        footprint.to_file(footprint_path, driver="GeoJSON")

                    try:
                        ci.assert_geom_equal(footprint, vectors.read(footprint_path))
                    except AssertionError:
                        assert_geom_almost_equal(
                            footprint, vectors.read(footprint_path)
                        )  # Has not happen for now

                    # Remove DEM tifs if existing
                    remove_dem(prod)

                    # Get stack bands
                    LOGGER.info("Checking load and stack")
                    # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
                    stack_bands = [
                        band for band in possible_bands if prod.has_band(band)
                    ]

                    # Stack data
                    ci_data = get_ci_data_dir().joinpath(
                        prod.condensed_name, "stack.tif"
                    )
                    if debug or not ci_data.is_file():
                        curr_path = prod.output.joinpath(
                            prod.condensed_name, "stack.tif"
                        )
                    else:
                        curr_path = os.path.join(
                            tmp_dir, f"{prod.condensed_name}_stack.tif"
                        )
                    prod.stack(stack_bands, resolution=res, stack_path=curr_path)

                    # Test
                    ci.assert_raster_almost_equal(curr_path, ci_data, decimal=4)

                # CRS
                LOGGER.info("Checking CRS")
                assert prod.crs().is_projected


@s3_env
def test_s2():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*S2*_MSI*")


@s3_env
def test_s2_theia():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*SENTINEL2*")


@s3_env
def test_s3_olci():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("*S3*_OL_1_*")


@s3_env
def test_s3_slstr():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("*S3*_SL_1_*")


@s3_env
def test_l8():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("*LC08*")


@s3_env
def test_l7():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LE07*")


@s3_env
def test_l5_tm():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LT05*")


@s3_env
def test_l4_tm():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LT04*")


@s3_env
def test_l5_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LM05*")


@s3_env
def test_l4_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LM04*")


@s3_env
def test_l3_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LM03*")


@s3_env
def test_l2_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LM02*")


@s3_env
def test_l1_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*LM01*")


@s3_env
def test_pla():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*202*1014*")


@s3_env
def test_pld():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*IMG_PHR*")


@s3_env
def test_spot6():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*IMG_SPOT6*")


@s3_env
def test_spot7():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("*IMG_SPOT7*")


@s3_env
def test_s1():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("*S1*_IW*")


@s3_env
def test_csk():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("*csk_*")


@s3_env
def test_tsx():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("*TSX*")


@s3_env
def test_rs2():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("*RS2_*")


# TODO:
# check non existing bands
# check cloud results
