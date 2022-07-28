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
STAC utils
"""
import os
from datetime import datetime
from pprint import pformat
from typing import Any

import geopandas as gpd
from sertit.vectors import WGS84
from shapely.geometry import mapping

from eoreader.stac._stac_keywords import DESCRIPTION, GSD, TITLE


def fill_common_mtd(asset: Any, prod, **kwargs) -> None:
    """
    Fill common metadata of STAC assets or items
    Args:
        asset (pystac.Asset, pystac.Item): Asset or item
        prod (product): EOReader product
        **kwargs: Additional arguments
    """
    # Basics
    asset.common_metadata.title = kwargs.get(TITLE)
    asset.common_metadata.description = kwargs.get(DESCRIPTION)

    # Date and Time
    asset.common_metadata.created = datetime.utcnow()
    asset.common_metadata.updated = None  # TODO

    # Licensing
    # asset.common_metadata.license = None  # Collection level if possible

    # Provider
    # asset.common_metadata.providers = None  # Collection level if possible

    # Date and Time Range
    asset.common_metadata.start_datetime = None  # TODO
    asset.common_metadata.end_datetime = None  # TODO

    # Instrument
    asset.common_metadata.platform = None  # TODO
    asset.common_metadata.instruments = None  # TODO
    asset.common_metadata.constellation = prod.constellation.value.lower()
    asset.common_metadata.mission = None
    asset.common_metadata.gsd = kwargs.get(GSD)


def gdf_to_geometry(gdf: gpd.GeoDataFrame) -> dict:
    """
    Convert a geodataframe to a STAC geometry
    Args:
        gdf (gpd.GeoDataFrame): Geodataframe to convert to geometry

    Returns:
        dict: STAC Geometry
    """
    return mapping(gdf.geometry.values[0])


def gdf_to_bbox(gdf: gpd.GeoDataFrame) -> list:
    """
    Convert a geodataframe to a STAC bbox
    Args:
        gdf (gpd.GeoDataFrame): Geodataframe to convert to bbox

    Returns:
        dict: STAC bbox
    """
    return list(gdf.bounds.values[0])


def gdf_to_centroid(gdf: gpd.GeoDataFrame) -> dict:
    """
    Convert a geodataframe to a STAC centroid
    Args:
        gdf (gpd.GeoDataFrame): Geodataframe to convert to centroid

    Returns:
        dict: STAC centroid
    """
    centroid = gdf.centroid.to_crs(WGS84).values[0]
    return {"lat": centroid.y, "lon": centroid.x}


def repr_multiline_str(to_str: Any, nof_tabs: int) -> str:
    """
    Format multiline string repr of a list, dict... by adding tabs at the beginning of every new line.

    Begins with a new line.

    Args:
        to_str (Any): List, dict... to convert to tabbed string
        nof_tabs (int): Number of tabs to put at the beginning of the lines

    Returns:

    """
    nof_tabs_str = "\t" * nof_tabs
    return f"\n{nof_tabs_str}" + f"{nof_tabs_str}".join(
        pformat(to_str).splitlines(True)
    )


def get_media_type(band_path: str) -> Any:
    """
    Get media type

    Args:
        band_path (str): Band path

    Returns:
        Any: Media Type

    """
    import pystac

    suffix = os.path.splitext(band_path)[-1]
    if suffix.lower() in [".tiff", ".tif"]:
        # Manage COGs
        media_type = pystac.MediaType.GEOTIFF
    elif suffix.lower() == ".jp2":
        media_type = pystac.MediaType.JPEG2000
    elif suffix.lower() == ".xml":
        media_type = pystac.MediaType.XML
    elif suffix.lower() == ".png":
        media_type = pystac.MediaType.PNG
    elif suffix.lower() in [".jpeg", ".jpg"]:
        media_type = pystac.MediaType.JPEG
    elif suffix.lower() == ".til":
        media_type = None  # Not existing
    elif suffix.lower() == ".nc":
        media_type = None  # Not existing
    else:
        media_type = None  # Not recognized

    return media_type
