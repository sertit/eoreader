"""Mask tests."""

import logging
import os

import tempenv
from sertit import AnyPath, ci, path

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
)
from eoreader import EOREADER_NAME
from eoreader.bands import (
    AOT,
    GREEN,
    SCL,
    WVP,
    DimapV2MaskBandNames,
    HlsMaskBandNames,
    LandsatMaskBandNames,
    PlanetMaskBandNames,
    S2MaskBandNames,
    S2TheiaMaskBandNames,
)
from eoreader.env_vars import CI_EOREADER_BAND_FOLDER

LOGGER = logging.getLogger(EOREADER_NAME)
WRITE_ON_DISK = False

reduce_verbosity()


@s3_env
def test_s2_l2a_specific_bands(tmp_path):
    """Test S2 L2A specific bands"""
    # Get paths
    prod_path = opt_path().joinpath(
        "S2B_MSIL2A_20210517T103619_N7990_R008_T30QVE_20211004T113819.SAFE"
    )

    # Open with a window
    with READER.open(prod_path, remove_tmp=not WRITE_ON_DISK) as prod:
        if WRITE_ON_DISK:
            tmp_path = AnyPath(
                "/mnt", "ds2_db3", "CI", "eoreader", "OUTPUT", prod.condensed_name
            )
        prod.output = tmp_path / prod.condensed_name
        stack_path = prod.output / f"{prod.condensed_name}_s2_l2a.tif"
        true_path = get_ci_data_dir().joinpath(prod.condensed_name, stack_path.name)
        prod.stack([AOT, WVP, SCL], pixel_size=600, stack_path=stack_path)

        ci.assert_raster_equal(stack_path, true_path)


@dask_env
def _test_masks(tmp_path, prod_regex, masks, **kwargs):
    pattern_paths = path.get_file_in_dir(
        opt_path(), prod_regex, exact_name=False, get_list=True
    )

    for prod_path in pattern_paths:
        LOGGER.info(
            f"%s on drive %s ({CI_EOREADER_S3}: %s)",
            prod_path.name,
            prod_path.drive,
            os.getenv(CI_EOREADER_S3),
        )

        with READER.open(prod_path, remove_tmp=not WRITE_ON_DISK) as prod:
            if WRITE_ON_DISK:
                tmp_path = AnyPath(
                    "/mnt", "ds2_db3", "CI", "eoreader", "OUTPUT", prod.condensed_name
                )
            prod.output = tmp_path / prod.condensed_name
            stack_path = prod.output / f"{prod.condensed_name}_masks.tif"
            true_path = get_ci_data_dir().joinpath(prod.condensed_name, stack_path.name)

            # DO NOT REPROJECT BANDS (WITH GDAL / SNAP) --> WAY TOO SLOW
            os.environ[CI_EOREADER_BAND_FOLDER] = str(
                get_ci_data_dir().joinpath(prod.condensed_name)
            )

            valid_bands = [b for b in masks.to_value_list() if prod.has_band(b)]

            prod.stack(
                valid_bands,
                pixel_size=test_satellites.get_pixel_size(prod),
                stack_path=stack_path,
                **kwargs,
            )

            ci.assert_raster_equal(stack_path, true_path)


@s3_env
def test_dimap_v2_masks(tmp_path):
    """Test DIMAP V2 masks"""
    # Non-ortho
    with tempenv.TemporaryEnvironment(
        {
            "EOREADER_DEM_PATH": os.path.join(
                get_db_dir_on_disk(), *test_satellites.MERIT_DEM_SUB_DIR_PATH
            )
        }
    ):
        _test_masks(tmp_path, "SPOT7", DimapV2MaskBandNames)

    # WGS84
    _test_masks(tmp_path, "SPOT6", DimapV2MaskBandNames)

    # UTM
    _test_masks(tmp_path, "PHR", DimapV2MaskBandNames)


@s3_env
def test_hls_masks(tmp_path):
    """Test HLS masks"""
    _test_masks(tmp_path, "HLS.L30", HlsMaskBandNames)


@s3_env
def test_landsat_masks(tmp_path):
    """Test Landsat masks"""
    # COL1
    _test_masks(
        tmp_path, "LC08_L1GT_023030_20200518_20200527_01_T2", LandsatMaskBandNames
    )

    # COL2 L1
    _test_masks(
        tmp_path, "LC08_L1TP_200030_20201220_20210310_02_T1", LandsatMaskBandNames
    )

    # COL2 L2
    _test_masks(
        tmp_path, "LC09_L2SP_152041_20220828_20220830_02_T1", LandsatMaskBandNames
    )


@s3_env
def test_planet_masks(tmp_path):
    """Test Planet masks"""
    _test_masks(tmp_path, "20200926_100102_1014", PlanetMaskBandNames)


@s3_env
def test_s2_masks(tmp_path):
    """Test S2 masks"""
    # PB < 04.00
    _test_masks(
        tmp_path,
        "S2B_MSIL2A_20171227T105439_N0206_R051_T31UFP_20171227T130927.SAFE",
        S2MaskBandNames,
        associated_bands={
            "DETFOO": "RED",
            "TECQUA": "RED",
            "DEFECT": "RED",
            "NODATA": "RED",
            S2MaskBandNames.SATURA: ["RED", GREEN],
        },
    )

    # PB >= 04.00
    _test_masks(
        tmp_path,
        "S2B_MSIL2A_20210517T103619_N7990_R008_T30QVE_20211004T113819.SAFE",
        S2MaskBandNames,
        associated_bands={S2MaskBandNames.DETFOO: ["RED", GREEN], "QUALIT": "RED"},
    )


@s3_env
def test_s2_theia_masks(tmp_path):
    """Test S2 Theia masks"""
    _test_masks(
        tmp_path,
        "SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2",
        S2TheiaMaskBandNames,
        associated_bands={S2TheiaMaskBandNames.DFP: "RED", "SAT": ["RED", GREEN]},
    )


# TODO: Test Venus and Satellogic (with clouds)
