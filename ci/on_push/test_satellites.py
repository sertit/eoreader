"""Script testing EOReader satellites in a push routine"""

import contextlib
import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from geopandas import gpd
from matplotlib import pyplot as plt
from sertit import ci, misc, path

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
    set_dem,
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
    SAR_DEF_PIXEL_SIZE,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import Product, SensorType, SlstrRadAdjust
from eoreader.reader import CheckMethod
from eoreader.utils import use_dask

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM_SUB_DIR_PATH = [
    "GLOBAL",
    "MERIT_Hydrologically_Adjusted_Elevations",
    "MERIT_DEM.vrt",
]

WRITE_ON_DISK = False

reduce_verbosity()


def _test_core_optical(
    pattern: str, tmpdir: Path, dem_path=None, debug=WRITE_ON_DISK, **kwargs
):
    """
    Core function testing optical data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [RED, SWIR_2, TIR_1, HILLSHADE, CLOUDS]
    _test_core(pattern, opt_path(), possible_bands, tmpdir, dem_path, debug, **kwargs)


def _test_core_sar(
    pattern: str, tmpdir: Path, dem_path=None, debug=WRITE_ON_DISK, **kwargs
):
    """
    Core function testing SAR data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    possible_bands = [VV, VV_DSPK, HH, HH_DSPK, SLOPE, HILLSHADE]
    _test_core(pattern, sar_path(), possible_bands, tmpdir, dem_path, debug, **kwargs)


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
                f"{geometry_str} file not found for {prod.condensed_name}!"
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
    LOGGER.info("Check stack")

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
            if "failed" in str(ex).replace("SLOPE failed", "").replace(
                "HILLSHADE failed", ""
            ):
                raise ex

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
    tmpdir: Path,
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
        tmpdir(Path): path to store temporary data
        debug (bool): Debug option
    """
    set_dem()

    with xr.set_options(warn_for_unclosed_files=debug):
        # DATA paths
        pattern_paths = path.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for pattern_path in pattern_paths[::-1]:
            use_dask_in_test = use_dask() and not (
                pattern_path.is_file() and os.getenv(CI_EOREADER_S3) == "1"
            )
            core(
                pattern_path,
                possible_bands,
                tmpdir,
                use_dask=use_dask_in_test,
                **kwargs,
            )


@dask_env
def core(prod_path, possible_bands, tmpdir, **kwargs):
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
            tmp_dir = os.path.join(tmpdir, prod.condensed_name)
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
                LOGGER.info("Check WGS84 extent")
                prod.wgs84_extent()

        if hasattr(prod, "_fallback_wgs84_extent"):
            with contextlib.suppress(NotImplementedError):
                LOGGER.info("Check WGS84 extent (fallback)")
                prod._fallback_wgs84_extent()

        # Get the bands we want to stack / load
        LOGGER.debug("Selecting bands for stacking")
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


test_optical_constellations_cases = [
    pytest.param("*VENUS*", {}, id="venus"),
    pytest.param("*S2*_MSI*_N7*", {}, id="s2_after_04_00"),
    pytest.param("*S2*_MSI*_N0209*", {}, id="s2_before_04_00"),
    pytest.param("*SENTINEL2*", {}, id="s2_theia"),
    pytest.param("*S2A_39KZU*", {}, id="s2_cloud"),
    pytest.param("*S3*_OL_1_*", {}, id="s3_olci"),
    pytest.param("*S3*_SL_1_*", {SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP}, id="s3_slstr"),
    pytest.param("*LC09*", {}, id="l9"),
    pytest.param("*LC08*", {}, id="l8"),
    pytest.param("*LE07*", {}, id="l7"),
    pytest.param("*LT05*", {}, id="l5_tm"),
    pytest.param("*LT04*", {}, id="l4_tm"),
    pytest.param(
        "*LM05*",
        {},
        marks=pytest.mark.skipif(
            sys.platform == "win32" or os.getenv(CI_EOREADER_S3) == "0",
            reason=(
                "Weirdly, Landsat-5 image shape is not the same with data from disk or S3. Skipping test on disk"
            ),
        ),
        id="l5_mss",
    ),
    pytest.param("*LM04*", {}, id="l4_mss"),
    pytest.param("*LM03*", {}, id="l3_mss"),
    pytest.param("*LM02*", {}, id="l2_mss"),
    pytest.param("*LM01*", {}, id="l1_mss"),
    pytest.param("*HLS*", {}, id="hls"),
    pytest.param("*202*1014*", {}, id="pla"),
    pytest.param("*ssc*", {}, id="sky"),
    pytest.param("*_RE4_*", {}, id="re"),
    pytest.param("*IMG_PHR*", {}, id="pld"),
    pytest.param("*IMG_*_PNEO*", {}, id="pneo"),
    pytest.param("*SP04*", {}, id="spot4"),
    pytest.param("*SP05*", {}, id="spot5"),
    pytest.param("*IMG_SPOT6*", {}, id="spot6"),
    pytest.param(
        "*IMG_SPOT7*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="spot7",
    ),
    pytest.param(
        "*055670633040_01_P001_MUL*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="wv02_wv03_mul",
    ),
    pytest.param("*P001_PSH*", {}, id="ge01_psh"),
    pytest.param("*050246698010_01_P001_MUL*", {}, id="wv_legion"),
    pytest.param(
        "*VIS1_MS4*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="vs1",
    ),
    pytest.param(
        "*0001_01*",
        {"dem_path": os.path.join(get_db_dir_on_disk(), *MERIT_DEM_SUB_DIR_PATH)},
        id="sv1",
    ),
    pytest.param("*DE2_*", {}, id="gs2"),
]


@s3_env
@pytest.mark.parametrize("pattern, kwargs", test_optical_constellations_cases)
def test_optical_constellations(pattern, kwargs, eoreader_tests_path):
    _test_core_optical(pattern, eoreader_tests_path.tmpdir, **kwargs)


test_sar_constellations_cases = [
    pytest.param("*S1*_IW_GRDH*", {}, id="s1"),
    pytest.param("*S1*_RTC*", {}, id="s1_rtc"),
    pytest.param("*csk_*", {}, id="csk"),
    pytest.param("*CSG_*", {}, id="csg"),
    pytest.param("*TSX*", {}, id="tsx"),
    pytest.param("*TDX*", {}, id="tdx"),  # Assume that tests PAZ and TDX
    pytest.param("*RS2_*", {}, id="rs2"),
    pytest.param("*RCM*", {}, id="rcm"),
    pytest.param("*SC_*", {}, id="iceye"),
    pytest.param("*SAO*", {}, id="saocom"),
    pytest.param("*CAPELLA*", {}, id="capella"),
    pytest.param("*UMBRA*", {}, id="umbra"),
]


@s3_env
@pytest.mark.parametrize("pattern, kwargs", test_sar_constellations_cases)
def test_sar_constellations(pattern, kwargs, eoreader_tests_path):
    _test_core_sar(pattern, eoreader_tests_path.tmpdir, **kwargs)


# TODO:
# check non existing bands
# check cloud results


def test_invalid():
    wrong_path = "dzfdzef"
    with pytest.raises(FileNotFoundError):
        READER.open(wrong_path, remove_tmp=True)
    assert not READER.valid_name(wrong_path, "S2")


@s3_env
def test_s2_after_04_00(eoreader_tests_path):
    """Function testing the support of Sentinel-2 constellation"""
    _test_core_optical("*S2*_MSI*_N7*", eoreader_tests_path.tmpdir)
