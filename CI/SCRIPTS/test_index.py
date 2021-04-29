""" Script testing EOReader index """
import logging
import os
import tempfile

import numpy as np

from eoreader.bands.index import get_all_index
from eoreader.utils import EOREADER_NAME
from sertit import ci, rasters

from .scripts_utils import OPT_PATH, READER, get_ci_data_dir

LOGGER = logging.getLogger(EOREADER_NAME)

RES = 2000.0  # 400 meters


def test_index():
    """Function testing the correct functioning of the index"""
    # Load S2 products as it can load every index
    s2_path = os.path.join(
        OPT_PATH, r"S2B_MSIL2A_20200114T065229_N0213_R020_T40REQ_20200114T094749.SAFE"
    )
    prod = READER.open(s2_path)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # tmp_dir = os.path.join(get_ci_data_dir(), "OUTPUT")
        prod.output = os.path.join(tmp_dir, prod.condensed_name)

        # Load every index
        LOGGER.info("Load all index")
        idx = prod.load(get_all_index(), resolution=RES)

        for idx_fct, idx_arr in idx.items():
            idx_name = idx_fct.__name__
            LOGGER.info("Write and compare: %s", idx_name)

            # Write on disk
            curr_path = os.path.join(prod.output, idx_name + ".tif")
            # curr_path = os.path.join(get_ci_data_dir(), prod.condensed_name, idx_name + ".tif")  # Debug
            ci_data = os.path.join(
                get_ci_data_dir(), prod.condensed_name, idx_name + ".tif"
            )
            rasters.write(idx_arr, curr_path, dtype=np.float32)

            # Test
            ci.assert_raster_almost_equal(curr_path, ci_data, decimal=4)
