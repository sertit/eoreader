# Copyright 2025, SERTIT-ICube - France, https://sertit.unistra.fr/
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
"""Class for STAC products"""

import asyncio
import contextlib
import logging
from io import BytesIO

import geopandas as gpd
import shapely
from lxml import etree
from rasterio import crs
from sertit import geometry, path, rasters, vectors
from sertit.types import AnyPathStrType

from eoreader import EOREADER_NAME, cache
from eoreader.exceptions import InvalidProductError
from eoreader.products.product import Product
from eoreader.stac import PROJ_EPSG
from eoreader.utils import simplify

try:
    from pystac import Item
except ModuleNotFoundError:
    from typing import Any as Item

LOGGER = logging.getLogger(EOREADER_NAME)


class StacProduct(Product):
    """Stac products"""

    with contextlib.suppress(AttributeError):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    item = None
    clients = None
    default_clients = None

    def _set_item(self, product_path: AnyPathStrType, **kwargs) -> Item:
        """
        Set the STAC Item as member

        Args:
            product_path (AnyPathStrType): Product path
            **kwargs: Other argumlents
        """
        item = kwargs.pop("item", None)
        if item is None:
            try:
                import pystac

                item = pystac.Item.from_file(product_path)
            except ModuleNotFoundError as exc:
                raise InvalidProductError(
                    "You should install 'pystac' to use STAC Products."
                ) from exc

            except TypeError as exc:
                raise InvalidProductError(
                    "You should either fill 'product_path' or 'item'."
                ) from exc

        return item

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
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "You need to install 'matplotlib' to plot the product."
            ) from exc
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
                    except ModuleNotFoundError as exc:
                        raise ModuleNotFoundError(
                            "You need to install 'pillow' to plot the product."
                        ) from exc

                    qlk = self.read_href(quicklook_path, clients=self.clients)
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

    def _is_mpc(self):
        """Is this product from Microsoft Planetary Computer?"""
        try:
            prod_path = str(self.path)
        except AttributeError:
            prod_path = self.item.self_href

        return "planetarycomputer" in prod_path

    def sign_url(self, url: str) -> str:
        """
        Sign URL with planetary computer if installed.
        Args:
            url (str): URL to sign

        Returns:
            str: Signed URL
        """
        if self._is_mpc():
            try:
                import planetary_computer

                return planetary_computer.sign_url(url)
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    "You need to install 'planetary-computer' to use MPC STAC products in EOReader."
                ) from exc
        else:
            return url

    def read_href(self, href: str, config=None, clients=None) -> bytes:
        """
        Read HREF (with stac-asset.blocking)

        Args:
            href: The href to read
            config: The download configuration to use
            clients: Any pre-configured clients to use

        Returns:
            bytes: The bytes from the href
        """
        try:
            from stac_asset import blocking
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "You need to install 'stac-asset' (see https://stac-asset.readthedocs.io/en/latest/) to use STAC products in EOReader."
            ) from exc
        return blocking.read_href(href, config, clients)

    def get_s3_client(self, region_name: str, requester_pays: bool = False, **kwargs):
        """
        Get a Client (for stac-asset)
        Args:
            region_name (str): Region name
            requester_pays (bool): Requester pays
            **kwargs: Other args

        Returns:

        """
        try:
            from stac_asset import S3Client
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "You need to install 'stac-asset' (see https://stac-asset.readthedocs.io/en/latest/) to use STAC products in EOReader."
            ) from exc
        return S3Client(
            region_name=region_name, requester_pays=requester_pays, **kwargs
        )

    def get_sinergise_client(self):
        """
        Get Sinergise S3 client (for stac-asset)
        """
        return self.get_s3_client(requester_pays=True, region_name="eu-central-1")

    def get_e84_client(self):
        """
        Get Element-84 client (for stac-asset)
        """
        return self.get_s3_client(region_name="us-west-2")

    def get_usgs_client(self):
        """
        Get USGS Landsat client (for stac-asset)
        """
        return self.get_s3_client(requester_pays=True, region_name="us-west-2")

    def _read_mtd_xml_stac(self, mtd_url, **kwargs) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dicts as a dict

        Args:
            mtd_from_path (str): Metadata regex (glob style) to find from extracted product
            mtd_archived (str): Metadata regex (re style) to find from archived product

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces

        """
        mtd_str = self.read_href(mtd_url, clients=self.clients)
        root = etree.fromstring(mtd_str)

        # Get namespaces map (only useful ones)
        nsmap = {key: f"{{{ns}}}" for key, ns in root.nsmap.items()}
        pop_list = ["xsi", "xs", "xlink"]
        for ns in pop_list:
            if ns in nsmap:
                nsmap.pop(ns)

        return root, nsmap


# TODO: expose other functions
