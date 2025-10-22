"""Utils module for on_push"""

import logging
import os
import warnings
from functools import wraps
from typing import Callable

import tempenv
from rasterio.errors import NotGeoreferencedWarning
from sertit import AnyPath, ci, dask, s3, unistra
from sertit.types import AnyPathStrType, AnyPathType
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
        return AnyPath("s3://sertit-ci/eoreader")
    else:
        # ON DISK
        try:
            # CI
            return AnyPath(get_db3_path(), "CI", "eoreader")
        except NotADirectoryError as exc:
            raise NotADirectoryError("Impossible to find get_ci_db_dir") from exc


def get_ci_data_dir() -> AnyPathType:
    """
    Get CI DATA directory (S3 bucket)
    Returns:
        str: CI DATA directory
    """
    return get_ci_db_dir().joinpath("DATA")


def get_db_dir_on_disk() -> AnyPathType:
    """
    Get database director (on disk)

    Returns:
        str: Database directory
    """
    try:
        db_dir = AnyPath(get_db2_path(), "BASES_DE_DONNEES")
    except NotADirectoryError:
        db_dir = AnyPath("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not db_dir.is_dir():
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir


def get_db_dir() -> AnyPathType:
    """
    Get geodatabase

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

    # Defaults to 5%
    gdal_cachemax_pct = 10
    gdal_cachemax_bytes = int(
        gdal_cachemax_pct / 100 * psutil.virtual_memory().available
    )
    LOGGER.debug(
        f"GDAL CACHEMAX[{gdal_cachemax_pct}%] = {gdal_cachemax_bytes / 1024 / 1024:.2f} Mo"
    )

    def decorator(function):
        @wraps(function)
        def s3_env_wrapper(*args, **kwargs):
            with rasterio.Env(
                # Global cache size for downloads in bytes, defaults to 16 MB.
                CPL_VSIL_CURL_CACHE_SIZE=mo_to_bytes(200),
                #
                # Enable / disable per-file caching by setting to TRUE or FALSE.
                VSI_CACHE=True,
                #
                # Per-file cache size in bytes
                VSI_CACHE_SIZE=mo_to_bytes(5),
                #
                # When set to YES, this attempts to download multiple range requests in parallel, reusing the same TCP connection
                GDAL_HTTP_MULTIPLEX=True,
                #
                # Gives the number of initial bytes GDAL should read when opening a file and inspecting its metadata.
                GDAL_INGESTED_BYTES_AT_OPEN=ko_to_bytes(32),
                GDAL_HTTP_VERSION=2,
                #
                # Tells GDAL to merge consecutive range GET requests.
                GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                #
                # -- useless by experience --
                # Size of the default block cache, can be set in byte, MB, or as a percentage of available main, memory.
                # GDAL_CACHEMAX=gdal_cachemax_bytes, # => doesn't seem to improve anything, in fact slows down things a bit
                # Number of threads GDAL can use for block reads and (de)compression, set to ALL_CPUS to use all available cores.
                # GDAL_NUM_THREADS="ALL_CPUS", #  => doesn't seem to improve anything, in fact slows down things
                # Set to TRUE or EMPTY_DIR to avoid listing all files in the directory once a single file is opened (this is highly recommended).
                # GDAL_DISABLE_READDIR_ON_OPEN=True, #  => seems to have drawbacks especially for s2
            ):
                return unistra.s3_env(
                    function(*args, **kwargs), use_s3_env_var=CI_EOREADER_S3
                )

        return s3_env_wrapper

    return decorator(*args, **kwargs)


def compare(to_be_checked, ref, topic):
    """
    Compare two fields
    """
    try:
        assert ref == to_be_checked, (
            f"Non equal {topic}: ref ={ref} != to_be_checked={to_be_checked}"
        )
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


def assert_is_cog(cog_path: AnyPathStrType):
    from rio_cogeo import cog_validate

    is_valid, errors, warnings = cog_validate(cog_path)
    assert is_valid and len(warnings) == 0, f"Invalid COG! {errors}"
