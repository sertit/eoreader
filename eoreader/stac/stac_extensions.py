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
STAC extensions:

- `STAC Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_
    - Cloud coverage (if existing)
- `STAC Projection Extension Specification <https://github.com/stac-extensions/projection/>`_
    - Projected (UTM) epsg, bbox, footprint, centroid...
- `STAC View Extension Specification <https://github.com/stac-extensions/view/>`_
    - Sun angles
    - Viewing position (in progress)
"""
import os

import geopandas as gpd
from rasterio.crs import CRS

from eoreader import cache
from eoreader.stac import StacCommonNames
from eoreader.stac._stac_keywords import (
    DESCRIPTION,
    EO_BANDS,
    EO_CC,
    GSD,
    PROJ_BBOX,
    PROJ_CENTROID,
    PROJ_EPSG,
    PROJ_GEOMETRY,
    PROJ_SHAPE,
    PROJ_TRANSFORM,
    TITLE,
    VIEW_SUN_AZIMUTH,
    VIEW_SUN_ELEVATION,
)
from eoreader.stac.stac_utils import (
    fill_common_mtd,
    gdf_to_bbox,
    gdf_to_centroid,
    gdf_to_geometry,
    repr_multiline_str,
)


class EoExt:
    """
    Class of `Electro-Optical Extension Specification <https://github.com/stac-extensions/eo/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        self.cloud_cover = None
        self._prod = prod

        try:
            if prod._has_cloud_cover:
                self.cloud_cover = prod.get_cloud_cover()
        except AttributeError:
            pass

        self.bands = prod.bands

    def _to_repr(self) -> list:
        """
        Get repr list.
        Returns:
            list: repr list
        """
        band_repr = "\n".join(
            [
                f"\t\t\t{band.value}:"
                f"\n\t\t\t\t{val.id}"
                f"\n\t\t\t\t{val.common_name.value}"
                for band, val in self.bands.items()
                if val is not None
            ]
        )
        repr_list = ["Electro-Optical STAC Extension attributes:"]

        if self.cloud_cover is not None:
            repr_list.append(f"\t{EO_CC}: {self.cloud_cover}")

        repr_list.append(f"\t{EO_BANDS}:\n{band_repr}")

        return repr_list

    def __repr__(self):
        return "\n".join(self._to_repr())

    def add_to_item(self, item) -> None:
        """
        Add extension to selected item.

        Args:
            item (pystac.Item): Selected item
        """
        try:
            import pystac
            from pystac.extensions.eo import Band, EOExtension
        except ImportError:
            raise ImportError(
                "You need to install 'pystac[validation]' to export your product to a STAC Item!"
            )
        # Add the EO extension
        eo_ext = EOExtension.ext(item, add_if_missing=True)
        if self.cloud_cover is not None:
            eo_ext.cloud_cover = self.cloud_cover

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
                    self._prod,
                    **{TITLE: band.name, GSD: band.gsd, DESCRIPTION: band.description},
                )

                item.add_asset(band.name, band_asset)
            except ValueError:
                continue


class ProjExt:
    """
    Class `Projection Extension Specification <https://github.com/stac-extensions/projection/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        self._prod = prod
        self.epsg = self.crs().to_epsg()
        self.wkt2 = self.crs().to_wkt()
        self.geometry = gdf_to_geometry(self.geometry_fct())
        self.bbox = gdf_to_bbox(self.bbox_fct())
        self.centroid = gdf_to_centroid(self.geometry_fct())

        if self._prod.is_ortho:
            transform, width, height, _ = self._prod.default_transform()
            self.shape = [height, width]
            self.transform = transform
        else:
            self.shape = None
            self.transform = None

    @cache
    def crs(self) -> CRS:
        """
        Getter of the projected CRS

        Returns:
            CRS: Projected CRS
        """
        return self._prod.crs()

    @cache
    def geometry_fct(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected geometry (footprint)

        Returns:
            gpd.GeoDataFrame: Projected geometry
        """
        if self._prod.is_ortho:
            return self._prod.footprint().to_crs(self.crs())
        else:
            return self.bbox_fct()

    @cache
    def bbox_fct(self) -> gpd.GeoDataFrame:
        """
        Getter of the projected bbox (extent)

        Returns:
            gpd.GeoDataFrame: Projected bbox
        """
        return self._prod.extent().to_crs(self.crs())

    def _to_repr(self) -> list:
        """
        Get repr list.
        Returns:
            list: repr list
        """
        repr_list = [
            "Projection STAC Extension attributes:",
            f"\t{PROJ_EPSG}: {self.epsg}",
            # f"\t{PROJ_WKT}: {self.wkt2}",  # Too long to display
            f"\t{PROJ_GEOMETRY}: {repr_multiline_str(self.geometry, nof_tabs=3)}",
            f"\t{PROJ_BBOX}: {repr_multiline_str(self.bbox, nof_tabs=3)}",
            f"\t{PROJ_CENTROID}: {repr_multiline_str(self.centroid, nof_tabs=3)}",
        ]

        if self.shape is not None:
            repr_list.append(f"\t{PROJ_SHAPE}: {self.shape}")

        if self.transform is not None:
            repr_list.append(
                f"\t{PROJ_TRANSFORM}: {repr_multiline_str(self.transform, nof_tabs=3)}"
            )

        return repr_list

    def __repr__(self):
        return "\n".join(self._to_repr())

    def add_to_item(self, item) -> None:
        """
        Add extension to selected item.

        Args:
            item (pystac.Item): Selected item
        """
        try:
            from pystac.extensions.projection import ProjectionExtension
        except ImportError:
            raise ImportError(
                "You need to install 'pystac[validation]' to export your product to a STAC Item!"
            )
        # Add the proj extension
        proj_ext = ProjectionExtension.ext(item, add_if_missing=True)
        proj_ext.epsg = self.epsg
        proj_ext.wkt2 = self.wkt2
        # proj_ext.projjson = None

        proj_ext.geometry = self.geometry
        proj_ext.bbox = self.bbox
        proj_ext.centroid = self.centroid

        if self._prod.is_ortho:
            proj_ext.shape = self.shape
            proj_ext.transform = self.transform


class ViewExt:
    """
    Class `View Extension Specification <https://github.com/stac-extensions/view/>`_ of STAC items.
    """

    def __init__(self, prod, **kwargs):
        try:
            sun_az, sun_el = prod.get_mean_sun_angles()
            self.sun_az = sun_az
            self.sun_el = sun_el
        except AttributeError:
            self.sun_az = None
            self.sun_el = None

        # TODO: Others will come
        # VIEW_OFF_NADIR = "view:off_nadir"
        # VIEW_INCIDENCE_ANGLE = "view:incidence_angle"
        # VIEW_AZIMUTH = "view:azimuth"

    def _to_repr(self) -> list:
        """
        Get repr list.
        Returns:
            list: repr list
        """
        if self.sun_az is not None and self.sun_el is not None:
            repr_list = [
                "View STAC Extension attributes:",
                f"\t{VIEW_SUN_AZIMUTH}: {self.sun_az}",
                f"\t{VIEW_SUN_ELEVATION}: {self.sun_el}",
            ]
        else:
            repr_list = []

        return repr_list

    def __repr__(self):
        return "\n".join(self._to_repr())

    def add_to_item(self, item) -> None:
        """
        Add extension to selected item.

        Args:
            item (pystac.Item): Selected item
        """
        try:
            from pystac.extensions.view import ViewExtension
        except ImportError:
            raise ImportError(
                "You need to install 'pystac[validation]' to export your product to a STAC Item!"
            )
        # Add the view extension
        # The View Geometry extension specifies information related to angles of sensors and other radiance angles that affect the view of resulting data
        if self.sun_az is not None and self.sun_el is not None:
            view_ext = ViewExtension.ext(item, add_if_missing=True)
            view_ext.sun_azimuth = self.sun_az
            view_ext.sun_elevation = self.sun_el
