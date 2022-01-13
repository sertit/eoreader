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
__all__ = [
    "Product",
    "SensorType",
]

from .product import Product, SensorType

__all__ += [
    "CustomProduct",
    "NAME",
    "ACQ_DATETIME",
    "BAND_MAP",
    "PLATFORM",
    "DEF_RES",
    "PROD_TYPE",
]
from .custom_product import (
    CustomProduct,
    NAME,
    ACQ_DATETIME,
    BAND_MAP,
    PLATFORM,
    DEF_RES,
    PROD_TYPE,
)

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
    "Spot6Product",
    "Spot7Product",
    "MaxarProduct",
    "MaxarProductType",
    "MaxarSatId",
    "MaxarBandId",
]
from .optical.vhr_product import VhrProduct
from .optical.dimap_product import DimapBandCombination, DimapProduct, DimapProductType
from .optical.pld_product import PldProduct
from .optical.spot6_product import Spot6Product
from .optical.spot7_product import Spot7Product
from .optical.maxar_product import (
    MaxarProduct,
    MaxarProductType,
    MaxarSatId,
    MaxarBandId,
)

# Planet
__all__ += [
    "PlaProduct",
    "PlaProductType",
    "PlaInstrument",
]
from .optical.pla_product import PlaProduct, PlaProductType, PlaInstrument

# Landsat
__all__ += [
    "LandsatProduct",
    "LandsatProductType",
    "LandsatCollection",
    "L1Product",
    "L2Product",
    "L3Product",
    "L4Product",
    "L5Product",
    "L7Product",
    "L8Product",
]
from .optical.landsat_product import (
    LandsatProduct,
    LandsatProductType,
    LandsatCollection,
)
from .optical.l1_product import L1Product
from .optical.l2_product import L2Product
from .optical.l3_product import L3Product
from .optical.l4_product import L4Product
from .optical.l5_product import L5Product
from .optical.l7_product import L7Product
from .optical.l8_product import L8Product

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
    "CosmoProduct",
    "CosmoProductType",
    "CosmoPolarization",
    "CsgProduct",
    "CsgSensorMode",
    "CskProduct",
    "CskSensorMode",
    "IceyeProduct",
    "IceyeProductType",
    "IceyeSensorMode",
    "RcmProduct",
    "RcmPolarization",
    "RcmProductType",
    "RcmSensorMode",
    "Rs2Product",
    "Rs2ProductType",
    "Rs2Polarization",
    "Rs2SensorMode",
    "S1Product",
    "S1SensorMode",
    "S1ProductType",
    "TsxProduct",
    "TsxPolarization",
    "TsxSatId",
    "TsxProductType",
    "TsxSensorMode",
]
from .sar.sar_product import SarProduct, SarProductType
from .sar.cosmo_product import CosmoProduct, CosmoProductType, CosmoPolarization
from .sar.csg_product import CsgProduct, CsgSensorMode
from .sar.csk_product import CskProduct, CskSensorMode
from .sar.iceye_product import IceyeProduct, IceyeProductType, IceyeSensorMode
from .sar.rcm_product import RcmProduct, RcmPolarization, RcmProductType, RcmSensorMode
from .sar.rs2_product import Rs2Product, Rs2ProductType, Rs2Polarization, Rs2SensorMode
from .sar.s1_product import S1Product, S1SensorMode, S1ProductType
from .sar.tsx_product import (
    TsxProduct,
    TsxPolarization,
    TsxSatId,
    TsxProductType,
    TsxSensorMode,
)
