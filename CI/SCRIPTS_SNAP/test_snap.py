""" Script testing EOReader satellites in a push routine """
import logging
import os
import tempfile

import xarray as xr
from cloudpathlib import AnyPath
from sertit import files, logs

from CI.SCRIPTS.scripts_utils import CI_EOREADER_S3, opt_path, s3_env, sar_path
from eoreader.bands import *
from eoreader.env_vars import SAR_DEF_RES
from eoreader.products.product import Product, SensorType
from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME

READER = Reader()

LOGGER = logging.getLogger(EOREADER_NAME)


def _test_core_optical(pattern: str, debug=False):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [RED, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, debug)


def _test_core_sar(pattern: str, debug=False):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK]
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
            prod: Product = READER.open(path)

            # Discard the case where an invalid file/directory is in the CI folder
            if prod is not None:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # tmp_dir = os.path.join("/home", "data", "OUTPUT")
                    prod.output = tmp_dir

                    # Get stack bands
                    LOGGER.info("Checking load and stack")
                    # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
                    stack_bands = [
                        band for band in possible_bands if prod.has_band(band)
                    ]

                    # Manage S3 resolution to speed up processes
                    if prod.sensor_type == SensorType.SAR:
                        res = 1000.0
                        os.environ[SAR_DEF_RES] = str(res)
                    else:
                        res = prod.resolution * 50

                    # Load data (just check if SNAP runs)
                    prod.load(stack_bands, resolution=res)


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


def test_rs2():
    """Function testing the correct functioning of the optical satellites"""
    _test_core_sar("*RS2_*")
