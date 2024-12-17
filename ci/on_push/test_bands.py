"""Script testing EOReader bands"""

from ci.scripts_utils import READER, opt_path, reduce_verbosity, s3_env
from eoreader.bands import BLUE, YELLOW

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
