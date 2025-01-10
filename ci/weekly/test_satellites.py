"""Script testing EOReader satellites weekly"""

import contextlib
import logging
import os
import sys
import tempfile

import numpy as np
import pytest
import xarray as xr
from lxml import etree
from rasterio.windows import Window
from sertit import ci, dask, path, rasters

from ci.on_push import test_satellites
from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    dask_env,
    get_ci_data_dir,
    get_db_dir_on_disk,
    opt_path,
    reduce_verbosity,
    s3_env,
    sar_path,
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    HH,
    HH_DSPK,
    HILLSHADE,
    NARROW_NIR,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SLOPE,
    SWIR_2,
    TIR_1,
    VV,
    VV_DSPK,
)
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import Product, S2Product, SensorType, SlstrRadAdjust
from eoreader.products.product import OrbitDirection
from eoreader.reader import Constellation

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = test_satellites.MERIT_DEM_SUB_DIR_PATH
WRITE_ON_DISK = False

reduce_verbosity()


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


def check_product_consistency(prod: Product):
    """
    Check if the products are consistent

    Args:
        prod (Product): Tested product
    """
    # Check if no error when asking band paths
    LOGGER.info("get_default_band_path")
    prod.get_default_band_path()  # noqa

    LOGGER.info("get_existing_band_paths")
    prod.get_existing_band_paths()  # noqa

    # Check if possible to load narrow nir, without checking result, for Sentinel-2 with new baseline
    if isinstance(prod, S2Product) and not prod._processing_baseline < 4.0:
        prod.load(NARROW_NIR)

    # Loading CRS and assert in UTM
    LOGGER.info("Checking CRS")
    assert prod.crs().is_projected

    # Load MTD
    LOGGER.info("Checking Mtd")
    mtd_xml, nmsp = prod.read_mtd()
    if not (
        prod.constellation == Constellation.S1 and prod.product_type.value == "RTC"
    ):
        assert isinstance(mtd_xml, etree._Element)
    else:
        assert mtd_xml is None

    assert isinstance(nmsp, dict)

    # Mean sun angle type, cloud cover...
    if prod.sensor_type == SensorType.OPTICAL:
        az, zen = prod.get_mean_sun_angles()
        assert isinstance(az, float)
        assert isinstance(zen, float)

        cc = prod.get_cloud_cover()
        assert isinstance(cc, float)

    # Orbit direction
    orbit_dir = prod.get_orbit_direction()
    assert isinstance(orbit_dir, OrbitDirection)


def check_load(prod: Product, first_band) -> None:
    """
    Check if the loading process
    Args:
        prod (Product): Tested product
        first_band: First band name
    """
    # Check loading 0 bands
    assert len(prod.load([])) == 0

    # Load with the raw process
    band_arr_raw = prod.load(
        first_band.value,
        window=Window(col_off=0, row_off=0, width=100, height=100),
        clean_optical="raw",
    )[first_band]

    # Check that band loaded 2 times gives the same results (disregarding float uncertainties)
    band_arr1 = prod.load(
        first_band,
        window=Window(col_off=0, row_off=0, width=100, height=100),
        clean_optical="nodata",
    )[first_band]
    band_arr2 = prod.load(
        first_band,
        window=Window(col_off=0, row_off=0, width=100, height=100),
    )[first_band]

    np.testing.assert_array_almost_equal(band_arr1, band_arr2)

    # Check dtypes
    ci.assert_val(band_arr_raw.dtype, np.float32, "band_arr_raw dtype")
    ci.assert_val(band_arr1.dtype, np.float32, "band_arr1 dtype")
    ci.assert_val(band_arr2.dtype, np.float32, "band_arr2 dtype")

    # Check shapes between raw and no data cleaning
    ci.assert_val(band_arr_raw.shape, band_arr1.shape, "band_arr1 shape")


def check_attrs(prod: Product, array: xr.DataArray, long_name) -> None:
    """
    Check attributes of a loaded band or stack.

    Args:
        prod (Product): Tested product
        array (xr.DataArray): Band or stack array
        long_name: Long name
    """
    return test_satellites.check_attrs(prod, array, long_name)


def check_load_size(
    prod: Product, tmp_dir: str, first_band, size: tuple, **kwargs
) -> xr.DataArray:
    """
    Check the load process with the 'size' keyword.

    Args:
        prod (Product): Tested product
        tmp_dir (str): Temporary output directory
        first_band: First band name
        size (tuple): Size as a tuple
        **kwargs: Other arguments

    Returns:
        xr.DataArray: Band array
    """
    # Load a band with the size option
    LOGGER.info("Checking load with size keyword")
    ci_band = get_ci_data_dir().joinpath(
        prod.condensed_name,
        f"{prod.condensed_name}_{first_band.name}_test.tif",
    )
    curr_path_band = os.path.join(
        tmp_dir, f"{prod.condensed_name}_{first_band.name}_test.tif"
    )

    if not ci_band.exists():
        if WRITE_ON_DISK:
            ci_band = curr_path_band
        else:
            raise FileNotFoundError(f"{ci_band} not found !")

    band_xds = prod.load(
        first_band,
        size=size,
        clean_optical="clean",
        **kwargs,
    )
    assert isinstance(band_xds, xr.Dataset)
    band_arr = band_xds[first_band]
    rasters.write(band_arr, curr_path_band)
    ci.assert_raster_almost_equal_magnitude(curr_path_band, ci_band, decimal=1)

    return band_arr


def check_band_consistency(prod: Product, band_arr: xr.DataArray, first_band) -> None:
    """
    Check if the loaded bands are consistent
    - reflectance validity
    - attributes

    Args:
        prod (Product): Tested product
        band_arr (xr.DataArray): Band array
        first_band: First band name
    """
    # Check reflectance validity
    if (
        prod.sensor_type == SensorType.OPTICAL
        and band_arr.attrs["radiometry"] == "reflectance"
    ):
        assert np.nanmax(band_arr) < 10.0
        assert np.nanpercentile(band_arr, 95) <= 1.0
        assert np.nanmin(band_arr) > -1.0
        assert np.nanpercentile(band_arr, 5) >= 0.0

    # Check attributes
    check_attrs(prod, band_arr, long_name=first_band.name)


def check_clouds(prod: Product, size: tuple) -> None:
    """
    Check if a proiduct can load its clouds without any error.
    We won't test their thematic content, just if this doesn't fails.

    TODO: Test properly the clouds

    Args:
        prod (Product): Tested product
        size (tuple): Size of the clouds
    """
    # CLOUDS: just try to load them without testing it
    LOGGER.info("Loading clouds")
    cloud_bands = [CLOUDS, ALL_CLOUDS, RAW_CLOUDS, CIRRUS, SHADOWS]
    ok_clouds = [cloud for cloud in cloud_bands if prod.has_band(cloud)]
    prod.load(ok_clouds, size=size)  # noqa


def _test_core(
    pattern: str,
    prod_dir: str,
    possible_bands: list,
    dem_path=None,
    debug=False,
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
    test_satellites.set_dem(dem_path)

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        pattern_paths = path.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for pattern_path in pattern_paths:
            core(pattern_path, possible_bands, debug, **kwargs)


@dask_env
def core(prod_path, possible_bands, debug, **kwargs):
    LOGGER.info(
        f"%s on drive %s ({CI_EOREADER_S3}: %s)",
        prod_path.name,
        prod_path.drive,
        os.getenv(CI_EOREADER_S3),
    )

    client = dask.get_client()
    if (
        prod_path.is_file()
        and os.getenv(CI_EOREADER_S3) == "1"
        and dask.get_client() is not None
    ):
        LOGGER.warning(
            f"Archived products ({prod_path.name}) cannot be used with Dask on S3, because of slowliness. Shutting down Dask client."
        )
        client.scheduler.shutdown()
        client.retire_workers()
        client.close()

        with contextlib.suppress(RuntimeError):
            client.shutdown()

    # Check products
    prod = test_satellites.check_prod(prod_path, debug)

    with tempfile.TemporaryDirectory() as tmp_dir:
        if WRITE_ON_DISK:
            tmp_dir = os.path.join("/home/data/ci/satellites")
        prod.output = tmp_dir

        # DO NOT REPROJECT BANDS (WITH GDAL / SNAP) --> WAY TOO SLOW
        os.environ[CI_EOREADER_BAND_FOLDER] = str(
            get_ci_data_dir().joinpath(prod.condensed_name)
        )

        # Get the pixel size
        pixel_size = test_satellites.get_pixel_size(prod)

        # Open product and set output
        check_product_consistency(prod)

        # Check extent and footprint
        test_satellites.check_geometry(prod, "extent", tmp_dir)
        test_satellites.check_geometry(prod, "footprint", tmp_dir)

        # Get the bands we want to stack / load
        stack_bands = [band for band in possible_bands if prod.has_band(band)]
        first_band = stack_bands[0]

        # Check that band loaded 2 times gives the same results (disregarding float uncertainties)
        check_load(prod, first_band)

        # Check stack
        stack = test_satellites.check_stack(
            prod, tmp_dir, stack_bands, first_band, pixel_size, **kwargs
        )

        # Check load with size keyword
        band_arr = check_load_size(
            prod,
            tmp_dir,
            first_band,
            size=(stack.rio.width, stack.rio.height),
            **kwargs,
        )
        check_band_consistency(prod, band_arr, first_band)

        # Check clouds
        check_clouds(prod, size=(stack.rio.width, stack.rio.height))

        # Check quicklook and plot
        test_satellites.check_plot(prod)

        # Clean temp
        if not WRITE_ON_DISK:
            test_satellites.check_clean(prod)

    if not WRITE_ON_DISK:
        prod.clear()


@s3_env
def test_s2_after_04_00():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*_N7*")


@s3_env
def test_s2_before_04_00():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*_N02*")


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
