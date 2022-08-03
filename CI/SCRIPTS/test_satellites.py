""" Script testing EOReader satellites in a push routine """
import logging
import os
import sys
import tempfile

import numpy as np
import pytest
import xarray as xr
from cloudpathlib import AnyPath
from geopandas import gpd
from lxml import etree
from matplotlib import pyplot as plt
from sertit import ci, files, rasters

from eoreader.bands import *
from eoreader.env_vars import (
    CI_EOREADER_BAND_FOLDER,
    DEM_PATH,
    S3_DB_URL_ROOT,
    SAR_DEF_RES,
    TEST_USING_S3_DB,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import Product, S2Product, SensorType, SlstrRadAdjust
from eoreader.products.product import OrbitDirection
from eoreader.reader import CheckMethod
from eoreader.utils import EOREADER_NAME

from .scripts_utils import (
    CI_EOREADER_S3,
    READER,
    assert_geom_almost_equal,
    assert_raster_almost_equal,
    dask_env,
    get_ci_data_dir,
    get_db_dir,
    get_db_dir_on_disk,
    opt_path,
    s3_env,
    sar_path,
)

ci.reduce_verbosity()

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]


def set_dem(dem_path):
    """ Set DEM"""
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


def _test_core_optical(pattern: str, dem_path=None, debug=False, **kwargs):
    """
    Core function testing optical data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [RED, SWIR_2, HILLSHADE, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, dem_path, debug, **kwargs)


def _test_core_sar(pattern: str, dem_path=None, debug=False, **kwargs):
    """
    Core function testing SAR data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, sar_path(), possible_bands, dem_path, debug, **kwargs)


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
    set_dem(dem_path)

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        pattern_paths = files.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for path in pattern_paths:
            LOGGER.info(
                "%s on drive %s (CI_EOREADER_S3: %s)",
                path.name,
                path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Open product and set output
            LOGGER.info("Checking opening solutions")

            LOGGER.info("NAME")
            prod_name = READER.open(path, method=CheckMethod.NAME)

            LOGGER.info("MTD")
            prod: Product = READER.open(
                path,
                method=CheckMethod.MTD,
                constellation=prod_name.constellation,
                remove_tmp=False,
            )
            assert prod is not None

            LOGGER.info("BOTH")
            prod_both = READER.open(
                path, method=CheckMethod.BOTH, constellation=prod.constellation
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

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir = os.path.join(
                    "/mnt", "ds2_db3", "CI", "eoreader", "DATA", "OUTPUT"
                )
                prod.output = tmp_dir

                os.environ[CI_EOREADER_BAND_FOLDER] = str(
                    get_ci_data_dir().joinpath(prod.condensed_name)
                )

                # Manage S3 resolution to speed up processes
                if prod.sensor_type == SensorType.SAR:
                    res = 1000.0
                    os.environ[SAR_DEF_RES] = str(res)
                elif prod.constellation_id in ["S2", "S2_THEIA"]:
                    res = 20.0 * 50  # Legacy
                else:
                    res = prod.resolution * 50

                # Extent
                LOGGER.info("Checking extent")
                extent = prod.extent()
                assert isinstance(extent, gpd.GeoDataFrame)
                assert extent.crs.is_projected and extent.crs == prod.crs()
                extent_path = get_ci_data_dir().joinpath(
                    prod.condensed_name, f"{prod.condensed_name}_extent.geojson"
                )
                # Write to path if needed
                if not extent_path.exists():
                    raise FileNotFoundError(
                        f"Extent not found for {prod.condensed_name}!"
                    )
                    # extent_path = os.path.join(
                    #     tmp_dir, f"{prod.condensed_name}_extent.geojson"
                    # )
                    # extent.to_file(extent_path, driver="GeoJSON")

                try:
                    ci.assert_geom_equal(extent, extent_path)
                except AssertionError:
                    extent_path = os.path.join(
                        tmp_dir, f"{prod.condensed_name}_extent.geojson"
                    )
                    extent.to_file(extent_path, driver="GeoJSON")

                    LOGGER.warning("Extent not equal, trying almost equal.")
                    assert_geom_almost_equal(extent, extent_path)

                # Footprint
                LOGGER.info("Checking footprint")
                footprint = prod.footprint()
                assert isinstance(footprint, gpd.GeoDataFrame)
                assert footprint.crs.is_projected and footprint.crs == prod.crs()
                footprint_path = get_ci_data_dir().joinpath(
                    prod.condensed_name, f"{prod.condensed_name}_footprint.geojson"
                )
                # Write to path if needed
                if not footprint_path.exists():
                    raise FileNotFoundError(
                        f"Footprint not found for {prod.condensed_name}!"
                    )
                    # footprint_path = os.path.join(
                    #     tmp_dir, f"{prod.condensed_name}_footprint.geojson"
                    # )
                    # footprint.to_file(footprint_path, driver="GeoJSON")

                try:
                    ci.assert_geom_equal(footprint, footprint_path)
                except AssertionError:
                    # Has not happened for now
                    footprint_path = os.path.join(
                        tmp_dir, f"{prod.condensed_name}_footprint.geojson"
                    )
                    footprint.to_file(footprint_path, driver="GeoJSON")

                    LOGGER.warning("Footprint not equal, trying almost equal.")
                    assert_geom_almost_equal(footprint, footprint_path)

                # BAND TESTS
                LOGGER.info("Checking load and stack")
                # DO NOT RECOMPUTE BANDS WITH SNAP --> WAY TOO SLOW
                stack_bands = [band for band in possible_bands if prod.has_band(band)]
                first_band = stack_bands[0]

                # Check that band loaded 2 times gives the same results (disregarding float uncertainties)
                assert prod.load([]) == {}
                band_arr_raw = prod.load(
                    first_band.value, resolution=res, clean_optical="raw"
                )[first_band]
                band_arr1 = prod.load(
                    first_band, resolution=res, clean_optical="nodata"
                )[first_band]
                band_arr2 = prod.load(first_band, resolution=res)[first_band]
                np.testing.assert_array_almost_equal(band_arr1, band_arr2)
                assert band_arr_raw.dtype == np.float32
                assert band_arr1.dtype == np.float32
                assert band_arr2.dtype == np.float32
                assert band_arr_raw.shape == band_arr1.shape

                # Get stack bands
                # Stack data
                ci_stack = get_ci_data_dir().joinpath(
                    prod.condensed_name, f"{prod.condensed_name}_stack.tif"
                )

                curr_path = os.path.join(tmp_dir, f"{prod.condensed_name}_stack.tif")
                stack = prod.stack(
                    stack_bands,
                    resolution=res,
                    stack_path=curr_path,
                    clean_optical="clean",
                    **kwargs,
                )
                assert stack.dtype == np.float32

                # Check attributes
                assert stack.attrs["long_name"] == " ".join(to_str(stack_bands))
                assert stack.attrs["constellation"] == prod._get_constellation().value
                assert stack.attrs["constellation_id"] == prod.constellation_id
                assert stack.attrs["product_type"] == prod.product_type.value
                assert (
                    stack.attrs["instrument"] == prod.instrument
                    if isinstance(prod.instrument, str)
                    else prod.instrument.value
                )
                assert stack.attrs["acquisition_date"] == prod.get_datetime(
                    as_datetime=False
                )
                assert stack.attrs["condensed_name"] == prod.condensed_name
                assert stack.attrs["product_path"] == str(prod.path)

                # Write to path if needed
                if not ci_stack.exists():
                    raise FileNotFoundError(f"{ci_stack} not found !")
                    # ci_stack = curr_path

                else:
                    # Test
                    assert_raster_almost_equal(curr_path, ci_stack, decimal=4)

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
                    ci_band = curr_path_band

                band_arr = prod.load(
                    first_band,
                    size=(stack.rio.width, stack.rio.height),
                    clean_optical="clean",
                    **kwargs,
                )[first_band]
                rasters.write(band_arr, curr_path_band)
                assert_raster_almost_equal(curr_path_band, ci_band, decimal=4)

                # Check reflectance validity
                if (
                    prod.sensor_type == SensorType.OPTICAL
                    and band_arr.attrs["radiometry"] == "reflectance"
                ):
                    assert np.nanmax(band_arr) < 10.0
                    assert np.nanpercentile(band_arr, 95) < 1.0
                    assert np.nanmin(band_arr) > -1.0
                    assert np.nanpercentile(band_arr, 5) > 0.0

                # Check attributes
                assert band_arr.attrs["long_name"] == first_band.name
                assert (
                    band_arr.attrs["constellation"] == prod._get_constellation().value
                )
                assert band_arr.attrs["constellation_id"] == prod.constellation_id
                assert band_arr.attrs["product_type"] == prod.product_type.value
                assert band_arr.attrs["acquisition_date"] == prod.get_datetime(
                    as_datetime=False
                )
                assert band_arr.attrs["condensed_name"] == prod.condensed_name
                assert band_arr.attrs["product_path"] == str(prod.path)

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

                # Mean sun angle type, cloud cover...
                if prod.sensor_type == SensorType.OPTICAL:
                    az, zen = prod.get_mean_sun_angles()
                    assert isinstance(az, float)
                    assert isinstance(zen, float)

                    cc = prod.get_cloud_cover()
                    assert isinstance(cc, float)

                # Quicklook and plot
                qck_path = prod.get_quicklook_path()
                if qck_path is not None:
                    assert isinstance(qck_path, str)

                # Plot and close figure
                prod.plot()
                plt.close()

                # Orbit direction
                orbit_dir = prod.get_orbit_direction()
                assert isinstance(orbit_dir, OrbitDirection)

                # Clean temp
                if not debug:
                    LOGGER.info("Cleaning tmp")
                    prod.clean_tmp()
                    assert len(list(prod._tmp_process.glob("*"))) == 0

            prod.clear()


@s3_env
@dask_env
def test_s2():
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*")


@s3_env
@dask_env
def test_s2_theia():
    """Function testing the support of Sentinel-2 Theia constellation"""
    _test_core_optical("*SENTINEL2*")


@s3_env
@dask_env
def test_s3_olci():
    """Function testing the support of Sentinel-3 OLCI constellation"""
    # Init logger
    _test_core_optical("*S3*_OL_1_*")


@s3_env
@dask_env
def test_s3_slstr():
    """Function testing the support of Sentinel-3 SLSTR constellation"""
    # Init logger
    _test_core_optical("*S3*_SL_1_*", **{SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP})


@s3_env
@dask_env
def test_l9():
    """Function testing the support of Landsat-9 constellation"""
    # Init logger
    _test_core_optical("*LC09*")


@s3_env
@dask_env
def test_l8():
    """Function testing the support of Landsat-8 constellation"""
    # Init logger
    _test_core_optical("*LC08*")


@s3_env
@dask_env
def test_l7():
    """Function testing the support of Landsat-7 constellation"""
    _test_core_optical("*LE07*")


@s3_env
@dask_env
def test_l5_tm():
    """Function testing the support of Landsat-5 TM constellation"""
    _test_core_optical("*LT05*")


@s3_env
@dask_env
def test_l4_tm():
    """Function testing the support of Landsat-4 TM constellation"""
    _test_core_optical("*LT04*")


@pytest.mark.skipif(
    sys.platform == "win32" or os.getenv(CI_EOREADER_S3) == "0",
    reason="Weirdly, Landsat-5 image shape is not the same with data from disk or S3. Skipping test on disk",
)
@s3_env
@dask_env
def test_l5_mss():
    """Function testing the support of Landsat-5 MSS constellation"""
    _test_core_optical("*LM05*")


@s3_env
@dask_env
def test_l4_mss():
    """Function testing the support of Landsat-4 MSS constellation"""
    _test_core_optical("*LM04*")


@s3_env
@dask_env
def test_l3_mss():
    """Function testing the support of Landsat-3 constellation"""
    _test_core_optical("*LM03*")


@s3_env
@dask_env
def test_l2_mss():
    """Function testing the support of Landsat-2 constellation"""
    _test_core_optical("*LM02*")


@s3_env
@dask_env
def test_l1_mss():
    """Function testing the support of Landsat-1 constellation"""
    _test_core_optical("*LM01*")


@s3_env
@dask_env
def test_pla():
    """Function testing the support of PlanetScope constellation"""
    _test_core_optical("*202*1014*")


@s3_env
@dask_env
def test_sky():
    """Function testing the support of SkySat constellation"""
    _test_core_optical("*ssc*")


@s3_env
@dask_env
def test_pld():
    """Function testing the support of Pleiades constellation"""
    _test_core_optical("*IMG_PHR*")


@s3_env
@dask_env
def test_pneo():
    """Function testing the support of Pleiades-Neo constellation"""
    _test_core_optical("*IMG_*_PNEO*")


@s3_env
@dask_env
def test_spot4():
    """Function testing the support of SPOT-4 constellation"""
    _test_core_optical("*SP04*")


@s3_env
@dask_env
def test_spot5():
    """Function testing the support of SPOT-5 constellation"""
    _test_core_optical("*SP05*")


@s3_env
@dask_env
def test_spot6():
    """Function testing the support of SPOT-6 constellation"""
    _test_core_optical("*IMG_SPOT6*")


@s3_env
@dask_env
def test_spot7():
    """Function testing the support of SPOT-7 constellation"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*IMG_SPOT7*", dem_path=dem_path)


@s3_env
@dask_env
def test_wv02_wv03():
    """Function testing the support of WorldView-2/3 constellations"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*P001_MUL*", dem_path=dem_path)


@s3_env
@dask_env
def test_ge01_wv04():
    """Function testing the support of GeoEye-1/WorldView-4 constellations"""
    _test_core_optical("*P001_PSH*")


@s3_env
@dask_env
def test_vs1():
    """Function testing the support of Vision-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*VIS1_MS4*", dem_path=dem_path)


@s3_env
@dask_env
def test_sv1():
    """Function testing the support of SuperView-1 constellation"""
    dem_path = os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)
    _test_core_optical("*0001_01*", dem_path=dem_path)


@s3_env
@dask_env
def test_s1():
    """Function testing the support of Sentinel-1 constellation"""
    _test_core_sar("*S1*_IW*")


@s3_env
@dask_env
def test_csk():
    """Function testing the support of COSMO-Skymed constellation"""
    _test_core_sar("*csk_*")


@s3_env
@dask_env
def test_csg():
    """Function testing the support of COSMO-Skymed 2nd Generation constellation"""
    _test_core_sar("*CSG_*")


@s3_env
@dask_env
def test_tsx():
    """Function testing the support of TerraSAR-X constellations"""
    _test_core_sar("*TSX*")


# Assume that tests PAZ and TDX
@s3_env
@dask_env
def test_tdx():
    """Function testing the support of PAZ SAR and TanDEM-X constellations"""
    _test_core_sar("*TDX*")


@s3_env
@dask_env
def test_rs2():
    """Function testing the support of RADARSAT-2 constellation"""
    _test_core_sar("*RS2_*")


@s3_env
@dask_env
def test_rcm():
    """Function testing the support of RADARSAT-Constellation constellation"""
    _test_core_sar("*RCM*")


@s3_env
@dask_env
def test_iceye():
    """Function testing the support of ICEYE constellation"""
    _test_core_sar("*SC_*")


@s3_env
@dask_env
def test_saocom():
    """Function testing the support of SAOCOM constellation"""
    _test_core_sar("*SAO*")


# TODO:
# check non existing bands
# check cloud results


def test_invalid():
    wrong_path = "dzfdzef"
    assert READER.open(wrong_path) is None
    assert not READER.valid_name(wrong_path, "S2")


@s3_env
@dask_env
def test_sar():
    """Function testing some other SAR methods"""
    # TODO
