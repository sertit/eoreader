""" Script testing EOReader satellites in a push routine """
import glob
import logging
import os
import tempfile

from sertit import logs, files, ci

from .scripts_utils import OPT_PATH, SAR_PATH, READER, get_ci_data_dir
from eoreader.bands.alias import *
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.env_vars import S3_DEF_RES, SAR_DEF_RES
from eoreader.products.sar.sar_product import SarProduct
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
RES = 1000  # 1000m


def remove_dem(prod):
    """ Remove DEM from product output """
    to_del = glob.glob(os.path.join(prod.output, "*_DEM.tif"))
    to_del += glob.glob(os.path.join(prod.output, "*_HILLSHADE.tif"))
    to_del += glob.glob(os.path.join(prod.output, "*_SLOPE.tif"))
    for to_d in to_del:
        files.remove(to_d)


def test_invalid():
    wrong_path = "dzfdzef"
    assert READER.open(wrong_path) is None
    assert READER.get_platform_id(wrong_path) == ""
    assert not READER.valid_name(wrong_path, "S2")


def test_optical():
    """ Function testing the correct functioning of the optical satellites """
    # Init logger
    logs.init_logger(LOGGER)

    # DATA paths
    opt_path = files.listdir_abspath(OPT_PATH)

    for path in opt_path:
        LOGGER.info(files.get_filename(path))

        # Open product and set output
        prod: OpticalProduct = READER.open(path)

        prod.output = os.path.join(get_ci_data_dir(), prod.condensed_name)

        # Remove DEM tifs if existing
        remove_dem(prod)

        # Get stack bands
        # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
        possible_bands = [RED, SWIR_2, NDVI, HILLSHADE]
        stack_bands = [band for band in possible_bands if prod.has_band(band)]

        # Manage S3 resolution to speed up processes
        if prod.sat_id == "S3":
            res = RES * prod.resolution / 20.
            os.environ[S3_DEF_RES] = str(res)
        else:
            res = RES

        # Stack data
        with tempfile.TemporaryDirectory() as tmp_dir:
            curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
            prod.stack(stack_bands,
                       resolution=res,
                       stack_path=curr_path)

            # Test
            ci_data = os.path.join(get_ci_data_dir(), prod.condensed_name, "stack.tif")
            ci.assert_raster_equal(curr_path, ci_data)

        # CRS
        assert prod.utm_crs().is_projected


def test_sar():
    """ Function testing the correct functioning of the SAR satellites """
    # Init logger
    logs.init_logger(LOGGER)

    # DATA paths
    sar_path = files.listdir_abspath(SAR_PATH)
    for path in sar_path:
        LOGGER.info(files.get_filename(path))

        # Open product and set output
        prod: SarProduct = READER.open(path)
        os.environ[SAR_DEF_RES] = str(RES)
        prod.output = os.path.join(get_ci_data_dir(), prod.condensed_name)

        # Remove DEM tifs if existing
        remove_dem(prod)

        # Get stack bands
        # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
        possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
        stack_bands = [band for band in possible_bands if prod.has_band(band)]

        # Stack data
        with tempfile.TemporaryDirectory() as tmp_dir:
            curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
            prod.stack(stack_bands,
                       resolution=RES,
                       stack_path=curr_path)

            # Test
            ci_data = os.path.join(get_ci_data_dir(), prod.condensed_name, "stack.tif")
            ci.assert_raster_equal(curr_path, ci_data)

        # CRS
        assert prod.utm_crs().is_projected
