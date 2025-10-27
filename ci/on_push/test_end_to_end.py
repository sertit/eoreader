"""Script testing EOReader satellites in an end-to-end manner."""

import logging
import os
import shutil
import sys
import tempfile

import pytest
import xarray as xr
from rasterio.enums import Resampling
from sertit import path

from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    assert_is_cog,
    dask_env,
    get_ci_db_dir,
    get_db_dir_on_disk,
    opt_path,
    reduce_verbosity,
    s3_env,
    set_dem,
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    ALL_CLOUDS,
    CLOUDS,
    F1,
    HH,
    HH_DSPK,
    HILLSHADE,
    NARROW_NIR,
    PAN,
    RED,
    SLOPE,
    SWIR_2,
    TIR_1,
    VV,
    VV_DSPK,
    Oa01,
)
from eoreader.env_vars import (
    SAR_DEF_PIXEL_SIZE,
)
from eoreader.products.product import Product, SensorType
from eoreader.reader import CheckMethod

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]

reduce_verbosity()


def _test_core_optical(pattern: str, dem_path=None, debug=False, **kwargs):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [
        PAN,
        RED,
        NARROW_NIR,
        Oa01,
        TIR_1,
        F1,
        SWIR_2,
        HILLSHADE,
        CLOUDS,
        ALL_CLOUDS,
    ]
    _test_core(pattern, opt_path(), possible_bands, dem_path, debug, **kwargs)


def _test_core_sar(pattern: str, dem_path=None, debug=False, **kwargs):
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
    prod_dir: str,
    possible_bands: list,
    dem_path=None,
    debug=False,
    **kwargs,
):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    set_dem()

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        pattern_paths = path.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

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
                # output = os.path.join(
                #     "/mnt", "ds2_db3", "CI", "eoreader", "DATA", "OUTPUT_ON_DISK_CLEAN"
                # )
                output = tmp_dir
                is_zip = "_ZIP" if prod.is_archived else ""
                prod.output = os.path.join(output, f"{prod.condensed_name}{is_zip}")

                # Manage S3 pixel_size to speed up processes
                if prod.sensor_type == SensorType.SAR:
                    pixel_size = 1000.0
                    os.environ[SAR_DEF_PIXEL_SIZE] = str(pixel_size)
                else:
                    pixel_size = prod.pixel_size * 50

                # BAND TESTS
                LOGGER.info("Checking load and stack")
                stack_bands = [band for band in possible_bands if prod.has_band(band)]
                first_band = stack_bands[0]

                # Geometric data
                footprint = prod.footprint()  # noqa
                extent = prod.extent()  # noqa

                # Get stack bands
                # Stack data
                curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
                stack = prod.stack(
                    stack_bands,
                    pixel_size=pixel_size,
                    stack_path=curr_path,
                    clean_optical="clean",
                    resamplig=Resampling.bilinear,
                    **kwargs,
                )
                assert_is_cog(curr_path)

                # Load a band with the size option
                LOGGER.info("Checking load with size keyword")
                band_arr = prod.load(  # noqa
                    first_band,
                    size=(stack.rio.width, stack.rio.height),
                    clean_optical="clean",
                    **kwargs,
                )[first_band]
            prod.clear()


# Test this only weekly now.
# @pytest.mark.skipif(
#     sys.platform == "win32",
#     reason="Not enough memory to reproject on Windows runner",
# )
# @dask_env
# def test_spot6():
#     """Function testing the support of SPOT-6 constellation"""
#     _test_core_optical("*IMG_SPOT6*")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Not enough memory to orthorectify on Windows runner",
)
@s3_env
@dask_env
def test_spot7():
    """Function testing the support of SPOT-7 constellation"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*IMG_SPOT7*", dem_path=dem_path)


@pytest.mark.skipif(
    shutil.which("gpt") is None, reason="Only works if SNAP GPT's exe can be found."
)
@s3_env
@dask_env
def test_iceye():
    """Function testing the support of ICEYE constellation"""
    _test_core_sar("*SLH_*")
