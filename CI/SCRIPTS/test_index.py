""" Script testing EOReader index """
import logging
import os
import tempfile

import numpy as np
from sertit import ci, rasters

from eoreader.bands.indices import get_all_indices
from eoreader.utils import EOREADER_NAME

from .scripts_utils import READER, dask_env, get_ci_data_dir, opt_path, s3_env

LOGGER = logging.getLogger(EOREADER_NAME)

RES = 2000.0  # 2000 meters

ci.reduce_verbosity()


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

        # Load every index
        LOGGER.info("Load all indices")
        idx_list = [idx for idx in get_all_indices() if prod.has_band(idx)]
        idx = prod.load(idx_list, resolution=RES)

        for idx_fct, idx_arr in idx.items():
            idx_name = idx_fct.__name__
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
            except AssertionError:
                failed_idx.append(idx_name)

        # Read the results
        # Do like that to check all existing indices
        if failed_idx:
            raise AssertionError(f"Failed index: {failed_idx}")
