"""Script testing EOReader index"""

import logging
import os

import numpy as np
from sertit import ci, rasters

from ci.scripts_utils import (
    READER,
    dask_env,
    get_ci_data_dir,
    opt_path,
    reduce_verbosity,
    s3_env,
)
from eoreader import EOREADER_NAME
from eoreader.bands import NBR, NDVI, NDWI, WDRVI

LOGGER = logging.getLogger(EOREADER_NAME)

RES = 2000.0  # 2000 meters

reduce_verbosity()

WRITE_ON_DISK = False


@s3_env
@dask_env
def test_index(tmp_path):
    """Function testing the correct functioning of the indices"""
    # Load S2 products as it can load every index
    s2_path = opt_path().joinpath(
        r"S2B_MSIL2A_20200114T065229_N0213_R020_T40REQ_20200114T094749.SAFE"
    )
    prod = READER.open(s2_path, remove_tmp=True)
    failed_idx = []
    if WRITE_ON_DISK:
        tmp_path = "/home/data/ci/indices"

    prod.output = os.path.join(tmp_path, prod.condensed_name)
    idx_list = [NBR, NDVI, NDWI]

    LOGGER.info(f"Load selected indices (EOReader's + {idx_list})")
    idx = prod.load(idx_list, pixel_size=RES)

    for idx_name, idx_arr in idx.items():
        LOGGER.info("Write and compare: %s", idx_name)

        # Write on disk
        curr_path = os.path.join(prod.output, idx_name + ".tif")
        ci_idx = get_ci_data_dir().joinpath(prod.condensed_name, idx_name + ".tif")
        rasters.write(idx_arr, curr_path, dtype=np.float32)

        # Write to path if needed
        if not ci_idx.exists():
            raise FileNotFoundError(f"{ci_idx} not found !")
            # ci_idx = curr_path

        # Test
        try:
            ci.assert_raster_max_mismatch(
                curr_path, ci_idx, max_mismatch_pct=1, decimal=1
            )
        except AssertionError as ex:
            LOGGER.debug(ex)
            failed_idx.append(idx_name)

    # Read the results
    # Do like that to check all existing indices
    if failed_idx:
        raise AssertionError(f"Failed index: {failed_idx}")

    # Test parametric index: just test if this doesn't fail
    LOGGER.info("Load parametric index: WDRVI")
    prod.load(WDRVI, pixel_size=RES, alpha=1)
