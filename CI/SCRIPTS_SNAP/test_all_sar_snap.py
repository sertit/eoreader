import logging
import os
import tempfile

from sertit import files

from CI.SCRIPTS.scripts_utils import CI_EOREADER_S3, dask_env, get_ci_db_dir, get_db_dir
from eoreader.bands import *
from eoreader.env_vars import DEM_PATH
from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME

# Init logger
logging.getLogger("boto3").setLevel(logging.WARNING)  # BOTO has way too much verbosity
logging.getLogger("botocore").setLevel(
    logging.WARNING
)  # BOTO has way too much verbosity
logging.getLogger("shapely").setLevel(
    logging.WARNING
)  # BOTO has way too much verbosity
logging.getLogger("fiona").setLevel(logging.WARNING)  # BOTO has way too much verbosity
logging.getLogger("rasterio").setLevel(
    logging.WARNING
)  # BOTO has way too much verbosity

READER = Reader()

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]
os.environ[DEM_PATH] = str(get_db_dir().joinpath(*MERIT_DEM_SUB_DIR_PATH))


def _test_sar(pattern, **kwargs):

    bands = [HH, VV]
    all_sar_paths = get_ci_db_dir().joinpath("all_sar")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output = tmp_dir
        # output = get_ci_db_dir().joinpath("all_sar_output")

        # DATA paths
        pattern_paths = files.get_file_in_dir(
            all_sar_paths, pattern, exact_name=True, get_list=True
        )
        for sar_path in pattern_paths:
            prod = Reader().open(sar_path)
            is_zip = "_ZIP" if prod.is_archived else ""
            prod.output = os.path.join(output, f"{prod.condensed_name}{is_zip}")

            LOGGER.info(
                "%s on drive %s (CI_EOREADER_S3: %s)",
                sar_path.name,
                sar_path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Load band
            ok_bands = [band for band in bands if prod.has_band(band)]
            prod.load(ok_bands, resolution=prod.resolution * 20)

            # Get extent
            ext = prod.extent  # noqa


@dask_env
def test_s1():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*S1*_IW*.SAFE")


@dask_env
def test_s1_zip():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*S1*_IW*.zip")


@dask_env
def test_csk():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*CSK_*")


@dask_env
def test_csg():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*CSG_*")


@dask_env
def test_tsx():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*TSX*")


@dask_env
def test_tdx():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*TDX*")


@dask_env
def test_paz():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*PAZ*")


@dask_env
def test_rs2():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*RS2_*")


@dask_env
def test_rcm():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*RCM2_*")


@dask_env
def test_iceye():
    """Function testing the correct functioning of the sar satellites"""
    _test_sar("*SLH*")
