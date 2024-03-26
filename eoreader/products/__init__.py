# -*- coding: utf-8 -*-
# Copyright 2024, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
SAR and Optical products
"""
# flake8: noqa
__all__ = ["Product", "SensorType", "OrbitDirection"]

from .product import OrbitDirection, Product, SensorType

__all__ += [
    "CustomProduct",
    "CustomFields",
]
from .custom_product import CustomFields, CustomProduct

# STAC products
__all__ += [
    "StacProduct",
]
from .stac_product import StacProduct

# -- Optical --
__all__ += [
    "OpticalProduct",
    "CleanMethod",
]
from .optical.optical_product import CleanMethod, OpticalProduct

# VHR
__all__ += [
    "VhrProduct",
    "DimapV1Product",
    "DimapV2Product",
    "DimapV2BandCombination",
    "DimapV2ProductType",
    "PldProduct",
    "Spot67Product",
    "MaxarProduct",
    "MaxarProductType",
    "MaxarSatId",
    "MaxarBandId",
    "Vis1Product",
    "Vis1ProductType",
    "Vis1BandCombination",
    "Sv1Product",
    "Sv1ProductType",
    "Sv1BandCombination",
    "Gs2Product",
    "Gs2ProductType",
    "Gs2BandCombination",
]
from .optical.dimap_v1_product import DimapV1Product
from .optical.dimap_v2_product import (
    DimapV2BandCombination,
    DimapV2Product,
    DimapV2ProductType,
)
from .optical.gs2_product import Gs2BandCombination, Gs2Product, Gs2ProductType
from .optical.maxar_product import (
    MaxarBandId,
    MaxarProduct,
    MaxarProductType,
    MaxarSatId,
)
from .optical.pld_product import PldProduct
from .optical.spot67_product import Spot67Product
from .optical.sv1_product import Sv1BandCombination, Sv1Product, Sv1ProductType
from .optical.vhr_product import VhrProduct
from .optical.vis1_product import Vis1BandCombination, Vis1Product, Vis1ProductType

# SPOT4/5
__all__ += [
    "Spot45ProductType",
    "Spot4BandCombination",
    "Spot5BandCombination",
    "Spot45Product",
]
from .optical.spot45_product import (
    Spot4BandCombination,
    Spot5BandCombination,
    Spot45Product,
    Spot45ProductType,
)

# Planet
__all__ += [
    "PlanetMaskType",
]

from .optical.planet_product import PlanetMaskType

# PlanetScope
__all__ += [
    "PlaProduct",
    "PlaProductType",
    "PlaInstrument",
]
from .optical.pla_product import PlaInstrument, PlaProduct, PlaProductType

# SkySat
__all__ += [
    "SkyProductType",
    "SkyProduct",
    "SkyInstrument",
]
from .optical.sky_product import SkyInstrument, SkyProduct, SkyProductType

# RapidEye
__all__ += [
    "ReProductType",
    "ReProduct",
    "ReInstrument",
]
from .optical.re_product import ReProduct, ReProductType

# Landsat
__all__ += [
    "LandsatProduct",
    "LandsatProductType",
    "LandsatCollection",
    "LandsatInstrument",
]
from .optical.landsat_product import (
    LandsatCollection,
    LandsatInstrument,
    LandsatProduct,
    LandsatProductType,
)

# Sentinel
__all__ += [
    "S2Product",
    "S2ProductType",
    "S2GmlMasks",
    "S2Jp2Masks",
    "S2StacProduct",
    "S2E84Product",
    "S2E84StacProduct",
    "S2MPCStacProduct",
    "S2TheiaProduct",
    "S3Product",
    "S3ProductType",
    "S3DataType",
    "S3Instrument",
    "S3SlstrProduct",
    "SlstrRadAdjustTuple",
    "SlstrRadAdjust",
    "SlstrView",
    "SlstrStripe",
]
from .optical.s2_e84_product import S2E84Product, S2E84StacProduct
from .optical.s2_mpc_product import S2MpcStacProduct
from .optical.s2_product import (
    S2GmlMasks,
    S2Jp2Masks,
    S2Product,
    S2ProductType,
    S2StacProduct,
)
from .optical.s2_theia_product import S2TheiaProduct
from .optical.s3_olci_product import S3OlciProduct
from .optical.s3_product import S3DataType, S3Instrument, S3Product, S3ProductType
from .optical.s3_slstr_product import (
    S3SlstrProduct,
    SlstrRadAdjust,
    SlstrRadAdjustTuple,
    SlstrStripe,
    SlstrView,
)

# -- SAR --
__all__ += [
    "SarProduct",
    "SarProductType",
    "SnapDems",
    "CosmoProduct",
    "CosmoProductType",
    "CsgProduct",
    "CsgSensorMode",
    "CskProduct",
    "CskSensorMode",
    "IceyeProduct",
    "IceyeProductType",
    "IceyeSensorMode",
    "RcmProduct",
    "RcmProductType",
    "RcmSensorMode",
    "Rs2Product",
    "Rs2ProductType",
    "Rs2SensorMode",
    "S1Product",
    "S1SensorMode",
    "S1ProductType",
    "S1RtcAsfProduct",
    "S1RtcProductType",
    "S1RtcMpcStacProduct",
    "SaocomProduct",
    "SaocomProductType",
    "SaocomPolarization",
    "SaocomSensorMode" "TsxProduct",
    "TsxPolarization",
    "TsxSatId",
    "TsxProductType",
    "TsxSensorMode",
    "CapellaProduct",
    "CapellaProductType",
    "CapellaSensorMode" "",
]
from .sar.capella_product import CapellaProduct, CapellaProductType, CapellaSensorMode
from .sar.cosmo_product import CosmoProduct, CosmoProductType
from .sar.csg_product import CsgProduct, CsgSensorMode
from .sar.csk_product import CskProduct, CskSensorMode
from .sar.iceye_product import IceyeProduct, IceyeProductType, IceyeSensorMode
from .sar.rcm_product import RcmProduct, RcmProductType, RcmSensorMode
from .sar.rs2_product import Rs2Product, Rs2ProductType, Rs2SensorMode
from .sar.s1_product import S1Product, S1ProductType, S1SensorMode
from .sar.s1_rtc_asf_product import S1RtcAsfProduct, S1RtcProductType
from .sar.s1_rtc_mpc_product import S1RtcMpcStacProduct
from .sar.saocom_product import (
    SaocomPolarization,
    SaocomProduct,
    SaocomProductType,
    SaocomSensorMode,
)
from .sar.sar_product import SarProduct, SarProductType, SnapDems
from .sar.tsx_product import (
    TsxPolarization,
    TsxProduct,
    TsxProductType,
    TsxSatId,
    TsxSensorMode,
)
