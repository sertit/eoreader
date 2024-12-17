"""Testing custom stacks weekly"""

import logging

import numpy as np
import pytest
from sertit import ci

from ci.on_push.test_custom import test_custom_invalid, test_custom_optical
from ci.scripts_utils import READER, dask_env, others_path, reduce_verbosity, s3_env
from eoreader import EOREADER_NAME
from eoreader.bands import (
    BLUE,
    CLOUDS,
    GREEN,
    HH,
    NDVI,
    NIR,
    RED,
    RH,
    VV,
    VV_DSPK,
    YELLOW,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products import SensorType

LOGGER = logging.getLogger(EOREADER_NAME)

reduce_verbosity()


@s3_env
@dask_env
def test_custom_optical_weekly():
    test_custom_optical()


def test_custom_sar():
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
        pixel_size=6.0,
        product_type="GRD",
        band_map={VV: 1, VV_DSPK: 2},
        remove_tmp=True,
    )
    LOGGER.info(prod_sar)
    extent_sar = prod_sar.extent()
    footprint_sar = prod_sar.footprint()
    crs_sar = prod_sar.crs()
    stack_sar = prod_sar.stack([VV, VV_DSPK], prod_sar.pixel_size * 10)

    # Errors
    with pytest.raises(AssertionError):
        prod_sar.load(NDVI)

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
    sar_stack = others_path() / "20210827T162210_ICEYE_SC_GRD_STK.tif"
    prod_wtf = READER.open(
        sar_stack,
        custom=True,
        sensor_type=SensorType.SAR,
        band_map={HH: 1, RH: 2},
        name=None,
        product_type=None,
        instrument=None,
        datetime=None,
        pixel_size=6.0,
        remove_tmp=True,
    )
    LOGGER.info(prod_wtf)
    extent_wtf = prod_wtf.extent()
    footprint_wtf = prod_wtf.footprint()
    crs_wtf = prod_wtf.crs()
    stack_wtf = prod_wtf.stack([HH, RH], prod_wtf.pixel_size * 10)

    ci.assert_geom_equal(extent_sar, extent_wtf)
    ci.assert_geom_equal(footprint_sar, footprint_wtf)
    assert crs_sar == crs_wtf
    assert prod_wtf.name is not None
    assert prod_wtf.product_type is not None
    assert prod_wtf.instrument is not None

    np.testing.assert_array_equal(stack_sar.data, stack_wtf.data)


def test_custom_wgs84():
    # WGS84
    wgs84_stack = others_path() / "SPOT6_WGS84.tif"
    prod_wgs84 = READER.open(
        wgs84_stack,
        custom=True,
        sensor_type=SensorType.OPTICAL,
        name="SPOT6_WGS84",
        datetime="20181218T090308",
        constellation="SPOT6",
        pixel_size=1.5 * 15,
        instrument="NAOMI",
        product_type="ORT",
        band_map={RED: 1, GREEN: 2, BLUE: 3, NIR: 4},
        remove_tmp=True,
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
    assert root.findtext("pixel_size") == str(1.5 * 15)
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
    for key, ppath in prod_wgs84.get_existing_band_paths().items():
        assert key in [BLUE, GREEN, RED, NIR]
        assert str(ppath) == str(wgs84_stack)

    # Load without a list and nothing
    with pytest.raises(InvalidProductError):
        prod_wgs84.load(BLUE, size=[3863, 1049])[BLUE]  # noqa

    # Try non-available clouds and bands
    assert len(prod_wgs84.load([])) == 0
    assert not prod_wgs84.has_bands(CLOUDS)
    with pytest.raises(AssertionError):
        prod_wgs84.load(CLOUDS, YELLOW)


def test_custom_invalid_weekly():
    test_custom_invalid()
