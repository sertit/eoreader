""" Script testing EOReader satellites in a push routine """
import glob
import logging
import os
import tempfile

import xarray

from eoreader.bands.alias import *
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER, S3_DEF_RES, SAR_DEF_RES
from eoreader.products.product import Product, SensorType
from eoreader.reader import CheckMethod, Platform
from eoreader.utils import EOREADER_NAME
from sertit import ci, files, logs

from .scripts_utils import OPT_PATH, READER, SAR_PATH, get_ci_data_dir

LOGGER = logging.getLogger(EOREADER_NAME)
RES = 1000  # 1000m


def remove_dem(prod):
    """Remove DEM from product output"""
    to_del = glob.glob(os.path.join(prod.output, f"{prod.condensed_name}_DEM.tif"))
    to_del += glob.glob(
        os.path.join(prod.output, f"{prod.condensed_name}_HILLSHADE.tif")
    )
    to_del += glob.glob(os.path.join(prod.output, f"{prod.condensed_name}_SLOPE.tif"))
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
    _test_core(pattern, OPT_PATH, possible_bands, debug)


def _test_core_sar(pattern: str, debug=False):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, SAR_PATH, possible_bands, debug)


def _test_core(pattern: str, prod_dir: str, possible_bands: list, debug=False):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    with xarray.set_options(warn_for_unclosed_files=False):

        # Init logger
        logs.init_logger(LOGGER)

        # DATA paths
        pattern_paths = files.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for path in pattern_paths:
            LOGGER.info(os.path.basename(path))

            # Open product and set output
            prod: Product = READER.open(path, method=CheckMethod.MTD)
            prod_name = READER.open(path, method=CheckMethod.NAME)
            prod_both = READER.open(path, method=CheckMethod.BOTH)
            assert prod is not None
            assert prod == prod_name
            assert prod == prod_both

            # Discard the case where an invalid file/directory is in the CI folder
            if prod is not None:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # tmp_dir = os.path.join(get_ci_data_dir(), "OUTPUT")
                    prod.output = tmp_dir
                    if (
                        prod.platform == Platform.S3
                        or prod.sensor_type == SensorType.SAR
                    ):
                        os.environ[CI_EOREADER_BAND_FOLDER] = os.path.join(
                            get_ci_data_dir(), prod.condensed_name
                        )
                    else:
                        if CI_EOREADER_BAND_FOLDER in os.environ:
                            os.environ.pop(CI_EOREADER_BAND_FOLDER)
                    os.environ[SAR_DEF_RES] = str(RES)

                    # Remove DEM tifs if existing
                    remove_dem(prod)

                    # Get stack bands
                    # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
                    stack_bands = [
                        band for band in possible_bands if prod.has_band(band)
                    ]

                    # Manage S3 resolution to speed up processes
                    if prod.sat_id == "S3":
                        res = RES * prod.resolution / 20.0
                        os.environ[S3_DEF_RES] = str(res)
                    else:
                        res = RES

                    # Stack data
                    ci_data = os.path.join(
                        get_ci_data_dir(), prod.condensed_name, "stack.tif"
                    )
                    if debug:
                        curr_path = os.path.join(
                            get_ci_data_dir(), prod.condensed_name, "stack.tif"
                        )
                    else:
                        curr_path = os.path.join(
                            tmp_dir, f"{prod.condensed_name}_stack.tif"
                        )
                    prod.stack(stack_bands, resolution=res, stack_path=curr_path)

                    # Test
                    ci.assert_raster_equal(curr_path, ci_data)

                # CRS
                assert prod.crs().is_projected


def test_s2():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("S2*_MSI*")


def test_s2_theia():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("SENTINEL2*")


def test_s3_olci():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("S3*_OL_1_*")


def test_s3_slstr():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("S3*_SL_1_*")


def test_l8():
    """Function testing the correct functioning of the optical satellites"""
    # Init logger
    _test_core_optical("LC08*")


def test_l7():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LE07*")


def test_l5_tm():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LT05*")


def test_l4_tm():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LT04*")


def test_l5_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LM05*")


def test_l4_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LM04*")


def test_l3_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LM03*")


def test_l2_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LM02*")


def test_l1_mss():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_optical("LM01*")


def test_s1():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("S1*_IW*")


def test_csk():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("csk_*")


def test_tsx():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("TSX*")


def test_rs2():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("RS2_*")


# TODO:
# check non existing bands
# check cloud results
