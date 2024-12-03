""" Script testing EOReader index """

import logging
import os
import tempfile

import numpy as np
from sertit import ci, rasters

from CI.scripts_utils import (
    READER,
    dask_env,
    get_ci_data_dir,
    opt_path,
    reduce_verbosity,
    s3_env,
)
from eoreader import EOREADER_NAME
from eoreader.bands import BAI, NBR, NDVI

LOGGER = logging.getLogger(EOREADER_NAME)

RES = 2000.0  # 2000 meters

reduce_verbosity()


@s3_env
@dask_env
def test_index():
    """Function testing the correct functioning of the indices"""
    # Load S2 products as it can load every index
    s2_path = opt_path().joinpath(
        r"S2B_MSIL2A_20200114T065229_N0213_R020_T40REQ_20200114T094749.SAFE"
    )
    prod = READER.open(s2_path)
    failed_idx = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        # tmp_dir = os.path.join("/mnt", "ds2_db3", "CI", "eoreader", "DATA", "INDEX")
        prod.output = os.path.join(tmp_dir, prod.condensed_name)
        idx_list = [NDVI, NBR, BAI]

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
                ci.assert_raster_almost_equal(curr_path, ci_idx, decimal=4)
            except AssertionError as ex:
                LOGGER.debug(ex)
                failed_idx.append(idx_name)

        # Read the results
        # Do like that to check all existing indices
        if failed_idx:
            raise AssertionError(f"Failed index: {failed_idx}")
