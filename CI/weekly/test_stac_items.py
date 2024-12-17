"""Script testing EOReader ingestion of STAC Items"""

import logging
import os
import tempfile

import xarray as xr
from botocore.exceptions import ClientError
from rasterio.windows import Window
from sertit import s3
from tempenv import tempenv

from ci.scripts_utils import READER, compare, reduce_verbosity
from eoreader import EOREADER_NAME
from eoreader.products import Product
from eoreader.reader import Constellation

LOGGER = logging.getLogger(EOREADER_NAME)

reduce_verbosity()


def _test_core(
    url: str,
    const: Constellation,
    debug=False,
    **kwargs,
):
    """
    Core function testing all data

    Args:
        url (str): Pattern of the satellite
        prod_dir (str): Product directory
        debug (bool): Debug option
    """
    with xr.set_options(warn_for_unclosed_files=debug):
        # Open product and set output
        prod: Product = READER.open(url, remove_tmp=True)

        # Check the product is found
        assert prod is not None

        with tempfile.TemporaryDirectory() as tmp_dir:
            prod.output = tmp_dir

            # Check constellation if OK
            compare(prod.constellation.value, const.value, "constellation")

            # Load default band
            # For an unknown reason it fails on Gitlab...
            try:
                def_band = prod.get_default_band()
                band = prod.load(
                    def_band, window=Window(col_off=0, row_off=0, width=100, height=100)
                )[def_band]
                assert band.shape == (1, 100, 100)
            except ClientError as ex:
                if ex.response["Error"]["Code"] in ["NoSuchBucket", "404"]:
                    LOGGER.warning(
                        f"Impossible to access the bands for {prod.condensed_name}."
                    )
                else:
                    raise

            # TODO: more checks


def test_s2_l1c_e84():
    """Function testing the support of Sentinel-2 L1C constellation processed by E84 and linked via a STAC URL"""
    with (
        tempenv.TemporaryEnvironment(
            {
                "AWS_S3_ENDPOINT": "s3.us-west-2.amazonaws.com",
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_S3_AWS_SECRET_ACCESS_KEY"),
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_S3_AWS_ACCESS_KEY_ID"),
            }
        ),
        s3.temp_s3(requester_pays=True),
    ):
        _test_core(
            "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c/items/S2B_29SLD_20231121_0_L1C",
            Constellation.S2,
        )


def test_s2_l2a_e84():
    """Function testing the support of Sentinel-2 L2A (COG) constellation processed by E84 and linked via a STAC URL"""
    _test_core(
        "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_26SKG_20231114_0_L2A",
        Constellation.S2,
    )


def test_l9_e84():
    """Function testing the support of Landsat-9 constellation processed by E84 and linked via a STAC URL"""
    with (
        tempenv.TemporaryEnvironment(
            {
                "AWS_S3_ENDPOINT": "s3.us-west-2.amazonaws.com",
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_S3_AWS_SECRET_ACCESS_KEY"),
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_S3_AWS_ACCESS_KEY_ID"),
            }
        ),
        s3.temp_s3(requester_pays=True),
    ):
        _test_core(
            "https://earth-search.aws.element84.com/v1/collections/landsat-c2-l2/items/LC09_L2SP_095022_20231119_02_T2",
            Constellation.L9,
        )


def test_l5_mpc():
    """Function testing the support of Landsat-5 constellation processed by MPC and linked via a STAC URL"""
    _test_core(
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l1/items/LM05_L1GS_039039_20130107_02_T2",
        Constellation.L5,
    )


def test_s2_mpc():
    """Function testing the support of Sentinel-2 L2A (COG) constellation processed by MPC and linked via a STAC URL"""
    _test_core(
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2A_MSIL2A_20231120T094301_R036_T36VUP_20231120T121554",
        Constellation.S2,
    )


def test_s1_rtc_mpc():
    """Function testing the support of Sentinel-1 RTC constellation processed by MPC and linked via a STAC URL"""
    _test_core(
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/items/S1A_IW_GRDH_1SDV_20231204T045058_20231204T045116_051500_063751_rtc",
        Constellation.S1,
    )
