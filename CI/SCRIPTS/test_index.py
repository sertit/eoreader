""" Script testing EOReader index """
import os
import logging

from sertit import files, rasters, ci

from eoreader.utils import EOREADER_NAME
from eoreader.bands.index import get_all_index

from CI.SCRIPTS.scripts_utils import OPT_PATH, READER, get_ci_dir, get_ci_data_dir

LOGGER = logging.getLogger(EOREADER_NAME)

OUTPUT = os.path.join(get_ci_dir(), "OUTPUT")
if os.path.isdir(OUTPUT):
    files.remove(OUTPUT)

RES = 2000. # 400 meters

def test_index():
    """ Function testing the correct functioning of the index """
    # Load S2 products as it can load every index
    s2_path = os.path.join(OPT_PATH, r"S2B_MSIL2A_20200114T065229_N0213_R020_T40REQ_20200114T094749.SAFE")
    prod = READER.open(s2_path)
    prod.output = os.path.join(OUTPUT, prod.condensed_name)


    # Load every index
    LOGGER.info("Load all index")
    idx, meta = prod.load(get_all_index(), resolution=RES)

    for idx_fct, idx_arr in idx.items():
        idx_name = idx_fct.__name__
        LOGGER.info("Write and compare: %s", idx_name)

        # Write on disk
        curr_path = os.path.join(prod.output, idx_name + ".tif")
        ci_data = os.path.join(get_ci_data_dir(), prod.condensed_name, idx_name + ".tif")
        rasters.write(idx_arr, curr_path, meta)

        # Test
        ci.assert_raster_equal(curr_path, ci_data)

