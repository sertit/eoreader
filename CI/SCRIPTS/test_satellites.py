""" Script testing EOReader satellites in a push routine """
import logging
import os
import tempfile

import numpy as np
import xarray as xr
from cloudpathlib import AnyPath
from geopandas import gpd
from lxml import etree
from sertit import ci, files, logs, rasters

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

from .scripts_utils import (
    CI_EOREADER_S3,
    READER,
    assert_geom_almost_equal,
    assert_raster_almost_equal,
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


def set_dem(dem_path):
    """ Set DEM"""
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


def remove_dem_files(prod):
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


def _test_core_optical(pattern: str, dem_path=None, debug=False):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [RED, SWIR_2, HILLSHADE, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, dem_path, debug)


def _test_core_sar(pattern: str, dem_path=None, debug=False):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, sar_path(), possible_bands, dem_path, debug)


def _test_core(
    pattern: str, prod_dir: str, possible_bands: list, dem_path=None, debug=False
):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    # Set DEM
    set_dem(dem_path)

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
            prod: Product = READER.open(path, method=CheckMethod.MTD, remove_tmp=False)
            prod_name = READER.open(path, method=CheckMethod.NAME)
            prod_both = READER.open(path, method=CheckMethod.BOTH)
            assert prod is not None
            assert prod == prod_name
            assert prod == prod_both

            # Discard the case where an invalid file/directory is in the CI folder
            if prod is not None:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # tmp_dir = os.path.join("/mnt", "ds2_db3", "CI", "eoreader", "DATA", "OUTPUT")
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
                    assert isinstance(extent, gpd.GeoDataFrame)
                    extent_path = get_ci_data_dir().joinpath(
                        prod.condensed_name, f"{prod.condensed_name}_extent.geojson"
                    )
                    # Write to path if needed
                    if not extent_path.exists():
                        extent_path = os.path.join(
                            tmp_dir, f"{prod.condensed_name}_extent.geojson"
                        )
                        extent.to_file(extent_path, driver="GeoJSON")

                    try:
                        ci.assert_geom_equal(extent, extent_path)
                    except AssertionError:
                        # TODO: WHY ???
                        LOGGER.warning("Extent not equal, trying almost equal.")
                        assert_geom_almost_equal(extent, extent_path)

                    # Footprint
                    LOGGER.info("Checking footprint")
                    footprint = prod.footprint()
                    assert isinstance(footprint, gpd.GeoDataFrame)
                    footprint_path = get_ci_data_dir().joinpath(
                        prod.condensed_name, f"{prod.condensed_name}_footprint.geojson"
                    )
                    # Write to path if needed
                    if not footprint_path.exists():
                        footprint_path = os.path.join(
                            tmp_dir, f"{prod.condensed_name}_footprint.geojson"
                        )
                        footprint.to_file(footprint_path, driver="GeoJSON")

                    try:
                        ci.assert_geom_equal(footprint, footprint_path)
                    except AssertionError:
                        # Has not happened for now
                        LOGGER.warning("Footprint not equal, trying almost equal.")
                        assert_geom_almost_equal(footprint, footprint_path)

                    # Remove DEM tifs if existing
                    remove_dem_files(prod)

                    # BAND TESTS
                    LOGGER.info("Checking load and stack")
                    # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
                    stack_bands = [
                        band for band in possible_bands if prod.has_band(band)
                    ]
                    first_band = stack_bands[0]

                    # Check that band loaded 2 times gives the same results (disregarding float uncertainties)
                    band_arr1 = prod.load(first_band, resolution=res)[first_band]
                    band_arr2 = prod.load(first_band, resolution=res)[first_band]
                    np.testing.assert_array_almost_equal(band_arr1, band_arr2)
                    assert band_arr1.dtype == np.float32
                    assert band_arr2.dtype == np.float32

                    # Get stack bands
                    # Stack data
                    ci_stack = get_ci_data_dir().joinpath(
                        prod.condensed_name, f"{prod.condensed_name}_stack.tif"
                    )

                    curr_path = os.path.join(
                        tmp_dir, f"{prod.condensed_name}_stack.tif"
                    )
                    stack = prod.stack(
                        stack_bands, resolution=res, stack_path=curr_path
                    )
                    assert stack.dtype == np.float32

                    # Write to path if needed
                    if not ci_stack.exists():
                        raise FileNotFoundError(f"{ci_stack} not found !")
                        # ci_stack = curr_path

                    # Test
                    assert_raster_almost_equal(curr_path, ci_stack, decimal=4)

                    # Load a band with the size option
                    LOGGER.info("Checking load with size keyword")
                    ci_band = get_ci_data_dir().joinpath(
                        prod.condensed_name,
                        f"{prod.condensed_name}_{first_band.name}_test.tif",
                    )
                    curr_path_band = os.path.join(
                        tmp_dir, f"{prod.condensed_name}_{first_band.name}_test.tif"
                    )
                    if not ci_band.exists():
                        ci_band = curr_path_band

                    band_arr = prod.load(
                        first_band, size=(stack.rio.width, stack.rio.height)
                    )[first_band]
                    rasters.write(band_arr, curr_path_band)
                    assert_raster_almost_equal(curr_path_band, ci_band, decimal=4)

                # CRS
                LOGGER.info("Checking CRS")
                assert prod.crs().is_projected

                # MTD
                mtd_xml, nmsp = prod.read_mtd()
                assert isinstance(mtd_xml, etree._Element)
                assert isinstance(nmsp, dict)

                # Clean temp
                if not debug:
                    LOGGER.info("Cleaning tmp")
                    prod.clean_tmp()
                    assert len(list(prod._tmp_process.glob("*"))) == 0


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
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(
        ci.get_db2_path(), "BASES_DE_DONNEES", *MERIT_DEM_SUB_DIR_PATH
    )
    _test_core_optical("*IMG_SPOT7*", dem_path=dem_path)


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
