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
    """Function testing the support of broken Sentinel-2 sensor"""
    res = 10.0 * 100

    # Broken MTD
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