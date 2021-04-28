""" Utils module for scripts """
import logging
import os

import numpy as np
import rasterio

from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME
from sertit import ci
from sertit.ci import get_db2_path

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()
try:
    # CI
    CI_PATH = os.path.join(ci.get_db3_path(), "CI", "eoreader")
except NotADirectoryError:
    # Windows
    CI_PATH = os.path.join(r"\\ds2", "database03", "CI", "eoreader")

OPT_PATH = os.path.join(CI_PATH, "optical")
SAR_PATH = os.path.join(CI_PATH, "sar")


def get_ci_dir() -> str:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_ci_data_dir() -> str:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return os.path.join(get_ci_dir(), "DATA")


def assert_raster_almost_equal(path_1: str, path_2: str, decimal=5) -> None:
    """
    Assert that two rasters are almost equal.
    (everything is equal except the transform and the arrays that are almost equal)

    Accepts an offset of `1E{decimal}` on the array and the transform

    -> Useful for pytests.

    ```python
    >>> path = r"CI\DATA\rasters\raster.tif"
    >>> path2 = r"CI\DATA\rasters\raster_almost.tif"
    >>> assert_raster_equal(path, path2)
    >>> # Raises AssertionError if sth goes wrong
    ```

    Args:
        path_1 (str): Raster 1
        path_2 (str): Raster 2
    """
    with rasterio.open(path_1) as dst_1:
        with rasterio.open(path_2) as dst_2:
            assert dst_1.meta["driver"] == dst_2.meta["driver"]
            assert dst_1.meta["dtype"] == dst_2.meta["dtype"]
            assert dst_1.meta["nodata"] == dst_2.meta["nodata"]
            assert dst_1.meta["width"] == dst_2.meta["width"]
            assert dst_1.meta["height"] == dst_2.meta["height"]
            assert dst_1.meta["count"] == dst_2.meta["count"]
            assert dst_1.meta["crs"] == dst_2.meta["crs"]
            dst_1.meta["transform"].almost_equals(
                dst_1.meta["transform"], precision=1e-7
            )
            for i in range(dst_1.count):

                LOGGER.info(f"Band {i + 1}: {dst_1.descriptions[i]}")
                try:
                    marr_1 = dst_1.read(i + 1, masked=True)
                    arr_1 = np.where(marr_1.mask, 0, marr_1.data)
                    arr_1 = np.where(arr_1 == 255.0, 0, arr_1)

                    marr_2 = dst_2.read(i + 1, masked=True)
                    arr_2 = np.where(marr_2.mask, 0, marr_2.data)
                    arr_2 = np.where(arr_2 == 255.0, 0, arr_2)
                    np.testing.assert_array_almost_equal(arr_1, arr_2, decimal=decimal)
                except AssertionError:
                    LOGGER.error(
                        f"Band {i + 1}: {dst_1.descriptions[i]} failed", exc_info=True
                    )


def get_db_dir() -> str:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    db_dir = os.path.join(r"\\ds2", "database02", "BASES_DE_DONNEES")

    if not os.path.isdir(db_dir):
        try:
            db_dir = os.path.join(get_db2_path(), "BASES_DE_DONNEES")
        except NotADirectoryError:
            db_dir = os.path.join("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not os.path.isdir(db_dir):
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir
