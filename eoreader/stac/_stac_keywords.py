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
""" STAC KEYWORDS """
from sertit.misc import ListEnum

__all__ = [
    "ID",
    "GSD",
    "TITLE",
    "DATETIME",
    "GEOMETRY",
    "BBOX",
    "STAC_EXTENSIONS",
    "NA",
    "CONSTELLATION",
    "PLATFORM",
    "INSTRUMENTS",
    "EO_BANDS",
    "EO_CC",
    "NAME",
    "COMMON_NAME",
    "DESCRIPTION",
    "CENTER_WV",
    "WV_MIN",
    "WV_MAX",
    "FWHM",
    "SOLAR_ILLUMINATION",
    "StacCommonNames",
    "ASSET_ROLE",
    "REFLECTANCE",
    "BT",
    "SATURATION",
    "CLOUD",
    "CLOUD_SHADOW",
    "AMPLITUDE",
    "INTENSITY",
    "COHERENCE",
    "PROJ_BBOX",
    "PROJ_EPSG",
    "PROJ_WKT",
    "PROJ_SHAPE",
    "PROJ_GEOMETRY",
    "PROJ_TRANSFORM",
    "PROJ_CENTROID",
    "VIEW_AZIMUTH",
    "VIEW_OFF_NADIR",
    "VIEW_SUN_AZIMUTH",
    "VIEW_INCIDENCE_ANGLE",
    "VIEW_SUN_ELEVATION",
]

# MISC

ID = "id"
GSD = "gsd"
TITLE = "title"
GEOMETRY = "geometry"
BBOX = "bbox"
DATETIME = "datetime"
NA = "N/A"
CONSTELLATION = "constellation"
PLATFORM = "platform"
INSTRUMENTS = "instruments"
STAC_EXTENSIONS = "stac_extensions"

# ---------------- Electro-Optical Extension Specification ----------------

# Additional Field Information: https://github.com/stac-extensions/eo/#additional-field-information
EO_BANDS = "eo:bands"
EO_CC = "eo:cloud_cover"

# Band object: https://github.com/stac-extensions/eo/#band-object
NAME = "name"
COMMON_NAME = "common_name"
DESCRIPTION = "description"
CENTER_WV = "center_wavelength"
WV_MIN = "min_wavelength"
WV_MAX = "max_wavelength"
FWHM = "full_width_half_max"
SOLAR_ILLUMINATION = "solar_illumination"


# Band common names: https://github.com/stac-extensions/eo/#common-band-names
class StacCommonNames(ListEnum):
    COASTAL = "coastal"  # Band 1, Sentinel-2
    BLUE = "blue"  # Band 2, Sentinel-2
    GREEN = "green"  # Band 3, Sentinel-2
    RED = "red"  # Band 4, Sentinel-2
    YELLOW = "yellow"  # Band Oa07, Sentinel-3 OLCI
    PAN = "pan"  # Band 8, Landsat OLI
    RE = "rededge"  # Band 5,6,7, Sentinel-2
    NIR = "nir"  # Band 8, Sentinel-2
    NIR08 = "nir08"  # Band 8a, Sentinel-2
    NIR09 = "nir09"  # Band 9, Sentinel-2
    CIRRUS = "cirrus"  # Band 10, Sentinel-2
    SWIR16 = "swir16"  # Band 11, Sentinel-2
    SWIR22 = "swir22"  # Band 12, Sentinel-2
    LWIR = "lwir"  # Band 6, Landsat TM
    LWIR11 = "lwir11"  # Band 10, Landsat TIRS
    LWIR12 = "lwir12"  # Band 11, Landsat TIRS


# Asset roles: https://github.com/stac-extensions/eo/#best-practices
ASSET_ROLE = "asset_role"

# Optical
REFLECTANCE = "reflectance"
BT = "brilliance_temperature"
SATURATION = "saturation"
CLOUD = "cloud"
CLOUD_SHADOW = "cloud-shadow"

# SAR
INTENSITY = "intensity"
AMPLITUDE = "amplitude"
COHERENCE = "coherence"

# ---------------- Projection Extension Specification ----------------

# https://github.com/stac-extensions/projection/
PROJ_EPSG = "proj:epsg"
PROJ_WKT = "proj:wkt2"
PROJ_GEOMETRY = "proj:geometry"
PROJ_BBOX = "proj:bbox"
PROJ_CENTROID = "proj:centroid"
PROJ_SHAPE = "proj:shape"
PROJ_TRANSFORM = "proj:transform"

# ---------------- View Extension Specification ----------------

# https://github.com/stac-extensions/view/
VIEW_OFF_NADIR = "view:off_nadir"
VIEW_INCIDENCE_ANGLE = "view:incidence_angle"
VIEW_AZIMUTH = "view:azimuth"
VIEW_SUN_AZIMUTH = "view:sun_azimuth"
VIEW_SUN_ELEVATION = "view:sun_elevation"
