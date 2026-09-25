"""Script testing EOReader bands"""

import tempenv

from ci.scripts_utils import (
    READER,
    get_ci_data_dir,
    opt_path,
    reduce_verbosity,
    s3_env,
    sar_path,
)
from eoreader.bands import BLUE, YELLOW
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER, SAR_DEF_PIXEL_SIZE

reduce_verbosity()


@s3_env
def test_bands_s3_olci():
    """Test EOReader bands for Sentinel-3 OLCI"""
    prod_path = opt_path().joinpath(
        "S3A_OL_1_EFR____20191215T105023_20191215T105323_20191216T153115_0179_052_322_2160_LN1_O_NT_002.SEN3.zip"
    )
    prod = READER.open(prod_path, remove_tmp=True)

    # Check all these bands are the same
    assert list(set(prod.to_band(["Oa07", YELLOW, "YELLOW"]))) == [YELLOW]


@s3_env
def test_bands_l8():
    """Test EOReader bands for Landsat-8"""
    prod_path = opt_path().joinpath("LC08_L1GT_023030_20200518_20200527_01_T2")
    prod = READER.open(prod_path, remove_tmp=True)

    # Check all these bands are the same
    assert list(set(prod.to_band(["BLUE", "Blue", 2, BLUE, "2"]))) == [BLUE]


@s3_env
def test_dspk_with_existing_spk(tmp_path):
    """Test loading despeckle band if already existing speckle"""
    pixel_size = 1000.0
    prod_path = sar_path().joinpath(
        "CAPELLA_C02_SS_GEC_HH_20210926061004_20210926061020"
    )
    prod = READER.open(prod_path, output_path=tmp_path, remove_tmp=True)
    with tempenv.TemporaryEnvironment(
        {
            CI_EOREADER_BAND_FOLDER: str(
                get_ci_data_dir() / (prod.condensed_name + "_dspk")
            ),
            SAR_DEF_PIXEL_SIZE: str(pixel_size),
        }
    ):
        # Just need to be sure it passes
        prod.load(["HH", "HH_DSPK"], pixel_size=pixel_size)
