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
import os
from datetime import datetime
from typing import Union

import geopandas as gpd
from sertit.vectors import WGS84
from shapely.geometry import mapping

from eoreader import cache
from eoreader.stac import DESCRIPTION, GSD
from eoreader.stac._stac_keywords import TITLE, StacCommonNames
from eoreader.stac.stac_extensions import EoExtension, ProjExtension, ViewExtension

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
        self.eo = EoExtension(prod, **kwargs)
        """
        STAC Electro-Optical Extension Specification
        """
        self.proj = ProjExtension(prod, **kwargs)
        """
        STAC Projection Extension Specification
        """
        self.view = ViewExtension(prod, **kwargs)
        """
        STAC View Extension Specification
        """

        # Keep others as dict and set them into metadata properties
        self.properties = {"tilename": prod.tile_name}
        self.properties.update(kwargs)
        """
        REQUIRED. A dictionary of additional metadata for the Item.
        """

        self._prod = prod

    @cache
    def geometry(self) -> gpd.GeoDataFrame:
        if self._prod.is_ortho:
            return self._prod.footprint().to_crs(WGS84)
        else:
            return self.bbox()

    @cache
    def bbox(self) -> gpd.GeoDataFrame:
        return self._prod.extent().to_crs(WGS84)

    @cache
    def create_item(self):
        try:
            import pystac
            from pystac.extensions.eo import Band, EOExtension
            from pystac.extensions.projection import ProjectionExtension
            from pystac.extensions.view import ViewExtension
        except ImportError:
            raise ImportError(
                "You need to install 'pystac[validation]' to export your product to a STAC Item!"
            )

        def fill_common_mtd(asset: Union[pystac.Asset, pystac.Item], **kwargs):

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
            asset.common_metadata.constellation = self._prod.constellation.value.lower()
            asset.common_metadata.mission = None
            asset.common_metadata.gsd = kwargs.get(GSD)

        # Item creation
        item = pystac.Item(
            id=self._prod.condensed_name,
            datetime=self._prod.datetime,
            geometry=mapping(self.geometry().geometry.values[0]),
            bbox=list(self.bbox().bounds.values[0]),
            properties=self.properties,
            stac_extensions=SAR_STAC_EXTENSIONS
            if self._prod.sensor_type.value == "SAR"
            else OPTICAL_STAC_EXTENSIONS,
        )

        # Add assets
        # TODO: manage S3 paths
        # TODO: relative path ?
        thumbnail_path = self._prod.get_quicklook_path()
        if thumbnail_path:
            suffix = os.path.splitext(thumbnail_path)[-1]
            if suffix.lower() == ".png":
                media_type = pystac.MediaType.PNG
            elif suffix.lower() == ".tif":
                media_type = pystac.MediaType.GEOTIFF
            elif suffix.lower() in [".jpeg", ".jpg"]:
                media_type = pystac.MediaType.JPEG
            else:
                raise ValueError(f"Not recognized media type: {suffix}")
            item.add_asset(
                "thumbnail",
                pystac.Asset(href=str(thumbnail_path), media_type=media_type),  # TODO
            )

        # Add the EO extension
        eo_ext = EOExtension.ext(item, add_if_missing=True)
        if self.eo.cloud_cover is not None:
            eo_ext.cloud_cover = self.eo.cloud_cover

        # Add band asset
        band_paths = self._prod.get_raw_band_paths()
        for band_name, band_path in band_paths.items():
            band = self._prod.bands[band_name]
            try:
                suffix = os.path.splitext(band_path)[-1]
                if suffix.lower() in [".tiff", ".tif"]:
                    # Manage COGs
                    media_type = pystac.MediaType.GEOTIFF
                elif suffix.lower() == ".jp2":
                    media_type = pystac.MediaType.JPEG2000
                elif suffix.lower() == ".xml":
                    media_type = pystac.MediaType.XML
                elif suffix.lower() == ".til":
                    media_type = None  # Not existing
                elif suffix.lower() == ".nc":
                    media_type = None  # Not existing
                else:
                    media_type = None  # Not recognized
                band_asset = pystac.Asset(
                    href=str(band_path),
                    media_type=media_type,
                    roles=[band.asset_role],
                    extra_fields={"eoreader_name": band.eoreader_name.value},
                )

                # Spectral bands
                try:
                    center_wavelength = band.center_wavelength
                    solar_illumination = band.solar_illumination
                    full_width_half_max = band.full_width_half_max
                except AttributeError:
                    center_wavelength = None
                    solar_illumination = None
                    full_width_half_max = None

                asset_eo_ext = EOExtension.ext(band_asset)
                common_name = (
                    band.common_name.value
                    if isinstance(band.common_name, StacCommonNames)
                    else None
                )
                asset_eo_ext.bands = [
                    Band.create(
                        name=band.name,
                        common_name=common_name,
                        description=band.description,
                        center_wavelength=center_wavelength,
                        full_width_half_max=full_width_half_max,
                        solar_illumination=solar_illumination,
                    )
                ]
                fill_common_mtd(
                    band_asset,
                    **{TITLE: band.name, GSD: band.gsd, DESCRIPTION: band.description},
                )

                item.add_asset(band.name, band_asset)
            except ValueError:
                continue

        # Add the PROJ extension
        proj_ext = ProjectionExtension.ext(item, add_if_missing=True)
        proj_ext.epsg = self.proj.crs().to_epsg()
        proj_ext.wkt2 = self.proj.crs().to_wkt()
        # proj_ext.projjson = None

        proj_geom = self.proj.geometry()
        proj_ext.geometry = mapping(proj_geom.geometry.values[0])
        proj_ext.bbox = list(self.proj.bbox().bounds.values[0])
        centroid = proj_geom.centroid.to_crs(WGS84).values[0]
        proj_ext.centroid = {"lat": centroid.y, "lon": centroid.x}

        if self._prod.is_ortho:
            transform, width, height, _ = self._prod.default_transform()
            proj_ext.shape = [height, width]
            proj_ext.transform = transform

        # The View Geometry extension specifies information related to angles of sensors and other radiance angles that affect the view of resulting data
        if self.view.sun_az is not None and self.view.sun_el is not None:
            view_ext = ViewExtension.ext(item, add_if_missing=True)
            view_ext.sun_azimuth = self.view.sun_az
            view_ext.sun_elevation = self.view.sun_el

        fill_common_mtd(
            item, **{TITLE: self._prod.condensed_name, GSD: self._prod.resolution}
        )

        # Now that we've added all the metadata to the item,
        # let's check the validator to make sure we've specified everything correctly.
        # The validation logic will take into account the new extensions
        # that have been enabled and validate against the proper schemas for those extensions
        item.validate()

        return item
