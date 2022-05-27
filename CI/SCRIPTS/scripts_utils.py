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
from sertit import ci, vectors
from sertit.ci import _assert_field

from eoreader.env_vars import USE_DASK
from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME, use_dask

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
        define_s3_client()
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

    Accepts an offset of :code:`1E{decimal}` on the array and the transform

    -> Useful for pytests.

    .. code-block:: python

        >>> path = r"CI/DATA/rasters/raster.tif"
        >>> path2 = r"CI/DATA/rasters/raster_almost.tif"
        >>> assert_raster_equal(path, path2)
        >>> # Raises AssertionError if sth goes wrong

    Args:
        path_1 (str): Raster 1
        path_2 (str): Raster 2
        decimal (int): Accepted decimals
    """
    with rasterio.open(str(path_1)) as ds_1:
        with rasterio.open(str(path_2)) as ds_2:
            meta_1 = ds_1.meta
            meta_2 = ds_2.meta
            _assert_field(meta_1, meta_2, "driver")
            _assert_field(meta_1, meta_2, "dtype")
            _assert_field(meta_1, meta_2, "nodata")
            _assert_field(meta_1, meta_2, "width")
            _assert_field(meta_1, meta_2, "height")
            _assert_field(meta_1, meta_2, "count")
            _assert_field(meta_1, meta_2, "crs")
            ds_1.meta["transform"].almost_equals(ds_1.meta["transform"], precision=1e-7)
            errors = []
            for i in range(ds_1.count):

                LOGGER.info(f"Checking Band {i + 1}: {ds_1.descriptions[i]}")
                try:
                    marr_1 = ds_1.read(i + 1)
                    marr_2 = ds_2.read(i + 1)
                    np.testing.assert_array_almost_equal(
                        marr_1, marr_2, decimal=decimal
                    )
                except AssertionError:
                    text = f"Band {i + 1}: {ds_1.descriptions[i]} failed"
                    errors.append(text)
                    LOGGER.error(text, exc_info=True)

            if errors:
                raise AssertionError(errors)


def assert_geom_almost_equal(
    geom_1: Union[str, CloudPath, Path, gpd.GeoDataFrame],
    geom_2: Union[str, CloudPath, Path, gpd.GeoDataFrame],
    decimal: int = 5,
) -> None:
    """
    Assert that two geometries are almost equal
    (do not check equality between geodataframe as they may differ on other fields).

    -> Useful for pytests.

    .. code-block:: python
        >>> path = r"CI/DATA/vectors/aoi.geojson"
        >>> assert_geom_equal(path, path)
        >>> # Raises AssertionError if sth goes wrong

    .. WARNING::
        Only checks:
         - valid geometries
         - length of GeoDataFrame
         - CRS

    Args:
        geom_1 (Union[str, CloudPath, Path, gpd.GeoDataFrame]): Geometry 1
        geom_2 (Union[str, CloudPath, Path, gpd.GeoDataFrame]): Geometry 2
        decimal (int): Accepted decimals
    """
    if not isinstance(geom_1, gpd.GeoDataFrame):
        geom_1 = vectors.read(geom_1)
    if not isinstance(geom_2, gpd.GeoDataFrame):
        geom_2 = vectors.read(geom_2)

    assert len(geom_1) == len(geom_2)
    assert geom_1.crs == geom_2.crs
    for idx in range(len(geom_1)):
        if geom_1.geometry.iat[idx].is_valid and geom_2.geometry.iat[idx].is_valid:
            # If valid geometries, assert that the both are equal
            assert geom_1.geometry.iat[idx].almost_equals(
                geom_2.geometry.iat[idx], decimal=decimal
            )


def get_db_dir_on_disk() -> Union[CloudPath, Path]:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    # ON DISK
    db_dir = AnyPath(r"//ds2/database02/BASES_DE_DONNEES")

    if not db_dir.is_dir():
        try:
            db_dir = AnyPath(ci.get_db2_path(), "BASES_DE_DONNEES")
        except NotADirectoryError:
            db_dir = AnyPath("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not db_dir.is_dir():
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir


def get_db_dir() -> Union[CloudPath, Path]:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """

    if int(os.getenv(CI_EOREADER_S3, 0)):
        # ON S3
        define_s3_client()
        return AnyPath("s3://sertit-geodatastore")
    else:
        # ON DISK
        db_dir = get_db_dir_on_disk()

    return db_dir


def dask_env(function: Callable):
    """
    Create dask-using environment
    Args:
        function (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(function)
    def dask_env_wrapper():
        """ S3 environment wrapper """
        os.environ[
            USE_DASK
        ] = "0"  # For now, our CI cannot create a cluster (memory insufficient)
        if use_dask():
            from dask.distributed import Client, LocalCluster

            with LocalCluster(
                n_workers=4, threads_per_worker=4, processes=True
            ) as cluster, Client(cluster):
                LOGGER.info("Using DASK Local Cluster")
                function()
        else:
            LOGGER.info("Using DASK Threading")
            function()

    return dask_env_wrapper


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
        if (
            int(os.getenv(CI_EOREADER_S3, 1))
            and os.getenv(AWS_SECRET_ACCESS_KEY)
            and sys.platform != "win32"
        ):
            # Define S3 client for S3 paths
            define_s3_client()
            os.environ[CI_EOREADER_S3] = "1"
            LOGGER.info("Using S3 files")
            with rasterio.Env(
                CPL_CURL_VERBOSE=False,
                AWS_VIRTUAL_HOSTING=False,
                AWS_S3_ENDPOINT=AWS_S3_ENDPOINT,
                GDAL_DISABLE_READDIR_ON_OPEN=False,
            ):
                function()

        else:
            os.environ[CI_EOREADER_S3] = "0"
            LOGGER.info("Using on disk files")
            function()

    return s3_env_wrapper


def define_s3_client():
    """
    Define S3 client
    """
    # ON S3
    client = S3Client(
        endpoint_url=f"https://{AWS_S3_ENDPOINT}",
        aws_access_key_id=os.getenv(AWS_ACCESS_KEY_ID),
        aws_secret_access_key=os.getenv(AWS_SECRET_ACCESS_KEY),
    )
    client.set_as_default_client()


def opt_path():
    return get_ci_db_dir().joinpath("optical")


def sar_path():
    return get_ci_db_dir().joinpath("sar")


def others_path():
    return get_ci_db_dir().joinpath("others")


def broken_s2_path():
    return get_ci_db_dir().joinpath("broken_s2")
