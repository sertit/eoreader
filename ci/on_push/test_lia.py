import os
import shutil

import pytest
from sertit import ci

from ci.scripts_utils import (
    READER,
    dask_env,
    get_ci_db_dir,
    others_path,
    reduce_verbosity,
    s3_env,
)
from eoreader.keywords import WRITE_LIA_KW

WRITE_ON_DISK = False


reduce_verbosity()


@pytest.mark.skipif(
    shutil.which("gpt") is None, reason="Only works if SNAP GPT's exe can be found."
)
@s3_env
@dask_env
def test_lia(tmp_path):
    """Function testing the correct loading of LIA"""

    if WRITE_ON_DISK:
        tmp_path = "/home/data/ci/lia"

    # Open SAR product
    iceye_path = next(get_ci_db_dir().joinpath("all_sar").glob("*SLH_*"))
    prod = READER.open(iceye_path, remove_tmp=not WRITE_ON_DISK)
    prod.output = os.path.join(tmp_path, prod.condensed_name)

    # Load LIA band (right now, loading another band is mandatory)
    prod.load(bands="VV", pixel_size=100, **{WRITE_LIA_KW: True})

    # Check LIA validity
    out_lia = next(prod.output.glob("tmp_*/*LIA*"))
    truth_lia = others_path() / "20210328T221613_ICEYE_VV_SL_GRD_VV_100m_LIA.tif"
    ci.assert_raster_almost_equal(out_lia, truth_lia)
