""" Script testing EOReader satellites in a push routine """
import logging
import os
import sys
import tempfile
from typing import Union

import pystac
import pytest
import xarray as xr
from sertit import ci, files
from sertit.vectors import WGS84
from shapely.geometry import mapping

from eoreader.bands import (
    NARROW_NIR,
    TIR_1,
    TIR_2,
    VRE_1,
    VRE_2,
    VRE_3,
    SarBand,
    SarBandNames,
    SpectralBand,
    SpectralBandNames,
)
from eoreader.keywords import SLSTR_RAD_ADJUST
from eoreader.products import (
    LandsatInstrument,
    OpticalProduct,
    Product,
    SarProduct,
    SensorType,
    SlstrRadAdjust,
)
from eoreader.reader import CheckMethod, Constellation
from eoreader.stac import EO_BANDS
from eoreader.stac._stac_keywords import (
    CONSTELLATION,
    DATETIME,
    EO_CC,
    GSD,
    PROJ_BBOX,
    PROJ_EPSG,
    PROJ_GEOMETRY,
    PROJ_SHAPE,
    PROJ_TRANSFORM,
    PROJ_WKT,
    TITLE,
    VIEW_AZIMUTH,
    VIEW_INCIDENCE_ANGLE,
    VIEW_OFF_NADIR,
    VIEW_SUN_AZIMUTH,
    VIEW_SUN_ELEVATION,
)
from eoreader.utils import EOREADER_NAME

from .scripts_utils import CI_EOREADER_S3, READER, dask_env, opt_path, s3_env, sar_path

ci.reduce_verbosity()

LOGGER = logging.getLogger(EOREADER_NAME)


def _test_core_optical(pattern: str, debug=False, **kwargs):
    """
    Core function testing optical data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    _test_core(pattern, opt_path(), debug, **kwargs)


def _test_core_sar(pattern: str, debug=False, **kwargs):
    """
    Core function testing SAR data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    _test_core(pattern, sar_path(), debug, **kwargs)


def compare(to_be_checked, ref, topic):
    """
    Compare two fields
    """
    assert (
        ref == to_be_checked
    ), f"Non equal {topic}: ref ={ref} != to_be_checked={to_be_checked}"


def _test_core(
    pattern: str,
    prod_dir: str,
    debug=False,
    **kwargs,
):
    """
    Core function testing all data

    Args:
        pattern (str): Pattern of the satellite
        prod_dir (str): Product directory
        debug (bool): Debug option
    """

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
            prod: Product = READER.open(path, method=CheckMethod.MTD, remove_tmp=True)

            with tempfile.TemporaryDirectory() as tmp_dir:
                prod.output = tmp_dir

                # Extent
                LOGGER.info("Computing STAC item")
                item: pystac.Item = prod.stac.create_item()
                LOGGER.info(prod.stac)

                # Object type
                compare(
                    item.STAC_OBJECT_TYPE,
                    pystac.STACObjectType.ITEM,
                    "item.STAC_OBJECT_TYPE",
                )

                # Geometry and bbox
                compare(
                    item.bbox,
                    list(prod.extent().to_crs(WGS84).bounds.values[0]),
                    "item.bbox",
                )
                if prod.is_ortho:
                    geometry_fct = prod.footprint
                else:
                    geometry_fct = prod.extent

                compare(
                    item.geometry,
                    mapping(geometry_fct().to_crs(WGS84).geometry.values[0]),
                    "item.geometry",
                )

                # Datetime
                compare(item.datetime, prod.datetime, "item.datetime")

                # ID
                compare(item.id, prod.condensed_name, "item.id")

                # Extensions
                if prod.sensor_type == SensorType.OPTICAL:
                    compare(
                        item.stac_extensions,
                        [
                            "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
                            "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
                            "https://stac-extensions.github.io/view/v1.0.0/schema.json",
                        ],
                        "item.stac_extensions",
                    )
                else:
                    compare(
                        item.stac_extensions,
                        [
                            "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
                            "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
                        ],
                        "item.stac_extensions",
                    )

                # Properties
                compare(
                    item.properties["tilename"],
                    prod.tile_name,
                    "tilename (item.properties)",
                )
                compare(
                    item.properties[TITLE],
                    prod.condensed_name,
                    f"{TITLE} (item.properties)",
                )
                compare(
                    item.properties[CONSTELLATION],
                    prod.constellation.value.lower(),
                    f"{CONSTELLATION} (item.properties)",
                )
                compare(
                    item.properties[GSD], prod.resolution, f"{GSD} (item.properties)"
                )
                compare(
                    item.properties[DATETIME],
                    prod.datetime.isoformat() + "Z",
                    f"{DATETIME} (item.properties)",
                )
                compare(
                    item.properties[PROJ_EPSG],
                    prod.crs().to_epsg(),
                    f"{PROJ_EPSG} (item.properties)",
                )
                compare(
                    item.properties[PROJ_WKT],
                    prod.crs().to_wkt(),
                    f"{PROJ_WKT} (item.properties)",
                )
                compare(
                    item.properties[PROJ_BBOX],
                    list(prod.extent().bounds.values[0]),
                    f"{PROJ_BBOX} (item.properties)",
                )
                compare(
                    item.properties[PROJ_GEOMETRY],
                    mapping(geometry_fct().geometry.values[0]),
                    f"{PROJ_GEOMETRY} (item.properties)",
                )

                if prod.is_ortho:
                    transform, width, height, _ = prod.default_transform()
                    compare(
                        item.properties[PROJ_SHAPE],
                        [height, width],
                        f"{PROJ_SHAPE} (item.properties)",
                    )
                    compare(
                        item.properties[PROJ_TRANSFORM],
                        transform,
                        f"{PROJ_TRANSFORM} (item.properties)",
                    )

                # TODO: Add centroid

                if prod.sensor_type == SensorType.OPTICAL:
                    prod: OpticalProduct
                    try:
                        compare(
                            item.properties[EO_CC],
                            prod.get_cloud_cover(),
                            f"{EO_CC} (item.properties)",
                        )
                    except KeyError:
                        pass

                    sun_az, sun_el = prod.get_mean_sun_angles()
                    compare(
                        item.properties[VIEW_SUN_AZIMUTH],
                        sun_az,
                        f"{VIEW_SUN_AZIMUTH} (item.properties)",
                    )
                    compare(
                        item.properties[VIEW_SUN_ELEVATION],
                        sun_el,
                        f"{VIEW_SUN_ELEVATION} (item.properties)",
                    )

                    azimuth, off_nadir, incidence_angle = prod.get_mean_viewing_angles()
                    if azimuth is not None:
                        compare(
                            item.properties[VIEW_AZIMUTH],
                            azimuth,
                            f"{VIEW_AZIMUTH} (item.properties)",
                        )
                    if off_nadir is not None:
                        compare(
                            item.properties[VIEW_OFF_NADIR],
                            off_nadir,
                            f"{VIEW_OFF_NADIR} (item.properties)",
                        )
                    if incidence_angle is not None:
                        compare(
                            item.properties[VIEW_INCIDENCE_ANGLE],
                            incidence_angle,
                            f"{VIEW_INCIDENCE_ANGLE} (item.properties)",
                        )

                # Assets
                if prod.sensor_type == SensorType.OPTICAL:
                    existing_bands = prod.get_existing_bands()
                    nof_assets = len(existing_bands)

                    if prod.constellation not in [
                        Constellation.S2,
                        Constellation.S2_THEIA,
                    ]:
                        if NARROW_NIR in existing_bands:
                            nof_assets -= 1  # remove NARROW NIR, except for S2
                    if prod.constellation not in [
                        Constellation.S2,
                        Constellation.S2_THEIA,
                        Constellation.S3_OLCI,
                    ]:
                        if VRE_1 in existing_bands and VRE_2 in existing_bands:
                            nof_assets -= 1  # remove one VRE, except for S2 and S3 OLCI
                        if VRE_1 in existing_bands and VRE_3 in existing_bands:
                            nof_assets -= 1  # remove one VRE, except for S2 and S3 OLCI
                    if prod.instrument == LandsatInstrument.TM:
                        if TIR_1 in existing_bands and TIR_2 in existing_bands:
                            nof_assets -= 1  # remove one TIR for TM data
                else:
                    prod: SarProduct
                    existing_bands = prod._get_raw_bands()
                    nof_assets = len(existing_bands)

                if prod.get_quicklook_path():
                    nof_assets += 1

                compare(len(item.assets), nof_assets, "number of assets")

                for band_name, band in item.assets.items():
                    band: pystac.Asset
                    if band_name == "thumbnail":
                        pass  # TODO
                    else:
                        eoreader_name_str = band.extra_fields["eoreader_name"]
                        if prod.sensor_type == SensorType.OPTICAL:
                            eoreader_name = SpectralBandNames.from_value(
                                eoreader_name_str
                            )
                        else:
                            eoreader_name = SarBandNames.from_value(eoreader_name_str)

                        prod_band: Union[SpectralBand, SarBand] = prod.bands[
                            eoreader_name
                        ]
                        compare(band_name, prod_band.name, "band name")

                        eo_band = band.extra_fields[EO_BANDS][0]
                        compare(eo_band["name"], prod_band.name, f"{EO_BANDS} name")
                        try:
                            compare(
                                eo_band["common_name"],
                                prod_band.common_name.value,
                                f"{EO_BANDS} common_name",
                            )
                        except KeyError:
                            pass
                        compare(
                            eo_band["description"],
                            prod_band.description,
                            f"{EO_BANDS} description",
                        )

                        if prod.sensor_type == SensorType.OPTICAL:
                            prod_band: SpectralBand
                            compare(
                                eo_band["center_wavelength"],
                                prod_band.center_wavelength,
                                f"{EO_BANDS} center_wavelength",
                            )
                            compare(
                                eo_band["full_width_half_max"],
                                prod_band.full_width_half_max,
                                f"{EO_BANDS} full_width_half_max",
                            )

                        compare(
                            band.extra_fields[CONSTELLATION],
                            prod.constellation.value.lower(),
                            f"band.extra_fields: {CONSTELLATION}",
                        )
                        compare(
                            band.extra_fields[GSD],
                            prod_band.gsd,
                            f"band.extra_fields: {GSD}",
                        )
                        compare(band.roles, [prod_band.asset_role], "band roles")
                        compare(band.title, prod_band.name, "band title")

                        # TODO: Add media_type and other common mtd when needed


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
    _test_core_optical("*IMG_SPOT7*")


@s3_env
@dask_env
def test_wv02_wv03():
    """Function testing the support of WorldView-2/3 constellations"""
    # This test orthorectifies DIMAP data, so we need a DEM stored on disk
    _test_core_optical("*P001_MUL*")


@s3_env
@dask_env
def test_ge01_wv04():
    """Function testing the support of GeoEye-1/WorldView-4 constellations"""
    _test_core_optical("*P001_PSH*")


@s3_env
@dask_env
def test_vs1():
    """Function testing the support of Vision-1 constellation"""
    _test_core_optical("*VIS1_MS4*")


@s3_env
@dask_env
def test_sv1():
    """Function testing the support of SuperView-1 constellation"""
    _test_core_optical("*0001_01*")


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
