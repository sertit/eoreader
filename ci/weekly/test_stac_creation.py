"""Script testing the creaction of STAC Items from EOReader Products."""

import contextlib
import logging
import os
import sys
import tempfile

import pystac
import pytest
import xarray as xr
from sertit import path
from sertit.vectors import WGS84
from shapely.geometry import mapping

from ci.scripts_utils import (
    CI_EOREADER_S3,
    READER,
    compare,
    dask_env,
    opt_path,
    reduce_verbosity,
    s3_env,
    sar_path,
)
from eoreader import EOREADER_NAME
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
from eoreader.products.optical.hls_product import HlsProductType
from eoreader.reader import CheckMethod, Constellation
from eoreader.stac import EO_BANDS
from eoreader.stac._stac_keywords import (
    CONSTELLATION,
    DATETIME,
    EO_CC,
    GSD,
    PROJ_BBOX,
    PROJ_CODE,
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

LOGGER = logging.getLogger(EOREADER_NAME)

reduce_verbosity()


def _test_core_optical(pattern: str, expected_assets, debug=False, **kwargs):
    """
    Core function testing optical data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    _test_core(pattern, opt_path(), debug, expected_assets, **kwargs)


def _test_core_sar(pattern: str, debug=False, **kwargs):
    """
    Core function testing SAR data

    Args:
        pattern (str): Pattern of the satellite
        debug (bool): Debug option
    """
    _test_core(pattern, sar_path(), debug, **kwargs)


def _test_core(
    pattern: str,
    prod_dir: str,
    debug=False,
    expected_assets=None,
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
        pattern_paths = path.get_file_in_dir(
            prod_dir, pattern, exact_name=True, get_list=True
        )

        for pattern_path in pattern_paths:
            LOGGER.info(
                f"%s on drive %s ({CI_EOREADER_S3}: %s)",
                pattern_path.name,
                pattern_path.drive,
                os.getenv(CI_EOREADER_S3),
            )

            # Open product and set output
            prod: Product = READER.open(
                pattern_path, method=CheckMethod.MTD, remove_tmp=True
            )

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
                geometry_fct = prod.footprint if prod.is_ortho else prod.extent

                compare(
                    item.geometry,
                    mapping(geometry_fct().to_crs(WGS84).geometry.iat[0]),
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
                            "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
                            "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
                            "https://stac-extensions.github.io/view/v1.0.0/schema.json",
                        ],
                        "item.stac_extensions",
                    )
                else:
                    compare(
                        item.stac_extensions,
                        [
                            "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
                            "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
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
                    item.properties[GSD], prod.pixel_size, f"{GSD} (item.properties)"
                )
                compare(
                    item.properties[DATETIME],
                    prod.datetime.isoformat() + "Z",
                    f"{DATETIME} (item.properties)",
                )
                compare(
                    item.properties[PROJ_CODE],
                    f"EPSG:{prod.crs().to_epsg()}",
                    f"{PROJ_CODE} (item.properties)",
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
                    mapping(geometry_fct().geometry.iat[0]),
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
                        list(transform),
                        f"{PROJ_TRANSFORM} (item.properties)",
                    )

                # TODO: Add centroid

                if prod.sensor_type == SensorType.OPTICAL:
                    prod: OpticalProduct
                    with contextlib.suppress(KeyError):
                        compare(
                            item.properties[EO_CC],
                            prod.get_cloud_cover(),
                            f"{EO_CC} (item.properties)",
                        )

                    sun_az, sun_zen = prod.get_mean_sun_angles()
                    sun_el = 90 - sun_zen
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
                    assert -90 < sun_el < 90

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
                is_not_s2 = (
                    prod.constellation not in [Constellation.S2, Constellation.S2_THEIA]
                    and prod.product_type != HlsProductType.S30
                )

                if prod.sensor_type == SensorType.OPTICAL:
                    existing_bands = prod.get_existing_bands()
                    nof_assets = len(existing_bands)
                    LOGGER.debug(
                        f"Nof existing bands to init nof assets: nof_assets={nof_assets}"
                    )

                    # Remove NARROW NIR, except for S2
                    if is_not_s2 and NARROW_NIR in existing_bands:
                        nof_assets -= 1
                        LOGGER.debug(
                            f"Remove one asset as NARROW NIR and NIR are the same band: nof_assets={nof_assets}"
                        )

                    # Keep only one VRE, except for
                    # - S2 and S3 OLCI (VRE1 is always existing if VRE bands are present)
                    # - WV Legion which has VRE 1 and VRE 2
                    if (
                        is_not_s2
                        and prod.constellation != Constellation.S3_OLCI
                        and VRE_1 in existing_bands
                    ):
                        if (
                            prod.constellation != Constellation.WVLG
                            and VRE_2 in existing_bands
                        ):
                            nof_assets -= 1
                            LOGGER.debug(
                                f"Remove one asset as VRE_1 and VRE_2 are the same band: nof_assets={nof_assets}"
                            )
                        if VRE_3 in existing_bands:
                            nof_assets -= 1
                            LOGGER.debug(
                                f"Remove one asset as VRE_1 and VRE_3 are the same band: nof_assets={nof_assets}"
                            )

                    # Remove one TIR for TM data
                    if (
                        prod.instrument == LandsatInstrument.TM
                        and TIR_1 in existing_bands
                        and TIR_2 in existing_bands
                    ):
                        nof_assets -= 1
                        LOGGER.debug(
                            f"Remove one asset as TIR_1 and TIR_2 are the same band: nof_assets={nof_assets}"
                        )
                else:
                    prod: SarProduct
                    existing_bands = prod._get_raw_bands()
                    nof_assets = len(existing_bands)

                if prod.get_quicklook_path():
                    nof_assets += 1
                    LOGGER.debug(f"Add the quicklook as asset: nof_assets={nof_assets}")

                if expected_assets is None:
                    compare(len(item.assets), nof_assets, "number of assets")
                else:
                    compare(len(item.assets), expected_assets, "number of assets")

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

                        prod_band: SpectralBand | SarBand = prod.bands[eoreader_name]
                        compare(band_name, prod_band.name, "band name")

                        eo_band = band.extra_fields[EO_BANDS][0]
                        compare(eo_band["name"], prod_band.name, f"{EO_BANDS} name")
                        with contextlib.suppress(KeyError):
                            compare(
                                eo_band["common_name"],
                                prod_band.common_name.value,
                                f"{EO_BANDS} common_name",
                            )

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

                # Add to catalog and save it to see if we can add the item (and if it's serializable)
                catalog_path = os.path.join(tmp_dir, "catalog.json")
                catalog = pystac.Catalog(
                    id="SERTIT_101",
                    description="SERTIT's Catalog",
                    title="SERTIT Catalog",
                    href=catalog_path,
                )
                catalog.add_item(item)
                catalog.normalize_and_save(
                    tmp_dir, catalog_type=pystac.CatalogType.SELF_CONTAINED
                )


test_optical_constellations_cases = [
    pytest.param("*VENUS*", {}, 12, id="venus"),
    pytest.param("*S2*_MSI*", {}, 11, id="s2"),
    pytest.param("*SENTINEL2*", {}, 11, id="s2_theia"),
    pytest.param("*S3*_OL_1_*", {}, 10, id="s3_olci"),
    pytest.param(
        "*S3*_SL_1_*", {SLSTR_RAD_ADJUST: SlstrRadAdjust.SNAP}, 12, id="s3_slstr"
    ),
    pytest.param("*LC09*", {}, 12, id="landsat_9"),
    pytest.param("*LC08*", {}, 12, id="landsat_8"),
    pytest.param("*LE07*", {}, 12, id="landsat_7"),
    pytest.param("*LT05*", {}, 12, id="landsat_5_tm"),
    pytest.param("*LT04*", {}, 12, id="landsat_4_tm"),
    pytest.param("*LM04*", {}, 12, id="landsat_4_mss"),
    pytest.param("*LM03*", {}, 12, id="landsat_3_mss"),
    pytest.param("*LM02*", {}, 12, id="landsat_2_mss"),
    pytest.param("*LM01*", {}, 12, id="landsat_1_mss"),
    pytest.param("*HLS*", {}, 12, id="hls"),
    pytest.param("*202*1014*", {}, 12, id="planet"),
    pytest.param("*ssc*", {}, 12, id="skysat"),
    pytest.param("*_RE4_*", {}, 12, id="rapideye"),
    pytest.param("*IMG_PHR*", {}, 12, id="pleiades"),
    pytest.param("*IMG_*_PNEO*", {}, 12, id="pleiades_neo"),
    pytest.param("*SP04*", {}, 12, id="spot4"),
    pytest.param("*SP05*", {}, 12, id="spot5"),
    pytest.param("*IMG_SPOT6*", {}, 12, id="spot6"),
    pytest.param("*IMG_SPOT7*", {}, 12, id="spot7"),
    pytest.param("*P001_MUL*", {}, 12, id="wv02_wv03_legion"),
    pytest.param("*P001_PSH*", {}, 12, id="ge01_wv04"),
    pytest.param("*VIS1_MS4*", {}, 12, id="vision1"),
    pytest.param("*0001_01*", {}, 12, id="superview1"),
    pytest.param("*DE2_*", {}, 12, id="geosat2"),
    pytest.param(
        "*LM05*",
        {},
        12,
        id="landsat_5_mss",
        marks=pytest.mark.skipif(
            sys.platform == "win32" or os.getenv(CI_EOREADER_S3) == "0",
            reason="Weirdly, Landsat-5 image shape is not the same with data from disk or S3. Skipping test on disk",
        ),
    ),
]


@pytest.mark.parametrize(
    "pattern, kwargs, expected_assets", test_optical_constellations_cases
)
@s3_env
@dask_env
def test_optical_constellations(pattern, kwargs, expected_assets):
    _test_core_optical(pattern, expected_assets, **kwargs)


test_sar_constellations_cases = [
    pytest.param("*S1*_IW*", {}, id="sentinel_1"),
    pytest.param("*csk_*", {}, id="cosmo_skymed"),
    pytest.param("*CSG_*", {}, id="cosmo_skymed_2"),
    pytest.param("*TSX*", {}, id="terrasar_x"),
    pytest.param("*TDX*", {}, id="tandem_x"),
    pytest.param("*RS2_*", {}, id="radarsat_2"),
    pytest.param("*RCM*", {}, id="radarsat_constellation"),
    pytest.param("*SC_*", {}, id="iceye"),
    pytest.param("*SAO*", {}, id="saocom"),
    pytest.param("*CAPELLA*", {}, id="capella"),
]


@pytest.mark.parametrize("pattern, kwargs", test_sar_constellations_cases)
@s3_env
@dask_env
def test_sar_constellations(pattern, kwargs):
    _test_core_sar(pattern, **kwargs)
