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
from ._stac_keywords import (
    AMPLITUDE,
    ASSET_ROLE,
    BBOX,
    BT,
    CENTER_WV,
    CLOUD,
    CLOUD_SHADOW,
    COHERENCE,
    COMMON_NAME,
    CONSTELLATION,
    DATETIME,
    DESCRIPTION,
    EO_BANDS,
    EO_CC,
    FWHM,
    GEOMETRY,
    GSD,
    ID,
    INSTRUMENTS,
    INTENSITY,
    NA,
    NAME,
    PLATFORM,
    PROJ_BBOX,
    PROJ_CENTROID,
    PROJ_EPSG,
    PROJ_GEOMETRY,
    PROJ_SHAPE,
    PROJ_TRANSFORM,
    PROJ_WKT,
    REFLECTANCE,
    SATURATION,
    SOLAR_ILLUMINATION,
    STAC_EXTENSIONS,
    TITLE,
    VIEW_AZIMUTH,
    VIEW_INCIDENCE_ANGLE,
    VIEW_OFF_NADIR,
    VIEW_SUN_AZIMUTH,
    VIEW_SUN_ELEVATION,
    WV_MAX,
    WV_MIN,
    StacCommonNames,
)

__all__ = _stac_keywords.__all__

from .stac_extensions import EoExt, ProjExt, ViewExt

__all__ += [
    "EoExt",
    "ViewExt",
    "ProjExt",
]

from .stac_item import OPTICAL_STAC_EXTENSIONS, SAR_STAC_EXTENSIONS, StacItem

__all__ += ["StacItem", "OPTICAL_STAC_EXTENSIONS", "SAR_STAC_EXTENSIONS"]
