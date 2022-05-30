import logging

import pytest

from CI.SCRIPTS.scripts_utils import READER, broken_s2_path, dask_env, s3_env
from eoreader.bands import NIR, RED
from eoreader.exceptions import InvalidProductError
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@s3_env
@dask_env
def test_broken_s2():
    """Function testing the support of broken Sentinel-2 constellation"""
    res = 10.0 * 100

    # ----------- Broken MTD -----------
    broken_mtd = broken_s2_path().joinpath(
        "S2A_MSIL2A_20170331T103021_N0001_R108_T32UMV_20190508T053047.SAFE"
    )

    broken_mtd_prod = READER.open(broken_mtd)

    assert broken_mtd_prod is not None
    LOGGER.info(broken_mtd_prod)
    LOGGER.info(broken_mtd_prod.bands)

    broken_mtd_prod.load(RED, resolution=res, clean_optical="clean")
    broken_mtd_prod.load(NIR, resolution=res, clean_optical="nodata")

    # Invalid tests
    with pytest.raises(InvalidProductError):
        broken_mtd_prod.read_mtd()

    # ----------- Broken DETFOO -----------
    broken_detfoo = broken_s2_path().joinpath(
        "S2A_MSIL2A_20170331T103021_N0001_R108_T32ULU_20190508T053054.SAFE"
    )

    broken_detfoo_prod = READER.open(broken_detfoo)

    assert broken_detfoo_prod is not None
    LOGGER.info(broken_detfoo_prod)
    LOGGER.info(broken_detfoo_prod.bands)

    # Should pass with warning
    broken_detfoo_prod.footprint()

    broken_detfoo_prod.load(
        RED, resolution=res, clean_optical="clean"
    )  # Not corrupted band

    # Invalid tests
    with pytest.raises(InvalidProductError):
        broken_detfoo_prod.load(
            NIR, resolution=res, clean_optical="nodata"
        )  # Corrupted band

    # ----------- Broken MSK -----------
    broken_msk = broken_s2_path().joinpath(
        "S2B_MSIL2A_20220201T104149_N0400_R008_T31UFP_20220201T122857.SAFE"
    )
    broken_msk_prod = READER.open(broken_msk)
    broken_msk_prod.load(RED, resolution=res, clean_optical="clean")
    broken_mtd_prod.load(NIR, resolution=res, clean_optical="nodata")
