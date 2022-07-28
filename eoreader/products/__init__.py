# -*- coding: utf-8 -*-
# Copyright 2022, SERTIT-ICube - France, https://sertit.unistra.fr/
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

from .product import Product, SensorType, OrbitDirection

__all__ += [
    "CustomProduct",
    "CustomFields",
]
from .custom_product import CustomProduct, CustomFields

# -- Optical --
__all__ += [
    "OpticalProduct",
    "CleanMethod",
]
from .optical.optical_product import OpticalProduct, CleanMethod

# VHR
__all__ += [
    "VhrProduct",
    "DimapBandCombination",
    "DimapProduct",
    "DimapProductType",
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
]
from .optical.vhr_product import VhrProduct
from .optical.dimap_product import DimapBandCombination, DimapProduct, DimapProductType
from .optical.pld_product import PldProduct
from .optical.spot67_product import Spot67Product
from .optical.maxar_product import (
    MaxarProduct,
    MaxarProductType,
    MaxarSatId,
    MaxarBandId,
)
from .optical.vis1_product import Vis1Product, Vis1ProductType, Vis1BandCombination
from .optical.sv1_product import Sv1Product, Sv1ProductType, Sv1BandCombination

# SPOT4/5
__all__ += [
    "Spot45ProductType",
    "Spot4BandCombination",
    "Spot5BandCombination",
    "Spot45Product",
]
from .optical.spot45_product import (
    Spot45ProductType,
    Spot4BandCombination,
    Spot5BandCombination,
    Spot45Product,
)

# PlanetScope
__all__ += [
    "PlaProduct",
    "PlaProductType",
    "PlaInstrument",
]
from .optical.pla_product import PlaProduct, PlaProductType, PlaInstrument

# SkySat
__all__ += [
    "SkyProductType",
    "SkyProduct",
    "SkyInstrument",
]
from .optical.sky_product import SkyProductType, SkyProduct, SkyInstrument

# Landsat
__all__ += [
    "LandsatProduct",
    "LandsatProductType",
    "LandsatCollection",
    "LandsatInstrument",
]
from .optical.landsat_product import (
    LandsatProduct,
    LandsatProductType,
    LandsatCollection,
    LandsatInstrument,
)

# Sentinel
__all__ += [
    "S2Product",
    "S2ProductType",
    "S2GmlMasks",
    "S2Jp2Masks",
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
from .optical.s2_product import S2Product, S2ProductType, S2GmlMasks, S2Jp2Masks
from .optical.s2_theia_product import S2TheiaProduct
from .optical.s3_product import S3Product, S3ProductType, S3DataType, S3Instrument
from .optical.s3_olci_product import S3OlciProduct
from .optical.s3_slstr_product import (
    S3SlstrProduct,
    SlstrRadAdjustTuple,
    SlstrRadAdjust,
    SlstrView,
    SlstrStripe,
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
    "SaocomProduct",
    "SaocomProductType",
    "SaocomPolarization",
    "SaocomSensorMode" "TsxProduct",
    "TsxPolarization",
    "TsxSatId",
    "TsxProductType",
    "TsxSensorMode",
]
from .sar.sar_product import SarProduct, SarProductType, SnapDems
from .sar.cosmo_product import CosmoProduct, CosmoProductType
from .sar.csg_product import CsgProduct, CsgSensorMode
from .sar.csk_product import CskProduct, CskSensorMode
from .sar.iceye_product import IceyeProduct, IceyeProductType, IceyeSensorMode
from .sar.rcm_product import RcmProduct, RcmProductType, RcmSensorMode
from .sar.rs2_product import Rs2Product, Rs2ProductType, Rs2SensorMode
from .sar.s1_product import S1Product, S1SensorMode, S1ProductType
from .sar.saocom_product import (
    SaocomProduct,
    SaocomProductType,
    SaocomPolarization,
    SaocomSensorMode,
)
from .sar.tsx_product import (
    TsxProduct,
    TsxPolarization,
    TsxSatId,
    TsxProductType,
    TsxSensorMode,
)
