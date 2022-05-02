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
import geopandas as gpd
from sertit import misc
from sertit.vectors import WGS84

from eoreader import cache
from eoreader.stac._stac_keywords import BBOX_FCT, DATETIME, GEOMETRY_FCT, ID
from eoreader.stac.stac_extensions import EoExtension, ProjExtension, ViewExtension


class StacItem:
    """
    Class of STAC object, mapping EOReader products to STAC Items.
    Implements STAC Spec basic and extensions
    TODO
    """

    def __init__(self, **kwargs):
        misc.check_mandatory_keys(kwargs, [ID, GEOMETRY_FCT, BBOX_FCT, DATETIME])
        self.id = kwargs.pop(ID)
        """
        REQUIRED.
        Provider identifier.
        The ID should be unique within the Collection that contains the Item.
        """

        self._geometry_fct = kwargs[GEOMETRY_FCT]
        """
        REQUIRED.
        Defines the full footprint of the asset represented by this item, formatted according to RFC 7946, section 3.1.
        The footprint should be the default GeoJSON geometry, though additional geometries can be included.
        Coordinates are specified in Longitude/Latitude or Longitude/Latitude/Elevation based on WGS 84.
        """

        self._bbox_fct = kwargs[BBOX_FCT]
        """
        REQUIRED if geometry is not null. Bounding Box of the asset represented by this Item, formatted according to RFC 7946, section 5.
        """

        self.datetime = kwargs.pop(DATETIME)
        """
        REQUIRED.
        The searchable date and time of the assets, which must be in UTC.
        It is formatted according to RFC 3339, section 5.6.
        null is allowed, but requires start_datetime and end_datetime from common metadata to be set.
        """

        self.eo = EoExtension(**kwargs)
        self.proj = ProjExtension(**kwargs)
        self.view = ViewExtension(**kwargs)

        # Pop some args that we do not want in our additional properties
        for arg in [GEOMETRY_FCT, BBOX_FCT]:
            kwargs.pop(arg)

        # Keep others as dict and set them into metadata properties
        self.properties = kwargs
        """
        REQUIRED. A dictionary of additional metadata for the Item.
        """

    @cache
    def geometry(self) -> gpd.GeoDataFrame:
        return self._geometry_fct().to_crs(WGS84)

    @cache
    def bbox(self) -> gpd.GeoDataFrame:
        return self._bbox_fct().to_crs(WGS84)

    def create_item(self):
        try:
            import pystac
            from pystac.extensions.eo import EOExtension  # , Band
            from pystac.extensions.projection import ProjectionExtension
            from pystac.extensions.view import ViewExtension
        except ImportError:
            raise ImportError(
                "You need to install 'pystac' to export your product to a STAC Item!"
            )

        # Item creation
        item = pystac.Item(
            id=self.id,
            datetime=self.datetime,
            geometry=self.geometry(),
            bbox=self.bbox(),
            properties=self.properties,
        )

        # Add assets
        # try:
        #     try:
        #         get_thumbnail = str(next(path.glob("**/*.jpg")))
        #     except StopIteration:
        #         get_thumbnail = str(next(path.glob("**/*.JPG")))
        #     thumbnail_url = to_s3_https_path(get_thumbnail)
        #
        #     item.add_asset("thumbnail",
        #                    pystac.Asset(
        #                        href=thumbnail_url,
        #                        media_type=pystac.MediaType.JPEG
        #                    ))
        # except StopIteration:
        #     pass
        #
        # # Add band asset
        # for band_id, band_path in bands():
        #     try:
        #         with rasterio.open(band_path) as ds:
        #             if ds.crs.is_projected:
        #                 gsd = ds.res[0]
        #     except:
        #         gsd = prod.resolution
        #
        #     band_url = to_s3_https_path(band_path)
        #     asset = pystac.Asset(href=band_url, media_type=pystac.MediaType.COG)
        #     asset_eo_ext = EOExtension.ext(asset)
        #     asset_eo_ext.bands = [
        #         Band.create(
        #             name=band_id.name,
        #             common_name=COMMON_NAMES[band_id],
        #             # center_wavelength=0.48, full_width_half_max=0.02
        #         )
        #     ]
        #     asset.common_metadata.gsd = gsd
        #
        #     item.add_asset(band_id.name, asset)

        # Add the EO extension
        eo_ext = EOExtension.ext(item, add_if_missing=True)
        eo_ext.cloud_cover = self.eo.cloud_cover

        # Add the PROJ extension
        proj_ext = ProjectionExtension.ext(item, add_if_missing=True)
        proj_ext.epsg = self.proj.crs().to_epsg()
        proj_ext.wkt2 = self.proj.crs().to_wkt()
        # TODO: proj_ext.projjson

        # The View Geometry extension specifies information related to angles of sensors and other radiance angles
        # that affect the view of resulting data
        view_ext = ViewExtension.ext(item, add_if_missing=True)
        view_ext.sun_azimuth = self.view.sun_az
        view_ext.sun_elevation = self.view.sun_el

        # Now that we've added all the metadata to the item,
        # let's check the validator to make sure we've specified everything correctly.
        # The validation logic will take into account the new extensions
        # that have been enabled and validate against the proper schemas for those extensions
        item.validate()
