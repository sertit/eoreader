""" Script testing EOReader """

import logging
import os

from sertit import logs, files, ci

from CI.SCRIPTS.scripts_utils import OPT_PATH, SAR_PATH, READER, get_ci_dir, get_ci_data_dir
from eoreader.bands.alias import *
from eoreader.products.optical.s3_product import S3_DEF_RES
from eoreader.products.sar.sar_product import SAR_DEF_RES
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
RES = 1000  # 1000m
os.environ[SAR_DEF_RES] = str(RES)
os.environ[S3_DEF_RES] = str(RES * 5)

OUTPUT = os.path.join(get_ci_dir(), "OUTPUT")
if os.path.isdir(OUTPUT):
    files.remove(OUTPUT)


def test_optical():
    """ Function testing the correct functioning of the optical satellites """
    # Init logger
    logs.init_logger(LOGGER)

    # DATA paths
    opt_path = files.listdir_abspath(OPT_PATH)

    for path in opt_path:
        LOGGER.info(files.get_filename(path))

        # Open product and set output
        prod = READER.open(path)
        prod.output = os.path.join(OUTPUT, prod.condensed_name)

        # Get stack bands
        possible_bands = [RED, SWIR_2, NDVI, HLSHD]
        stack_bands = [band for band in possible_bands if prod.has_band(band)]

        # Manage S3 resolution
        res = RES * 15 if prod.sat_id == "S3" else RES

        # Stack data
        curr_path = os.path.join(prod.output, "stack.tif")
        prod.stack(stack_bands,
                   resolution=res,
                   stack_path=curr_path)

        # Test
        ci_data = os.path.join(get_ci_data_dir(), prod.condensed_name, "stack.tif")
        ci.assert_raster_equal(curr_path, ci_data)


def test_sar():
    """ Function testing the correct functioning of the SAR satellites """
    # Init logger
    logs.init_logger(LOGGER)

    # DATA paths
    sar_path = files.listdir_abspath(SAR_PATH)
    for path in sar_path:
        LOGGER.info(files.get_filename(path))

        # Open product and set output
        prod = READER.open(path)
        prod.output = os.path.join(OUTPUT, prod.condensed_name)

        # Get stack bands
        possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HLSHD]
        stack_bands = [band for band in possible_bands if prod.has_band(band)]

        # Stack data
        curr_path = os.path.join(prod.output, "stack.tif")
        prod.stack(stack_bands,
                   resolution=RES,
                   stack_path=curr_path)

        # Test
        ci_data = os.path.join(get_ci_data_dir(), prod.condensed_name, "stack.tif")
        ci.assert_raster_equal(curr_path, ci_data)
