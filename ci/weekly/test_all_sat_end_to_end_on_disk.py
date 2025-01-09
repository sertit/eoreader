"""Script testing EOReader satellites in a push routine"""

import logging
import os
import tempfile
from typing import Union

import xarray as xr
from lxml import etree
from sertit import AnyPath, path, types

from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    dask_env,
    get_ci_db_dir,
    get_db_dir,
    get_db_dir_on_disk,
    opt_path,
    reduce_verbosity,
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    F1,
    F2,
    HH,
    HH_DSPK,
    HILLSHADE,
    NARROW_NIR,
    NDVI,
    NIR,
    PAN,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SLOPE,
    SWIR_2,
    TIR_1,
    VV,
    VV_DSPK,
    Oa01,
)
from eoreader.env_vars import (
    DEM_PATH,
    S3_DB_URL_ROOT,
    SAR_DEF_PIXEL_SIZE,
    TEST_USING_S3_DB,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import S2Product, SlstrRadAdjust
from eoreader.products.product import Product, SensorType
from eoreader.reader import CheckMethod

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]
WRITE_ON_DISK = False

reduce_verbosity()


def set_dem(dem_path):
    """Set DEM"""
    if dem_path:
        dem_path = AnyPath(dem_path)
        if not dem_path.is_file():
            raise FileNotFoundError(f"Not existing DEM: {dem_path}")
        os.environ[DEM_PATH] = str(dem_path)
    else:
        if os.environ.get(TEST_USING_S3_DB) not in ("Y", "YES", "TRUE", "T", "1"):
            try:
                merit_dem = get_db_dir().joinpath(*MERIT_DEM_SUB_DIR_PATH)
                # eudem_path = os.path.join(utils.get_db_dir(), 'GLOBAL', "EUDEM_v2", "eudem_wgs84.tif")
                os.environ[DEM_PATH] = str(merit_dem)
            except NotADirectoryError as ex:
                LOGGER.debug("Non available default DEM: %s", ex)
                pass
        else:
            if S3_DB_URL_ROOT not in os.environ:
                raise Exception(
                    f"You must specify the S3 db root using env variable {S3_DB_URL_ROOT} if you activate S3_DB"
                )
            merit_dem = "/".join(
                [os.environ.get(S3_DB_URL_ROOT), *MERIT_DEM_SUB_DIR_PATH]
            )
            os.environ[DEM_PATH] = merit_dem
            LOGGER.info(
                f"Using DEM provided through Unistra S3 ({os.environ[DEM_PATH]})"
            )


def _test_core_optical(pattern: str, dem_path=None, debug=WRITE_ON_DISK, **kwargs):
    """
    Core function testing optical data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [
        PAN,
        RED,
        NARROW_NIR,
        NIR,
        Oa01,
        TIR_1,
        F1,
        F2,
        SWIR_2,
        HILLSHADE,
        CLOUDS,
        ALL_CLOUDS,
        NDVI,
    ]
    _test_core(
        pattern,
        [opt_path(), get_ci_db_dir().joinpath("more_optical")],
        possible_bands,
        dem_path,
        debug,
        **kwargs,
    )


def _test_core_sar(pattern: str, dem_path=None, debug=WRITE_ON_DISK, **kwargs):
    """
    Core function testing SAR data
    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE]
    _test_core(
        pattern,
        get_ci_db_dir().joinpath("all_sar"),
        possible_bands,
        dem_path,
        debug,
        **kwargs,
    )


def _test_core(
    pattern: str,
    prod_dirs: Union[str, list],
    possible_bands: list,
    dem_path=None,
    debug=WRITE_ON_DISK,
    **kwargs,
):
    """
    Core function testing all data
    Args:
        pattern (str): Pattern of the satellite
        prod_dirs (Union[str, list]): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    # Set DEM
    set_dem(dem_path)

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        prod_dirs = types.make_iterable(prod_dirs)

        pattern_paths = []
        for prod_dir in prod_dirs:
            try:
                pattern_paths += path.get_file_in_dir(
                    prod_dir, pattern, exact_name=True, get_list=True
                )
            except FileNotFoundError:
                continue

        for pattern_path in pattern_paths:
            LOGGER.info(
                f"%s on drive %s ({CI_EOREADER_S3}: %s)",
                pattern_path.name,
                pattern_path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Open product and set output
            LOGGER.info("Checking opening solutions")
            LOGGER.info("MTD")
            prod: Product = READER.open(
                pattern_path, method=CheckMethod.MTD, remove_tmp=not debug
            )

            # Log name
            assert prod is not None
            assert prod.name is not None
            LOGGER.info(f"Product name: {prod.name}")

            with tempfile.TemporaryDirectory() as tmp_dir:
                if WRITE_ON_DISK:
                    tmp_dir = os.path.join("/home/data/ci/e2e_satellites")
                output = tmp_dir
                is_zip = "_ZIP" if prod.is_archived else ""
                prod.output = os.path.join(output, f"{prod.condensed_name}{is_zip}")

                # Manage S3 pixel_size to speed up processes
                if prod.sensor_type == SensorType.SAR:
                    pixel_size = 1000.0
                    os.environ[SAR_DEF_PIXEL_SIZE] = str(pixel_size)
                else:
                    pixel_size = prod.pixel_size * 50

                # BAND TESTS
                LOGGER.info("Checking load and stack")
                stack_bands = [band for band in possible_bands if prod.has_band(band)]
                first_band = stack_bands[0]

                # Geometric data
                footprint = prod.footprint()  # noqa
                extent = prod.extent()  # noqa

                # Get stack bands
                # Stack data
                curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
                stack = prod.stack(
                    stack_bands,
                    pixel_size=pixel_size,
                    stack_path=curr_path,
                    clean_optical="clean",
                    **kwargs,
                )

                # Load a band with the size option
                LOGGER.info("Checking load with size keyword")
                band_arr = prod.load(  # noqa
                    first_band,
                    size=(stack.rio.width, stack.rio.height),
                    clean_optical="clean",
                    **kwargs,
                )[first_band]

                # CLOUDS: just try to load them without testing it
                LOGGER.info("Loading clouds")
                cloud_bands = [CLOUDS, ALL_CLOUDS, RAW_CLOUDS, CIRRUS, SHADOWS]
                ok_clouds = [cloud for cloud in cloud_bands if prod.has_band(cloud)]
                prod.load(ok_clouds, size=(stack.rio.width, stack.rio.height))  # noqa

                # Check if no error
                LOGGER.info("get_default_band_path")
                prod.get_default_band_path()  # noqa

                LOGGER.info("get_existing_band_paths")
                prod.get_existing_band_paths()  # noqa

                # Check if possible to load narrow nir, without checking result
                if isinstance(prod, S2Product) and not prod._processing_baseline < 4.0:
                    prod.load(NARROW_NIR)

                # CRS
                LOGGER.info("Checking CRS")
                assert prod.crs().is_projected

                # MTD
                LOGGER.info("Checking Mtd")
                mtd_xml, nmsp = prod.read_mtd()
                assert isinstance(mtd_xml, etree._Element)
                assert isinstance(nmsp, dict)

                # Clean temp
                if not debug:
                    LOGGER.info("Cleaning tmp")
                    prod.clean_tmp()
                    assert len(list(prod._tmp_process.glob("*"))) == 0


def test_s1_slc(capfd):
    @dask_env
    def test_s1_slc_core():
        """Function testing the support of Sentinel-1 constellation"""
        try:
            _test_core_sar("*S1*_IW_SLC*.SAFE")
        except RuntimeError:
            # Sometimes SNAP kills the process when out of memory: assert OK in this case
            out, err = capfd.readouterr()
            assert "90%" in out
            LOGGER.warning("SNAP killed the process!")

    test_s1_slc_core()


def test_s1_slc_zip(capfd):
    @dask_env
    def test_s1_slc_zip_core():
        """Function testing the support of Sentinel-1 constellation"""
        try:
            _test_core_sar("*S1*_IW_SLC*.zip")
        except RuntimeError:
            # Sometimes SNAP kills the process when out of memory: assert OK in this case
            out, err = capfd.readouterr()
            assert "90%" in out
            LOGGER.warning("SNAP killed the process!")

    test_s1_slc_zip_core()


@dask_env
def test_s1_slc_sm():
    """Function testing the support of Sentinel-1 constellation"""
    _test_core_sar("*S1*_S4_SLC*.SAFE")


@dask_env
def test_s1_grdh():
    """Function testing the support of Sentinel-1 constellation"""
    _test_core_sar("*S1*_IW_GRDH*.SAFE")


@dask_env
def test_s1_grdh_zip():
    """Function testing the support of Sentinel-1 constellation"""
    _test_core_sar("*S1*_IW_GRDH*.zip")


@dask_env
def test_csk():
    """Function testing the support of COSMO-Skymed constellation"""
    _test_core_sar("*CSK*")


@dask_env
def test_csg():
    """Function testing the support of COSMO-Skymed 2nd Generation constellation"""
    _test_core_sar("*CSG*")


@dask_env
def test_tsx():
    """Function testing the support of TerraSAR-X constellation"""
    _test_core_sar("*TSX*")


# Assume that tests TDX and PAZ constellations
@dask_env
def test_tdx():
    """Function testing the support of TanDEM-X constellation"""
    _test_core_sar("*TDX*")


# Assume that tests TDX and PAZ constellations
@dask_env
def test_paz():
    """Function testing the support of PAZ SAR constellation"""
    _test_core_sar("*PAZ*")


@dask_env
def test_rs2():
    """Function testing the support of RADARSAT-2 constellation"""
    _test_core_sar("*RS2_*")


@dask_env
def test_rcm():
    """Function testing the support of RADARSAT-Constellation constellation"""
    _test_core_sar("*RCM*")


@dask_env
def test_iceye():
    """Function testing the support of ICEYE constellation"""
    _test_core_sar("*SLH_*")


@dask_env
def test_saocom():
    """Function testing the support of SAOCOM constellation"""
    _test_core_sar("*SAO*")


@dask_env
def test_capella():
    """Function testing the support of CAPELLA constellation"""
    _test_core_sar("*CAPELLA*")


@dask_env
def test_s2():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*T30*")


@dask_env
def test_s2_theia():
    """Function testing the support of Sentinel-2 Theia constellation"""
    _test_core_optical("*SENTINEL2*")


@dask_env
def test_s3_olci():
    """Function testing the support of Sentinel-3 OLCI constellation"""
    # Init logger
    _test_core_optical("*S3*_OL_1_*")


@dask_env
def test_s3_slstr():
    """Function testing the support of Sentinel-3 SLSTR constellation"""
    # Init logger
    _test_core_optical("*S3*_SL_1_*", **{SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP})


@dask_env
def test_l9():
    """Function testing the support of Landsat-9 constellation"""
    # Init logger
    _test_core_optical("*LC09*")


@dask_env
def test_l8():
    """Function testing the support of Landsat-8 constellation"""
    # Init logger
    _test_core_optical("*LC08*")


@dask_env
def test_l7():
    """Function testing the support of Landsat-7 constellation"""
    _test_core_optical("*LE07*")


@dask_env
def test_l5_tm():
    """Function testing the support of Landsat-5 TM constellation"""
    _test_core_optical("*LT05*")


@dask_env
def test_l4_tm():
    """Function testing the support of Landsat-4 TM constellation"""
    _test_core_optical("*LT04*")


@dask_env
def test_l5_mss():
    """Function testing the support of Landsat-5 MSS constellation"""
    _test_core_optical("*LM05*")


@dask_env
def test_l4_mss():
    """Function testing the support of Landsat-4 MSS constellation"""
    _test_core_optical("*LM04*")


@dask_env
def test_l3_mss():
    """Function testing the support of Landsat-3 constellation"""
    _test_core_optical("*LM03*")


@dask_env
def test_l2_mss():
    """Function testing the support of Landsat-2 constellation"""
    _test_core_optical("*LM02*")


@dask_env
def test_l1_mss():
    """Function testing the support of Landsat-1 constellation"""
    _test_core_optical("*LM01*")


@dask_env
def test_hls():
    """Function testing the support of HLS constellation"""
    _test_core_optical("*HLS*")


@dask_env
def test_pla():
    """Function testing the support of PlanetScope constellation"""
    _test_core_optical("*_psscene_*")
    _test_core_optical("*_psorthotile_*")
    _test_core_optical("*202*1014*")
    _test_core_optical("*202*245e*")


@dask_env
def test_sky():
    """Function testing the support of SkySat constellation"""
    _test_core_optical("*_ssc*")
    _test_core_optical("*_skysatscene_*")


@dask_env
def test_re():
    """Function testing the support of RapidEye constellation"""
    _test_core_optical("*_RE4_*")


@dask_env
def test_pld():
    """Function testing the support of Pleiades constellation"""
    _test_core_optical("*IMG_PHR*")


@dask_env
def test_pneo():
    """Function testing the support of Pleiades-Neo constellation"""
    _test_core_optical("*IMG_*_PNEO*")


@dask_env
def test_spot4():
    """Function testing the support of SPOT-4 constellation"""
    _test_core_optical("*SP04*")


@dask_env
def test_spot5():
    """Function testing the support of SPOT-5 constellation"""
    _test_core_optical("*SP05*")
    _test_core_optical("*SPVIEW*")


@dask_env
def test_spot6():
    """Function testing the support of SPOT-6 constellation"""
    _test_core_optical("*IMG_SPOT6*")


@dask_env
def test_spot7():
    """Function testing the support of SPOT-7 constellation"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*IMG_SPOT7*", dem_path=dem_path)


@dask_env
def test_wv02_wv03():
    """Function testing the support of WorldView-2/3 constellations"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*P001_MUL*", dem_path=dem_path)


@dask_env
def test_ge01_wv04():
    """Function testing the support of GeoEye-1/WorldView-4 constellations"""
    _test_core_optical("*P001_PSH*")


@dask_env
def test_vs1():
    """Function testing the support of Vision-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*VIS1*", dem_path=dem_path)


@dask_env
def test_sv1():
    """Function testing the support of SuperView-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*0001_01*", dem_path=dem_path)


@dask_env
def test_gs2():
    """Function testing the support of GEOSAT-2 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*DE2_*", dem_path=dem_path)
    _test_core_optical("*Turkey*", dem_path=dem_path)
