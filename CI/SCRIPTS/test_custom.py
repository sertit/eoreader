import logging
import os

import numpy as np
import pytest
from sertit import ci

from eoreader.bands import (
    BLUE,
    CLOUDS,
    GREEN,
    HH,
    HILLSHADE,
    NIR,
    RED,
    RH,
    SWIR_1,
    VV,
    VV_DSPK,
    YELLOW,
)
from eoreader.env_vars import DEM_PATH
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import SensorType
from eoreader.utils import EOREADER_NAME

from .scripts_utils import READER, dask_env, get_db_dir, others_path, s3_env

LOGGER = logging.getLogger(EOREADER_NAME)

ci.reduce_verbosity()


@s3_env
@dask_env
def test_custom():
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
        resolution=2.0,
        product_type="Ortho",
        band_map={BLUE: 1, GREEN: 2, RED: 3, NIR: 4, SWIR_1: 5},
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
    )
    LOGGER.info(prod_min)
    extent_min = prod_min.extent()
    footprint_min = prod_min.footprint()
    crs_min = prod_min.crs()
    bands = prod_min.load([BLUE, NIR])

    # Check attributes
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
        band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4, SWIR_1: 5},
    )
    LOGGER.info(prod_some)
    extent_some = prod_some.extent()
    footprint_some = prod_some.footprint()
    crs_some = prod_some.crs()
    bands = prod_some.load([HILLSHADE], resolution=200.0)

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
        READER.open(opt_stack, custom=True, sensor_type="Optical")

    with pytest.raises(ValueError):
        READER.open(
            opt_stack, custom=True, band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4}
        )

    # SAR
    sar_stack = others_path() / "20210827T162210_ICEYE_SC_GRD_STK.tif"

    # Load with all info
    prod_sar = READER.open(
        sar_stack,
        custom=True,
        sensor_type=SensorType.SAR,
        name="20210827T162210_ICEYE_SC_GRD",
        datetime="20210827T162210",
        constellation="ICEYE",
        instrument="SAR X-band",
        resolution=6.0,
        product_type="GRD",
        band_map={VV: 1, VV_DSPK: 2},
    )
    LOGGER.info(prod_sar)
    extent_sar = prod_sar.extent()
    footprint_sar = prod_sar.footprint()
    crs_sar = prod_sar.crs()
    stack_sar = prod_sar.stack([VV, VV_DSPK], prod_sar.resolution * 10)

    # Check attributes
    assert stack_sar.attrs["long_name"] == "VV VV_DSPK"
    assert stack_sar.attrs["constellation"] == "ICEYE"
    assert stack_sar.attrs["constellation_id"] == "ICEYE"
    assert stack_sar.attrs["product_type"] == "GRD"
    assert stack_sar.attrs["instrument"] == "SAR X-band"
    assert stack_sar.attrs["acquisition_date"] == "20210827T162210"
    assert stack_sar.attrs["condensed_name"] == "20210827T162210_ICEYE_GRD"
    assert stack_sar.attrs["product_path"] == str(sar_stack)

    # MIX
    prod_wtf = READER.open(
        sar_stack,
        custom=True,
        sensor_type=SensorType.SAR,
        band_map={HH: 1, RH: 2},
        resolution=6.0,
    )
    LOGGER.info(prod_wtf)
    extent_wtf = prod_wtf.extent()
    footprint_wtf = prod_wtf.footprint()
    crs_wtf = prod_wtf.crs()
    stack_wtf = prod_wtf.stack([HH, RH], prod_wtf.resolution * 10)

    ci.assert_geom_equal(extent_sar, extent_wtf)
    ci.assert_geom_equal(footprint_sar, footprint_wtf)
    assert crs_sar == crs_wtf

    np.testing.assert_array_equal(stack_sar.data, stack_wtf.data)

    # WGS84
    wgs84_stack = others_path() / "SPOT6_WGS84.tif"
    prod_wgs84 = READER.open(
        wgs84_stack,
        custom=True,
        sensor_type=SensorType.OPTICAL,
        name="SPOT6_WGS84",
        datetime="20181218T090308",
        constellation="SPOT6",
        resolution=1.5 * 15,
        instrument="NAOMI",
        product_type="ORT",
        band_map={RED: 1, GREEN: 2, BLUE: 3, NIR: 4},
    )
    LOGGER.info(prod_wgs84)

    # Check geometries -> assert projected
    with pytest.raises(InvalidProductError):
        prod_wgs84.extent()  # noqa

    with pytest.raises(InvalidProductError):
        prod_wgs84.footprint()  # noqa

    with pytest.raises(InvalidProductError):
        prod_wgs84.crs()  # noqa

    # Read mtd
    root, nsp = prod_wgs84.read_mtd()
    assert nsp == {}
    assert root.findtext("name") == "SPOT6_WGS84"
    assert root.findtext("datetime") == "2018-12-18T09:03:08"
    assert root.findtext("sensor_type") == "Optical"
    assert root.findtext("constellation") == "Spot-6"
    assert root.findtext("resolution") == str(1.5 * 15)
    assert root.findtext("product_type") == "ORT"
    assert root.findtext("band_map") == "{'BLUE': 3, 'GREEN': 2, 'RED': 1, 'NIR': 4}"
    assert root.findtext("sun_azimuth") == "None"
    assert root.findtext("sun_zenith") == "None"
    assert root.findtext("orbit_direction") == "None"
    assert root.findtext("cloud_cover") == "None"
    assert root.findtext("instrument") == "NAOMI"

    # Band paths
    assert prod_wgs84.get_existing_bands() == [BLUE, GREEN, RED, NIR]
    assert prod_wgs84.get_default_band() == BLUE
    for key, path in prod_wgs84.get_existing_band_paths().items():
        assert key in [BLUE, GREEN, RED, NIR]
        assert str(path) == str(wgs84_stack)

    # Load without a list and nothing
    with pytest.raises(InvalidProductError):
        prod_wgs84.load(BLUE, size=[3863, 1049])[BLUE]  # noqa

    # Try non available clouds and bands
    assert prod_wgs84.load([]) == {}
    assert not prod_wgs84.has_bands(CLOUDS)
    with pytest.raises(AssertionError):
        prod_wgs84.load(CLOUDS, YELLOW)

    # Invalid tests
    with pytest.raises(InvalidTypeError):
        READER.open(
            opt_stack,
            custom=True,
            sensor_type=SensorType.SAR,
            band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4},
        )
