"""Testing custom stacks."""

import logging
import os

import pytest
from rasterio.windows import Window
from sertit import ci

from ci.scripts_utils import (
    READER,
    dask_env,
    get_db_dir,
    others_path,
    reduce_verbosity,
    s3_env,
)
from eoreader import EOREADER_NAME
from eoreader.bands import BLUE, CA, GREEN, HILLSHADE, NDVI, NIR, RED, SWIR_1
from eoreader.env_vars import DEM_PATH
from eoreader.exceptions import InvalidTypeError
from eoreader.products import SensorType

LOGGER = logging.getLogger(EOREADER_NAME)


reduce_verbosity()


@s3_env
@dask_env
def test_custom_optical():
    # -- OPTICAL
    # Load with all info
    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    prod_all = READER.open(
        opt_stack,
        custom=True,
        name="20200310T030415_WV02_Ortho",
        datetime="20200310T030415",
        sensor_type=SensorType.OPTICAL,
        constellation="WV02",
        instrument="WW110",
        pixel_size=2.0,
        product_type="Ortho",
        band_map={BLUE: 1, GREEN: 2, RED: 3, NIR: 4, SWIR_1: 5},
        remove_tmp=True,
    )
    LOGGER.info(prod_all)
    extent_all = prod_all.extent()
    footprint_all = prod_all.footprint()
    crs_all = prod_all.crs()
    stack = prod_all.stack([BLUE, GREEN, RED, NIR])

    # Check attributes
    assert stack.attrs["long_name"] == "BLUE GREEN RED NIR"
    assert stack.attrs["constellation"] == "WorldView-2"
    assert stack.attrs["constellation_id"] == "WV02"
    assert stack.attrs["product_type"] == "Ortho"
    assert stack.attrs["instrument"] == "WW110"
    assert stack.attrs["acquisition_date"] == "20200310T030415"
    assert stack.attrs["condensed_name"] == "20200310T030415_WV02_Ortho"
    assert stack.attrs["product_path"] == str(opt_stack)

    # Load with minimum info
    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    prod_min = READER.open(
        opt_stack,
        custom=True,
        sensor_type="OPTICAL",
        band_map={"BLUE": 1, "GREEN": 2, "RED": 3, "NIR": 4, SWIR_1: 5},
        remove_tmp=True,
    )
    LOGGER.info(prod_min)
    extent_min = prod_min.extent()
    footprint_min = prod_min.footprint()
    crs_min = prod_min.crs()
    bands = prod_min.load(
        [BLUE, NIR, NDVI],
        window=Window(col_off=0, row_off=0, width=100, height=100),
    )

    # Check attributes
    assert NDVI in bands
    assert bands[BLUE].attrs["long_name"] == "BLUE"
    assert bands[NIR].attrs["long_name"] == "NIR"
    assert bands[BLUE].attrs["constellation"] == "CUSTOM"
    assert bands[BLUE].attrs["constellation_id"] == "CUSTOM"
    assert bands[BLUE].attrs["product_type"] == "CUSTOM"
    assert bands[BLUE].attrs["instrument"] == "CUSTOM"
    # assert bands[BLUE].attrs["acquisition_date"] == "20200310T030415"  Don't test this, datetime == now
    assert bands[BLUE].attrs["condensed_name"].endswith("CUSTOM_CUSTOM")
    assert bands[BLUE].attrs["product_path"] == str(opt_stack)

    ci.assert_geom_equal(extent_all, extent_min)
    ci.assert_geom_equal(footprint_all, footprint_min)
    assert crs_all == crs_min

    # Load with some info + HILLSHADE
    dem_sub_dir_path = [
        "GLOBAL",
        "MERIT_Hydrologically_Adjusted_Elevations",
        "MERIT_DEM.vrt",
    ]
    os.environ[DEM_PATH] = str(get_db_dir().joinpath(*dem_sub_dir_path))
    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    prod_some = READER.open(
        opt_stack,
        custom=True,
        datetime="20200310T030415",
        sensor_type="Optical",
        product_type="wonderful_type",
        sun_azimuth=10.0,
        sun_zenith=20.0,
        band_map={CA: 1, "COASTAL_AEROSOL": 2, RED: 3, "CA": 4, SWIR_1: 5},
        remove_tmp=True,
    )
    LOGGER.info(prod_some)
    extent_some = prod_some.extent()
    footprint_some = prod_some.footprint()
    crs_some = prod_some.crs()
    bands = prod_some.load(
        [HILLSHADE],
        window=Window(col_off=0, row_off=0, width=100, height=100),
    )

    # Check attributes
    assert bands[HILLSHADE].attrs["long_name"] == "HILLSHADE"
    assert bands[HILLSHADE].attrs["constellation"] == "CUSTOM"
    assert bands[HILLSHADE].attrs["constellation_id"] == "CUSTOM"
    assert bands[HILLSHADE].attrs["instrument"] == "CUSTOM"
    assert bands[HILLSHADE].attrs["product_type"] == "wonderful_type"
    assert bands[HILLSHADE].attrs["acquisition_date"] == "20200310T030415"
    assert (
        bands[HILLSHADE].attrs["condensed_name"]
        == "20200310T030415_CUSTOM_wonderful_type"
    )
    assert bands[HILLSHADE].attrs["product_path"] == str(opt_stack)

    ci.assert_geom_equal(extent_all, extent_some)
    ci.assert_geom_equal(footprint_all, footprint_some)
    assert crs_all == crs_some

    # Errors
    with pytest.raises(ValueError):
        READER.open(opt_stack, custom=True, sensor_type="Optical", remove_tmp=True)

    with pytest.raises(ValueError):
        READER.open(
            opt_stack,
            custom=True,
            band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4},
            remove_tmp=True,
        )


def test_custom_invalid():
    # Invalid tests
    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    with pytest.raises(InvalidTypeError):
        READER.open(
            opt_stack,
            custom=True,
            sensor_type=SensorType.SAR,
            band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4},
            remove_tmp=True,
        )
