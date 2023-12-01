# -*- coding: utf-8 -*-
# Copyright 2023, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" Class for STAC products """
import logging
from io import BytesIO

import geopandas as gpd
import planetary_computer
import shapely
from lxml import etree
from rasterio import crs
from sertit import geometry, path, rasters, vectors
from stac_asset import blocking

from eoreader import EOREADER_NAME, cache
from eoreader.products.product import Product
from eoreader.stac import PROJ_EPSG
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


class StacProduct(Product):
    """Stac products"""

    item = None
    clients = None
    default_clients = None

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of stack.

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get extent
        return gpd.GeoDataFrame(
            geometry=geometry.from_bounds_to_polygon(*self.item.bbox),
            crs=vectors.EPSG_4326,
        ).to_crs(self.crs())

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # Get extent
        return gpd.GeoDataFrame.from_dict(
            data=shapely.polygons(self.item.geometry["coordinates"]),
            crs=vectors.EPSG_4326,
        ).to_crs(self.crs())

    @cache
    def crs(self) -> crs.CRS:
        """
        Get UTM projection of stack.

        Returns:
            crs.CRS: CRS object
        """
        epsg = self.item.properties.get(PROJ_EPSG)

        if epsg is None:
            def_crs = gpd.GeoDataFrame(
                geometry=geometry.from_bounds_to_polygon(*self.item.bbox),
                crs=vectors.EPSG_4326,
            ).estimate_utm_crs()
        else:
            def_crs = crs.CRS.from_epsg(code=epsg)

        return def_crs

    def plot(self) -> None:
        """
        Plot the quicklook if existing
        """
        try:
            import matplotlib.pyplot as plt
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "You need to install 'matplotlib' to plot the product."
            )
        else:
            quicklook_path = self.get_quicklook_path()

            if quicklook_path is not None:
                plt.figure(figsize=(6, 6))
                if path.get_ext(quicklook_path).split("?")[0].lower() in [
                    "png",
                    "jpg",
                    "jpeg",
                ]:
                    try:
                        from PIL import Image
                    except ModuleNotFoundError:
                        raise ModuleNotFoundError(
                            "You need to install 'pillow' to plot the product."
                        )

                    qlk = blocking.read_href(quicklook_path, clients=self.clients)
                    plt.imshow(Image.open(BytesIO(qlk)))
                else:
                    # Check it
                    qck = rasters.read(quicklook_path)
                    if qck.rio.count == 3:
                        qck.plot.imshow(robust=True)
                    elif qck.rio.count == 1:
                        qck.plot(cmap="GnBu_r", robust=True)
                    else:
                        pass

                plt.title(f"{self.condensed_name}")

    def sign_url(self, url: str):
        # TODO complete if needed
        return planetary_computer.sign_url(url)

    def _read_mtd_xml_stac(self, mtd_url, **kwargs) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dicts as a dict

        Args:
            mtd_from_path (str): Metadata regex (glob style) to find from extracted product
            mtd_archived (str): Metadata regex (re style) to find from archived product

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces

        """
        mtd_str = blocking.read_href(mtd_url, clients=self.clients)
        root = etree.fromstring(mtd_str)

        # Get namespaces map (only useful ones)
        nsmap = {key: f"{{{ns}}}" for key, ns in root.nsmap.items()}
        pop_list = ["xsi", "xs", "xlink"]
        for ns in pop_list:
            if ns in nsmap.keys():
                nsmap.pop(ns)

        return root, nsmap


# TODO: expose other functions
