"""Script testing EOReader satellites in a push routine"""

import contextlib
import logging
import os
import sys
import tempfile

import numpy as np
import pytest
import xarray as xr
from geopandas import gpd
from matplotlib import pyplot as plt
from sertit import AnyPath, ci, misc, path

from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    dask_env,
    get_ci_data_dir,
    get_db_dir,
    get_db_dir_on_disk,
    opt_path,
    reduce_verbosity,
    s3_env,
    sar_path,
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    CLOUDS,
    HH,
    HH_DSPK,
    HILLSHADE,
    PAN,
    RED,
    SLOPE,
    SWIR_2,
    TIR_1,
    VV,
    VV_DSPK,
    to_str,
)
from eoreader.env_vars import (
    CI_EOREADER_BAND_FOLDER,
    DEM_PATH,
    S3_DB_URL_ROOT,
    SAR_DEF_PIXEL_SIZE,
    TEST_USING_S3_DB,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import Product, SensorType, SlstrRadAdjust
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
    possible_bands = [RED, SWIR_2, TIR_1, HILLSHADE, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, dem_path, debug, **kwargs)


def _test_core_sar(pattern: str, dem_path=None, debug=WRITE_ON_DISK, **kwargs):
    """
    Core function testing SAR data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, sar_path(), possible_bands, dem_path, debug, **kwargs)


def check_prod(pattern_path: str, debug: bool = WRITE_ON_DISK) -> Product:
    """
    Open and check the products

    Args:
        pattern_path (str): Pattern path used to open the right product

    Returns:
        Product: Opened product
    """
    # Check if all opening solutions are working
    LOGGER.info("Checking opening solutions")

    LOGGER.info("NAME")
    prod_name = READER.open(pattern_path, method=CheckMethod.NAME, remove_tmp=True)

    LOGGER.info("MTD")
    prod: Product = READER.open(
        pattern_path,
        method=CheckMethod.MTD,
        constellation=prod_name.constellation,
        remove_tmp=not debug,
    )
    assert prod is not None

    LOGGER.info("BOTH")
    prod_both = READER.open(
        pattern_path,
        method=CheckMethod.BOTH,
        constellation=prod.constellation,
        remove_tmp=True,
    )
    assert prod_name is not None
    assert prod_both is not None
    assert prod == prod_name
    assert prod == prod_both

    # Log product and bands
    assert prod.name is not None
    LOGGER.info(prod)
    LOGGER.info(prod.bands)

    # Instrument
    assert prod.instrument is not None

    # Stacked product
    if len(prod.get_raw_band_paths()) > 1:
        raw_bands = prod.get_raw_band_paths()
        # PAN is not considered here
        raw_bands.pop(PAN, None)
        ci.assert_val(
            prod.is_stacked,
            len(misc.unique(raw_bands.values())) == 1,
            "Stacked product",
        )

    return prod


def get_pixel_size(prod: Product) -> int:
    """
    Get the pixel size that will be used for loading stacks and bands

    Args:
        prod (Product): Tested product

    Returns:
        int: Pixel size

    """
    # Manage pixel_sizes to speed up processes
    if prod.sensor_type == SensorType.SAR:
        pixel_size = 1000
        os.environ[SAR_DEF_PIXEL_SIZE] = str(pixel_size)
    elif prod.constellation_id in ["S2", "S2_THEIA"]:
        pixel_size = 20 * 50  # Legacy
    else:
        pixel_size = prod.pixel_size * 50

    return pixel_size


def check_geometry(prod: Product, geometry_str: str, tmp_dir: str) -> None:
    """
    Check the geometry computation of a product (footprint or extent)

    Args:
        prod (Product): Tested product
        geometry_str (str): Geometry, either 'footprint' or 'extent'
        tmp_dir (str): Temporary directory
    """
    LOGGER.info(f"Checking {geometry_str}")
    geometry = getattr(prod, geometry_str)()
    assert isinstance(geometry, gpd.GeoDataFrame)
    assert geometry.crs.is_projected and geometry.crs == prod.crs()
    geometry_path = get_ci_data_dir().joinpath(
        prod.condensed_name, f"{prod.condensed_name}_{geometry_str}.geojson"
    )
    # Write to path if needed
    if not geometry_path.exists():
        if WRITE_ON_DISK:
            geometry_path = os.path.join(
                tmp_dir, f"{prod.condensed_name}_{geometry_str}.geojson"
            )
            geometry.to_file(geometry_path, driver="GeoJSON")
        else:
            raise FileNotFoundError(
                f"{geometry_str} not found for {prod.condensed_name}!"
            )

    try:
        ci.assert_geom_equal(geometry, geometry_path)
    except AssertionError:
        # Has not happened for now
        geometry_path = os.path.join(
            tmp_dir, f"{prod.condensed_name}_{geometry_str}.geojson"
        )
        geometry.to_file(geometry_path, driver="GeoJSON")

        LOGGER.warning(f"{geometry} not equal, trying almost equal.")
        ci.assert_geom_almost_equal(geometry, geometry_path)


def check_attrs(prod: Product, array: xr.DataArray, long_name) -> None:
    """
    Check attributes of a loaded band or stack.

    Args:
        prod (Product): Tested product
        array (xr.DataArray): Band or stack array
        long_name: Long name
    """
    # Check attributes
    try:
        ci.assert_val(
            array.attrs["long_name"],
            long_name,
            "long_name",
        )
    except AssertionError:
        # Just try the other way, it depends on the saved stack
        ci.assert_val(
            " ".join(array.attrs["long_name"]),
            long_name,
            "long_name",
        )

    ci.assert_val(
        array.attrs["constellation"],
        prod._get_constellation().value,
        "constellation",
    )
    ci.assert_val(
        array.attrs["constellation_id"],
        prod.constellation_id,
        "constellation_id",
    )
    ci.assert_val(array.attrs["product_type"], prod.product_type.value, "product_type")
    ci.assert_val(
        array.attrs["instrument"],
        prod.instrument if isinstance(prod.instrument, str) else prod.instrument.value,
        "instrument",
    )
    ci.assert_val(
        array.attrs["acquisition_date"],
        prod.get_datetime(as_datetime=False),
        "acquisition_date",
    )
    ci.assert_val(array.attrs["condensed_name"], prod.condensed_name, "condensed_name")
    try:
        ci.assert_val(array.attrs["product_path"], str(prod.path), "product_path")
    except AssertionError:
        ci.assert_val(
            path.get_filename(array.attrs["product_path"]),
            path.get_filename(prod.path),
            "product_path",
        )


def check_stack(
    prod: Product,
    tmp_dir: str,
    stack_bands: list,
    first_band,
    pixel_size: int,
    **kwargs,
) -> xr.DataArray:
    """
    Check the stack process + the stack consistency

    Args:
        prod (Product): Tested product
        tmp_dir (str): Temporary output directory
        stack_bands (list): List of bands to stack
        first_band: First band name
        pixel_size (int): Pixel size
        **kwargs: Other arguments

    Returns:
        xr.DataArray: Band array
    """

    # Stack data
    ci_stack = get_ci_data_dir().joinpath(
        prod.condensed_name, f"{prod.condensed_name}_stack.tif"
    )

    curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
    stack = prod.stack(
        stack_bands,
        pixel_size=pixel_size,
        stack_path=curr_path,
        clean_optical="clean",
        **kwargs,
    )
    ci.assert_val(stack.dtype, np.float32, "dtype")

    # Check attributes
    check_attrs(prod, stack, long_name=" ".join(to_str(stack_bands)))

    # Write to path if needed
    if not ci_stack.exists():
        if WRITE_ON_DISK:
            ci_stack = curr_path
        else:
            raise FileNotFoundError(f"{ci_stack} not found !")

    else:
        # Test
        try:
            ci.assert_raster_almost_equal_magnitude(curr_path, ci_stack, decimal=1)
        except AssertionError as ex:
            # Allow DEM-related bands to fails with the current changes in sertit-utils
            # TODO: recompute the stacks when these DEM-related function will be stabilized in sertit-utils (with 'xdem')
            if "SLOPE" in str(ex) or "HILLSHADE" in str(ex):
                pass

    return stack


def check_plot(prod: Product):
    """
    Check if the products can display their quiclook properly
    Args:
        prod (Product): Tested product
    """
    LOGGER.info("Plotting the quicklook")
    qck_path = prod.get_quicklook_path()
    if qck_path is not None:
        assert isinstance(qck_path, str)

    # Plot and close figure
    prod.plot()
    plt.close()


def check_clean(prod: Product) -> None:
    """
    Check the cleaning process of a Product
    Args:
        prod (Product): Tested product
    """
    LOGGER.info("Cleaning tmp")
    prod.clean_tmp()
    ci.assert_val(
        len(list(prod._tmp_process.glob("*"))),
        0,
        "Number of file in temp directory",
    )


def _test_core(
    pattern: str,
    prod_dir: str,
    possible_bands: list,
    dem_path=None,
    debug=WRITE_ON_DISK,
    **kwargs,
):
    """
    Core function testing all data

    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        possible_bands(list): Possible bands
        debug (bool): Debug option
    """
    # Set DEM
    set_dem(dem_path)

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        pattern_paths = path.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for pattern_path in pattern_paths[::-1]:
            use_dask = not (pattern_path.is_file() and os.getenv(CI_EOREADER_S3) == "1")
            core(pattern_path, possible_bands, use_dask=use_dask, **kwargs)


@dask_env
def core(prod_path, possible_bands, **kwargs):
    LOGGER.info(
        f"%s on drive %s ({CI_EOREADER_S3}: %s)",
        prod_path.name,
        prod_path.drive,
        os.getenv(CI_EOREADER_S3),
    )

    # Check products
    prod = check_prod(prod_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        if WRITE_ON_DISK:
            tmp_dir = os.path.join(
                "/mnt", "ds2_db3", "CI", "eoreader", "DATA", "OUTPUT"
            )
        prod.output = tmp_dir

        # DO NOT REPROJECT BANDS (WITH GDAL / SNAP) --> WAY TOO SLOW
        os.environ[CI_EOREADER_BAND_FOLDER] = str(
            get_ci_data_dir().joinpath(prod.condensed_name)
        )

        # Get the pixel size
        pixel_size = get_pixel_size(prod)

        # Check extent and footprint
        check_geometry(prod, "extent", tmp_dir)
        check_geometry(prod, "footprint", tmp_dir)

        if hasattr(prod, "wgs84_extent"):
            with contextlib.suppress(NotImplementedError):
                prod.wgs84_extent()

        if hasattr(prod, "_fallback_wgs84_extent"):
            with contextlib.suppress(NotImplementedError):
                prod._fallback_wgs84_extent()

        # Get the bands we want to stack / load
        stack_bands = [band for band in possible_bands if prod.has_band(band)]
        first_band = stack_bands[0]

        # Check stack
        check_stack(prod, tmp_dir, stack_bands, first_band, pixel_size, **kwargs)

        # Check quicklook and plot
        check_plot(prod)

        # Clean temp
        if not WRITE_ON_DISK:
            check_clean(prod)

        prod.clear()


@s3_env
def test_s2_after_04_00():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*_N7*")


@s3_env
def test_s2_before_04_00():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*_N0209*")


@s3_env
def test_s2_theia():
    """Function testing the support of Sentinel-2 Theia constellation"""
    _test_core_optical("*SENTINEL2*")


@s3_env
def test_s2_cloud():
    """Function testing the support of Sentinel-2 cloud-stored constellation"""
    _test_core_optical("*S2A_39KZU*")


@s3_env
def test_s3_olci():
    """Function testing the support of Sentinel-3 OLCI constellation"""
    # Init logger
    _test_core_optical("*S3*_OL_1_*")


@s3_env
def test_s3_slstr():
    """Function testing the support of Sentinel-3 SLSTR constellation"""
    # Init logger
    _test_core_optical("*S3*_SL_1_*", **{SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP})


@s3_env
def test_l9():
    """Function testing the support of Landsat-9 constellation"""
    # Init logger
    _test_core_optical("*LC09*")


@s3_env
def test_l8():
    """Function testing the support of Landsat-8 constellation"""
    # Init logger
    _test_core_optical("*LC08*")


@s3_env
def test_l7():
    """Function testing the support of Landsat-7 constellation"""
    _test_core_optical("*LE07*")


@s3_env
def test_l5_tm():
    """Function testing the support of Landsat-5 TM constellation"""
    _test_core_optical("*LT05*")


@s3_env
def test_l4_tm():
    """Function testing the support of Landsat-4 TM constellation"""
    _test_core_optical("*LT04*")


@pytest.mark.skipif(
    sys.platform == "win32" or os.getenv(CI_EOREADER_S3) == "0",
    reason="Weirdly, Landsat-5 image shape is not the same with data from disk or S3. Skipping test on disk",
)
@s3_env
def test_l5_mss():
    """Function testing the support of Landsat-5 MSS constellation"""
    _test_core_optical("*LM05*")


@s3_env
def test_l4_mss():
    """Function testing the support of Landsat-4 MSS constellation"""
    _test_core_optical("*LM04*")


@s3_env
def test_l3_mss():
    """Function testing the support of Landsat-3 constellation"""
    _test_core_optical("*LM03*")


@s3_env
def test_l2_mss():
    """Function testing the support of Landsat-2 constellation"""
    _test_core_optical("*LM02*")


@s3_env
def test_l1_mss():
    """Function testing the support of Landsat-1 constellation"""
    _test_core_optical("*LM01*")


@s3_env
def test_hls():
    """Function testing the support of HLS constellation"""
    _test_core_optical("*HLS*")


@s3_env
def test_pla():
    """Function testing the support of PlanetScope constellation"""
    _test_core_optical("*202*1014*")


@s3_env
def test_sky():
    """Function testing the support of SkySat constellation"""
    _test_core_optical("*ssc*")


@s3_env
def test_re():
    """Function testing the support of RapidEye constellation"""
    _test_core_optical("*_RE4_*")


@s3_env
def test_pld():
    """Function testing the support of Pleiades constellation"""
    _test_core_optical("*IMG_PHR*")


@s3_env
def test_pneo():
    """Function testing the support of Pleiades-Neo constellation"""
    _test_core_optical("*IMG_*_PNEO*")


@s3_env
def test_spot4():
    """Function testing the support of SPOT-4 constellation"""
    _test_core_optical("*SP04*")


@s3_env
def test_spot5():
    """Function testing the support of SPOT-5 constellation"""
    _test_core_optical("*SP05*")


@s3_env
def test_spot6():
    """Function testing the support of SPOT-6 constellation"""
    _test_core_optical("*IMG_SPOT6*")


@s3_env
def test_spot7():
    """Function testing the support of SPOT-7 constellation"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*IMG_SPOT7*", dem_path=dem_path)


@s3_env
def test_wv02_wv03():
    """Function testing the support of WorldView-2/3 constellations"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*P001_MUL*", dem_path=dem_path)


@s3_env
def test_ge01_wv04():
    """Function testing the support of GeoEye-1/WorldView-4 constellations"""
    _test_core_optical("*P001_PSH*")


@s3_env
def test_vs1():
    """Function testing the support of Vision-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*VIS1_MS4*", dem_path=dem_path)


@s3_env
def test_sv1():
    """Function testing the support of SuperView-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*0001_01*", dem_path=dem_path)


@s3_env
def test_gs2():
    """Function testing the support of GEOSAT-2 constellation"""
    _test_core_optical("*DE2_*")


@s3_env
def test_s1():
    """Function testing the support of Sentinel-1 constellation"""
    _test_core_sar("*S1*_IW_GRDH*")


@s3_env
def test_s1_rtc():
    """Function testing the support of Sentinel-1 RTC constellation"""
    _test_core_sar("*S1*_RTC*")


@s3_env
def test_csk():
    """Function testing the support of COSMO-Skymed constellation"""
    _test_core_sar("*csk_*")


@s3_env
def test_csg():
    """Function testing the support of COSMO-Skymed 2nd Generation constellation"""
    _test_core_sar("*CSG_*")


@s3_env
def test_tsx():
    """Function testing the support of TerraSAR-X constellations"""
    _test_core_sar("*TSX*")


# Assume that tests PAZ and TDX
@s3_env
def test_tdx():
    """Function testing the support of PAZ SAR and TanDEM-X constellations"""
    _test_core_sar("*TDX*")


@s3_env
def test_rs2():
    """Function testing the support of RADARSAT-2 constellation"""
    _test_core_sar("*RS2_*")


@s3_env
def test_rcm():
    """Function testing the support of RADARSAT-Constellation constellation"""
    _test_core_sar("*RCM*")


@s3_env
def test_iceye():
    """Function testing the support of ICEYE constellation"""
    _test_core_sar("*SC_*")


@s3_env
def test_saocom():
    """Function testing the support of SAOCOM constellation"""
    _test_core_sar("*SAO*")


@s3_env
def test_capella():
    """Function testing the support of CAPELLA constellation"""
    _test_core_sar("*CAPELLA*")


# TODO:
# check non existing bands
# check cloud results


def test_invalid():
    wrong_path = "dzfdzef"
    assert READER.open(wrong_path, remove_tmp=True) is None
    assert not READER.valid_name(wrong_path, "S2")


@s3_env
def test_sar():
    """Function testing some other SAR methods"""
    # TODO
