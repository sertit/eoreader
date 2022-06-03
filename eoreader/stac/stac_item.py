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
STAC object that will be passed as a `Product` attribute.
Implements STAC item and
`stable <https://github.com/radiantearth/stac-spec/blob/master/extensions/README.md#extension-maturity>_`
extensions:

- `STAC Item Specification <https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md>`_
    - Everything possible
- `STAC Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_
    - Cloud coverage (if existing)
- `STAC Projection Extension Specification <https://github.com/stac-extensions/projection/>`_
    - Projected (UTM) epsg, bbox, footprint, centroid...
- `STAC View Extension Specification <https://github.com/stac-extensions/view/>`_
    - Sun angles
    - Viewing position (in progress)
"""
from datetime import datetime

import geopandas as gpd
from sertit.vectors import WGS84

from eoreader import cache
from eoreader.stac import GSD, stac_utils
from eoreader.stac._stac_keywords import (
    BBOX,
    CONSTELLATION,
    DATETIME,
    GEOMETRY,
    ID,
    STAC_EXTENSIONS,
    TITLE,
)
from eoreader.stac.stac_extensions import EoExt, ProjExt, ViewExt
from eoreader.stac.stac_utils import (
    gdf_to_bbox,
    gdf_to_geometry,
    get_media_type,
    repr_multiline_str,
)

SAR_STAC_EXTENSIONS = [
    "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
    "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
]
OPTICAL_STAC_EXTENSIONS = [
    "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
    "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
    "https://stac-extensions.github.io/view/v1.0.0/schema.json",
]


class StacItem:
    """
    Class of STAC object, mapping EOReader products to STAC Items.
    Implements STAC Spec basic and extensions
    TODO
    """

    def __init__(self, prod, **kwargs):
        self.eo = EoExt(prod, **kwargs)
        """
        STAC Electro-Optical Extension Specification
        """
        self.proj = ProjExt(prod, **kwargs)
        """
        STAC Projection Extension Specification
        """
        self.view = ViewExt(prod, **kwargs)
        """
        STAC View Extension Specification
        """

        self._prod = prod

        # STAC fields
        self.id = self._prod.condensed_name
        self.datetime = self._prod.datetime
        self.geometry = gdf_to_geometry(self.geometry_fct())
        self.bbox = gdf_to_bbox(self.bbox_fct())
        self.extensions = (
            SAR_STAC_EXTENSIONS
            if self._prod.sensor_type.value == "SAR"
            else OPTICAL_STAC_EXTENSIONS
        )

        # Common mtd
        self.gsd = self._prod.resolution
        self.title = self._prod.condensed_name
        self.constellation = self._prod.constellation.value.lower()
        self.created = datetime.utcnow()

        # Keep others as dict and set them into metadata properties
        self.properties = {"tilename": prod.tile_name}
        self.properties.update(kwargs)
        """
        REQUIRED. A dictionary of additional metadata for the Item.
        """

    @cache
    def geometry_fct(self) -> gpd.GeoDataFrame:
        if self._prod.is_ortho:
            return self._prod.footprint().to_crs(WGS84)
        else:
            return self.bbox_fct()

    @cache
    def bbox_fct(self) -> gpd.GeoDataFrame:
        return self._prod.extent().to_crs(WGS84)

    @cache
    def create_item(self):
        try:
            import pystac
        except ImportError:
            raise ImportError(
                "You need to install 'pystac[validation]' to export your product to a STAC Item!"
            )

        # Item creation
        item = pystac.Item(
            id=self.id,
            datetime=self.datetime,
            geometry=self.geometry,
            bbox=self.bbox,
            properties=self.properties.copy(),
            stac_extensions=self.extensions,
        )

        # Add assets
        # TODO: manage S3 paths
        # TODO: relative path ?
        thumbnail_path = self._prod.get_quicklook_path()
        if thumbnail_path:
            item.add_asset(
                "thumbnail",
                pystac.Asset(
                    href=str(thumbnail_path), media_type=get_media_type(thumbnail_path)
                ),  # TODO
            )

        # Add EO extension
        self.eo.add_to_item(item)

        # Add the PROJ extension
        self.proj.add_to_item(item)

        # Add the View extension
        self.view.add_to_item(item)

        stac_utils.fill_common_mtd(
            item, self._prod, **{TITLE: self.title, GSD: self.gsd}
        )

        # Now that we've added all the metadata to the item,
        # let's check the validator to make sure we've specified everything correctly.
        # The validation logic will take into account the new extensions
        # that have been enabled and validate against the proper schemas for those extensions
        item.validate()

        return item

    def _to_repr(self) -> list:
        """
        Get repr list.
        Returns:
            list: repr list
        """
        repr_list = [
            "STAC Item attributes:",
            f"\t{ID}: {self.id}",
            f"\t{CONSTELLATION}: {self.constellation}",
            f"\t{GSD}: {self.gsd}",
            f"\t{DATETIME}: {self.datetime}",
            f"\t{GEOMETRY}:{repr_multiline_str(self.geometry, nof_tabs=2)}",
            f"\t{BBOX}: {repr_multiline_str(self.bbox, nof_tabs=2)}",
            f"\t{STAC_EXTENSIONS}: {repr_multiline_str(self.extensions, nof_tabs=2)}",
        ]

        for key, val in self.properties.items():
            if val is not None:
                repr_list.append(f"\tproperties - {key}: {val}")

        return repr_list

    def __repr__(self):
        repr_list = "\n".join(self._to_repr())
        repr_list += "\n\n\t"
        repr_list += "\n\t".join(self.eo._to_repr())
        repr_list += "\n\t"
        repr_list += "\n\t".join(self.proj._to_repr())
        repr_list += "\n\t"
        repr_list += "\n\t".join(self.view._to_repr())

        return repr_list
