import os

import numpy as np
import pytest
from sertit import ci

from eoreader.bands import *
from eoreader.env_vars import DEM_PATH
from eoreader.exceptions import InvalidTypeError
from eoreader.products import SensorType

from .scripts_utils import READER, dask_env, get_db_dir, others_path, s3_env


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
        acquisition_datetime="20200310T030415",
        sensor_type=SensorType.OPTICAL,
        platform="WV02",
        default_resolution=2.0,
        product_type="Ortho",
        band_map={BLUE: 1, GREEN: 2, RED: 3, NIR: 4, SWIR_1: 5},
    )
    extent_all = prod_all.extent
    footprint_all = prod_all.footprint
    crs_all = prod_all.crs
    stack = prod_all.stack([BLUE, GREEN, RED, NIR])

    # Check attributes
    assert stack.attrs["long_name"] == "BLUE GREEN RED NIR"
    assert stack.attrs["sensor"] == "WorldView-2"
    assert stack.attrs["sensor_id"] == "WV02"
    assert stack.attrs["product_type"] == "Ortho"
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
    extent_min = prod_min.extent
    footprint_min = prod_min.footprint
    crs_min = prod_min.crs
    bands = prod_min.load([BLUE, NIR])

    # Check attributes
    assert bands[BLUE].attrs["long_name"] == "BLUE"
    assert bands[NIR].attrs["long_name"] == "NIR"
    assert bands[BLUE].attrs["sensor"] == "CUSTOM"
    assert bands[BLUE].attrs["sensor_id"] == "CUSTOM"
    assert bands[BLUE].attrs["product_type"] == "CUSTOM"
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
        acquisition_datetime="20200310T030415",
        sensor_type="Optical",
        product_type="wonderful_type",
        sun_azimuth=10.0,
        sun_zenith=20.0,
        band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4, SWIR_1: 5},
    )
    extent_some = prod_some.extent
    footprint_some = prod_some.footprint
    crs_some = prod_some.crs
    bands = prod_some.load([HILLSHADE], resolution=200.0)

    # Check attributes
    assert bands[HILLSHADE].attrs["long_name"] == "HILLSHADE"
    assert bands[HILLSHADE].attrs["sensor"] == "CUSTOM"
    assert bands[HILLSHADE].attrs["sensor_id"] == "CUSTOM"
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
    opt_stack = others_path() / "20200310T030415_WV02_Ortho_BGRN_STK.tif"
    prod_sar = READER.open(
        sar_stack,
        custom=True,
        sensor_type=SensorType.SAR,
        name="20210827T162210_ICEYE_SC_GRD",
        acquisition_datetime="20210827T162210",
        platform="ICEYE",
        default_resolution=6.0,
        product_type="GRD",
        band_map={VV: 1, VV_DSPK: 2},
    )
    extent_sar = prod_sar.extent
    footprint_sar = prod_sar.footprint
    crs_sar = prod_sar.crs
    stack_sar = prod_sar.stack([VV, VV_DSPK])

    # Check attributes
    assert stack_sar.attrs["long_name"] == "VV VV_DSPK"
    assert stack_sar.attrs["sensor"] == "ICEYE"
    assert stack_sar.attrs["sensor_id"] == "ICEYE"
    assert stack_sar.attrs["product_type"] == "GRD"
    assert stack_sar.attrs["acquisition_date"] == "20210827T162210"
    assert stack_sar.attrs["condensed_name"] == "20210827T162210_ICEYE_GRD"
    assert stack_sar.attrs["product_path"] == str(sar_stack)

    # MIX
    prod_wtf = READER.open(
        sar_stack, custom=True, sensor_type=SensorType.SAR, band_map={HH: 1, RH: 2}
    )
    extent_wtf = prod_wtf.extent
    footprint_wtf = prod_wtf.footprint
    crs_wtf = prod_wtf.crs
    stack_wtf = prod_wtf.stack([HH, RH])

    ci.assert_geom_equal(extent_sar, extent_wtf)
    ci.assert_geom_equal(footprint_sar, footprint_wtf)
    assert crs_sar == crs_wtf

    np.testing.assert_array_equal(stack_sar.data, stack_wtf.data)

    with pytest.raises(InvalidTypeError):
        READER.open(
            opt_stack,
            custom=True,
            sensor_type=SensorType.SAR,
            band_map={BLUE: 1, "GREEN": 2, RED: 3, "NIR": 4},
        )
