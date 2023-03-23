""" Utils module for scripts """
import logging
import os
from functools import wraps
from pathlib import Path
from typing import Callable, Union

from cloudpathlib import AnyPath, CloudPath
from sertit import ci

from eoreader import EOREADER_NAME
from eoreader.env_vars import TILE_SIZE
from eoreader.reader import Reader
from eoreader.utils import use_dask

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()

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
        ci.define_s3_client()
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
    if len(os.getenv(ci.AWS_ACCESS_KEY_ID, "")) > 0:
        return get_ci_db_dir().joinpath("DATA")
    else:
        return get_ci_dir().joinpath("DATA")


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
        ci.define_s3_client()
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
        """S3 environment wrapper"""
        # os.environ[
        #     USE_DASK
        # ] = "0"  # For now, our CI cannot create a cluster (memory insufficient)
        # if use_dask():
        #     from dask.distributed import Client, LocalCluster
        #
        #     with LocalCluster(
        #         n_workers=4, threads_per_worker=4, processes=True
        #     ) as cluster, Client(cluster):
        #         LOGGER.info("Using DASK Local Cluster")
        #         function()
        # else:
        os.environ[TILE_SIZE] = "2048"
        if use_dask():
            LOGGER.info("Using DASK threading by chunking the data")
        else:
            LOGGER.info("No chunking will be done. Beware of memory overflow errors!")

        function()

    return dask_env_wrapper


def opt_path():
    return get_ci_db_dir().joinpath("optical")


def sar_path():
    return get_ci_db_dir().joinpath("sar")


def others_path():
    return get_ci_db_dir().joinpath("others")


def broken_s2_path():
    return get_ci_db_dir().joinpath("broken_s2")


def s3_env(function):
    return ci.s3_env(function, use_s3_env_var=CI_EOREADER_S3)
