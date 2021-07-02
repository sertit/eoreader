""" Utils module for scripts """
import logging
import os
import sys
from functools import wraps
from pathlib import Path
from typing import Callable, Union

import geopandas as gpd
import numpy as np
import rasterio
from cloudpathlib import AnyPath, CloudPath, S3Client

from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME
from sertit import ci

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()

AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
AWS_S3_ENDPOINT = "s3.unistra.fr"
CI_EOREADER_S3 = "CI_EOREADER_USE_S3"


def get_ci_dir() -> Union[CloudPath, Path]:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return AnyPath(__file__).parent.parent


def get_ci_db_dir() -> Union[CloudPath, Path]:
    """
    Get CI database directory (S3 bucket)
    Returns:
        str: CI database directory
    """
    if int(os.getenv(CI_EOREADER_S3, 0)):
        # ON S3
        client = S3Client(
            endpoint_url=f"https://{AWS_S3_ENDPOINT}",
            aws_access_key_id=os.getenv(AWS_ACCESS_KEY_ID),
            aws_secret_access_key=os.getenv(AWS_SECRET_ACCESS_KEY),
        )
        client.set_as_default_client()
        return AnyPath("s3://sertit-eoreader-ci")
    else:
        # ON DISK
        try:
            # CI
            return AnyPath(ci.get_db3_path(), "CI", "eoreader")
        except NotADirectoryError:
            # Windows
            path = AnyPath(r"//ds2/database03/CI/eoreader")
            if not path.is_dir():
                raise NotADirectoryError("Impossible to find get_ci_db_dir")

            return path


def get_ci_data_dir() -> Union[CloudPath, Path]:
    """
    Get CI DATA directory (S3 bucket)
    Returns:
        str: CI DATA directory
    """
    if len(os.getenv(AWS_ACCESS_KEY_ID, "")) > 0:
        return get_ci_db_dir().joinpath("DATA")
    else:
        return get_ci_dir().joinpath("DATA")


def assert_raster_almost_equal(path_1: str, path_2: str, decimal: int = 5) -> None:
    """
    Assert that two rasters are almost equal.
    (everything is equal except the transform and the arrays that are almost equal)

    Accepts an offset of `1E{decimal}` on the array and the transform

    -> Useful for pytests.

    .. code-block:: python

        >>> path = r"CI\DATA\rasters\raster.tif"
        >>> path2 = r"CI\DATA\rasters\raster_almost.tif"
        >>> assert_raster_equal(path, path2)
        >>> # Raises AssertionError if sth goes wrong

    Args:
        path_1 (str): Raster 1
        path_2 (str): Raster 2
        decimal (int): Accepted decimals
    """
    with rasterio.open(str(path_1)) as dst_1:
        with rasterio.open(str(path_2)) as dst_2:
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


def assert_geom_almost_equal(
    geom_1: gpd.GeoDataFrame, geom_2: gpd.GeoDataFrame, decimal: int = 5
) -> None:
    """
    Assert that two geometries are almost equal
    (do not check equality between geodataframe as they may differ on other fields).

    -> Useful for pytests.

    ```python
    >>> path = r"CI\DATA\vectors\aoi.geojson"
    >>> assert_geom_equal(path, path)
    >>> # Raises AssertionError if sth goes wrong
    ```

    .. WARNING::
        Only checks:
         - valid geometries
         - length of GeoDataFrame
         - CRS

    Args:
        geom_1 (gpd.GeoDataFrame): Geometry 1
        geom_2 (gpd.GeoDataFrame): Geometry 2
        decimal (int): Accepted decimals
    """
    assert len(geom_1) == len(geom_2)
    assert geom_1.crs == geom_2.crs
    for idx in range(len(geom_1)):
        if geom_1.geometry.iat[idx].is_valid and geom_2.geometry.iat[idx].is_valid:
            # If valid geometries, assert that the both are equal
            assert geom_1.geometry.iat[idx].almost_equals(
                geom_2.geometry.iat[idx], decimal=decimal
            )


def get_db_dir() -> Union[CloudPath, Path]:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    db_dir = AnyPath(r"//ds2/database02/BASES_DE_DONNEES")

    if not db_dir.is_dir():
        try:
            db_dir = AnyPath(ci.get_db2_path(), "BASES_DE_DONNEES")
        except NotADirectoryError:
            db_dir = AnyPath("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not db_dir.is_dir():
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir


def s3_env(function: Callable):
    """
    Create S3 compatible storage environment
    Args:
        function (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(function)
    def s3_env_wrapper():
        """ S3 environment wrapper """
        if os.getenv(AWS_SECRET_ACCESS_KEY) and sys.platform != "win32":
            os.environ[CI_EOREADER_S3] = "1"
            print("Using S3 files")
            with rasterio.Env(
                CPL_CURL_VERBOSE=False,
                AWS_VIRTUAL_HOSTING=False,
                AWS_S3_ENDPOINT=AWS_S3_ENDPOINT,
                GDAL_DISABLE_READDIR_ON_OPEN=False,
            ):
                function()

        else:
            os.environ[CI_EOREADER_S3] = "0"
            print("Using on disk files")
            function()

    return s3_env_wrapper


def opt_path():
    return get_ci_db_dir().joinpath("optical")


def sar_path():
    return get_ci_db_dir().joinpath("sar")
