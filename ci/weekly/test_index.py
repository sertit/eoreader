"""Script testing EOReader index weekly."""

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
from eoreader.bands import (
    BAI,
    BAIM,
    BAIS2,
    EVI,
    NBR,
    NDMI,
    NDVI,
    SAVI,
    VARI,
    AWEInsh,
    AWEIsh,
    get_eoreader_indices,
)

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
        tmp_path = "/home/data/ci/indices_weekly"
    prod.output = os.path.join(tmp_path, prod.condensed_name)

    # Load every index
    spyndex_list = [
        NDVI,
        NDMI,
        NBR,
        BAI,
        AWEIsh,
        AWEInsh,
        BAIM,
        BAIS2,
        EVI,
        SAVI,
        VARI,
    ]
    LOGGER.info(f"Load selected indices (EOReader's + {spyndex_list})")
    idx_list = [
        idx for idx in spyndex_list + get_eoreader_indices() if prod.has_band(idx)
    ]
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
            decimal = 2
            max_mismatch_pct = 1
            if idx_name in ["BAI", "BAIM", "WI", "EVI", "AWEInsh", "GRI"]:
                # Not bound between -1 / 1 indices
                decimal = 0
                max_mismatch_pct = 2
            ci.assert_raster_max_mismatch(
                curr_path, ci_idx, max_mismatch_pct=max_mismatch_pct, decimal=decimal
            )
        except AssertionError as ex:
            LOGGER.debug(ex)
            failed_idx.append(idx_name)

    # Read the results
    # Do like that to check all existing indices
    if failed_idx:
        raise AssertionError(f"Failed index: {failed_idx}")
