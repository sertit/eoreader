"""Utils module for on_push"""

import logging
import os
import warnings
from functools import wraps
from typing import Callable

import tempenv
from rasterio.errors import NotGeoreferencedWarning
from sertit import AnyPath, ci, dask, s3, unistra
from sertit.types import AnyPathType
from sertit.unistra import get_db2_path, get_db3_path, get_geodatastore

from eoreader import EOREADER_NAME
from eoreader.env_vars import TILE_SIZE
from eoreader.reader import Reader
from eoreader.utils import use_dask

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()

CI_EOREADER_S3 = "CI_EOREADER_USE_S3"


def get_ci_dir() -> AnyPathType:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return AnyPath(__file__).parent.parent


def get_ci_db_dir() -> AnyPathType:
    """
    Get CI database directory (S3 bucket)
    Returns:
        str: CI database directory
    """
    if int(os.getenv(CI_EOREADER_S3, 0)):
        # ON S3
        unistra.define_s3_client()
        return AnyPath("s3://sertit-eoreader-ci")
    else:
        # ON DISK
        try:
            # CI
            return AnyPath(get_db3_path(), "CI", "eoreader")
        except NotADirectoryError as exc:
            # Windows
            db_path = AnyPath(r"//ds2/database03/CI/eoreader")
            if not db_path.is_dir():
                raise NotADirectoryError("Impossible to find get_ci_db_dir") from exc

            return db_path


def get_ci_data_dir() -> AnyPathType:
    """
    Get CI DATA directory (S3 bucket)
    Returns:
        str: CI DATA directory
    """
    return get_ci_db_dir().joinpath("DATA")


def get_db_dir_on_disk() -> AnyPathType:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    # ON DISK
    db_dir = AnyPath(r"//ds2/database02/BASES_DE_DONNEES")

    if not db_dir.is_dir():
        try:
            db_dir = AnyPath(get_db2_path(), "BASES_DE_DONNEES")
        except NotADirectoryError:
            db_dir = AnyPath("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not db_dir.is_dir():
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir


def get_db_dir() -> AnyPathType:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    with tempenv.TemporaryEnvironment(
        {s3.USE_S3_STORAGE: os.getenv(CI_EOREADER_S3, "0")}
    ):
        return get_geodatastore()


def dask_env(function: Callable):
    """
    Create dask-using environment
    Args:
        function (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(function)
    def dask_env_wrapper(*_args, **_kwargs):
        """S3 environment wrapper"""
        use_dask_overload = _kwargs.pop("use_dask", use_dask())

        processes = False

        os.environ[TILE_SIZE] = "auto"
        if use_dask_overload:

            def set_env():
                os.environ["CLOUDPATHLIB_FORCE_OVERWRITE_FROM_CLOUD"] = "1"

                if processes:
                    # Set that to dask workers to make process=True work on cloud
                    # Sertit-utils
                    os.environ["AWS_S3_ENDPOINT"] = os.getenv("AWS_S3_ENDPOINT")
                    os.environ["AWS_S3_AWS_ACCESS_KEY_ID"] = os.getenv(
                        "AWS_S3_AWS_ACCESS_KEY_ID"
                    )
                    os.environ["AWS_S3_AWS_SECRET_ACCESS_KEY"] = os.getenv(
                        "AWS_S3_AWS_SECRET_ACCESS_KEY"
                    )

                    # Other AWS
                    os.environ["AWS_ENDPOINT_URL"] = (
                        f"https://{os.getenv('AWS_S3_ENDPOINT')}"
                    )
                    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
                    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv(
                        "AWS_SECRET_ACCESS_KEY"
                    )

            LOGGER.info("Using Dask and creating Dask client.")
            with (
                tempenv.TemporaryEnvironment(
                    {"CLOUDPATHLIB_FORCE_OVERWRITE_FROM_CLOUD": "1"}
                ),
                dask.get_or_create_dask_client(processes=processes) as client,
            ):
                # TODO: test with process=true also
                # Update workers' env
                client.run(set_env)

                # Run fct
                function(*_args, **_kwargs)

                # Set back AWS_ENDPOINT_URL
                if processes:
                    client.run(lambda: os.environ.pop("AWS_ENDPOINT_URL"))
        else:
            LOGGER.info("**NOT** using Dask!")
            function(*_args, **_kwargs)

    return dask_env_wrapper


def opt_path():
    return get_ci_db_dir().joinpath("optical")


def sar_path():
    return get_ci_db_dir().joinpath("sar")


def others_path():
    return get_ci_db_dir().joinpath("others")


def broken_s2_path():
    return get_ci_db_dir().joinpath("broken_s2")


def s3_env(*args, **kwargs):
    # See https://developmentseed.org/titiler/advanced/performance_tuning/#recommended-configuration-for-dynamic-tiling
    # And https://gdalcubes.github.io/source/concepts/config.html#recommended-settings-for-cloud-access

    def ko_to_bytes(value):
        return int(value * 1e3)

    def mo_to_bytes(value):
        return int(value * 1e6)

    import psutil
    import rasterio

    gdal_cachemax_pct = 10
    gdal_cachemax_bytes = int(
        gdal_cachemax_pct / 100 * psutil.virtual_memory().available
    )
    LOGGER.debug(
        f"GDAL CACHEMAX[{gdal_cachemax_pct}%] = {gdal_cachemax_bytes / 1024 / 1024:.2f} Mo"
    )

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN=True,
        GDAL_CACHEMAX=gdal_cachemax_bytes,
        CPL_VSIL_CURL_CACHE_SIZE=mo_to_bytes(10),
        VSI_CACHE=True,
        VSI_CACHE_SIZE=mo_to_bytes(5),
        GDAL_HTTP_MULTIPLEX=True,
        GDAL_INGESTED_BYTES_AT_OPEN=ko_to_bytes(32),
        GDAL_HTTP_VERSION=2,
        GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
        GDAL_NUM_THREADS="ALL_CPUS",
    ):
        return unistra.s3_env(*args, use_s3_env_var=CI_EOREADER_S3, **kwargs)


def compare(to_be_checked, ref, topic):
    """
    Compare two fields
    """
    try:
        assert (
            ref == to_be_checked
        ), f"Non equal {topic}: ref ={ref} != to_be_checked={to_be_checked}"
    except AssertionError:
        assert str(to_be_checked).startswith("No") and str(to_be_checked).endswith(
            "available"
        ), f"Non equal {topic}: ref={ref} != to_be_checked={to_be_checked}"


def reduce_verbosity():
    # Ignore warning
    warnings.filterwarnings(
        "ignore", category=NotGeoreferencedWarning, module="rasterio"
    )

    # Reduce verbosity to warning
    ci.reduce_verbosity(["dicttoxml", "pyogrio"])

    # Errors
    logging.getLogger("rasterio._env").setLevel(logging.ERROR)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

    # Critical
    logging.getLogger("distributed.worker").setLevel(logging.CRITICAL)


def assert_raster_max_mismatch(
    path_1,
    path_2,
    max_mismatch_pct=0.5,
    decimal=-1,
) -> None:
    """
    Assert that two rasters are almost equal.
    (everything is equal except the transform and the arrays that are almost equal)

    Accepts an offset of :code:`1E{decimal}` on the array and a precision of 10^-9 on the transform

    Useful for pytests.

    Args:
        path_1 (AnyPathStrType): Raster 1
        path_2 (AnyPathStrType): Raster 2
        max_mismatch_pct (float): Maximum of element mismatch in %

    Example:
        >>> path = r"CI/DATA/rasters/raster.tif"
        >>> path2 = r"CI/DATA/rasters/raster_almost.tif"
        >>> assert_raster_max_mismatch(path, path2)
        >>> # Raises AssertionError if sth goes wrong
    """
    try:
        # Sertit > 1.44.4
        ci.assert_raster_max_mismatch(
            path_1, path_2, max_mismatch_pct=max_mismatch_pct, decimal=decimal
        )
    except TypeError:
        import numpy as np
        from sertit.ci import assert_meta

        try:
            import rasterio
        except ModuleNotFoundError as ex:
            raise ModuleNotFoundError(
                "Please install 'rasterio' to use assert_raster_max_mismatch."
            ) from ex

        with rasterio.open(str(path_1)) as ds_1, rasterio.open(str(path_2)) as ds_2:
            # Metadata
            assert_meta(ds_1.meta, ds_2.meta)

            # Compute the number of mismatch
            arr_1 = ds_1.read()
            arr_2 = ds_2.read()

            if decimal >= 0:
                arr_1 = np.round(arr_1, decimal)
                arr_2 = np.round(arr_2, decimal)

            diffs = np.abs(arr_1 - arr_2)
            nof_mismatch = np.count_nonzero(diffs)
            nof_elements = ds_1.count * ds_1.width * ds_1.height
            pct_mismatch = nof_mismatch / nof_elements * 100.0
            assert pct_mismatch < max_mismatch_pct, (
                f"Too many mismatches !\n"
                f"Number of mismatches: {nof_mismatch} / {nof_elements},\n"
                f"Percentage of mismatches: {pct_mismatch:0.2f}% > {max_mismatch_pct}%\n"
                f"Mean of mismatches: {np.mean(np.where(diffs != 0)):0.2f}"
            )
