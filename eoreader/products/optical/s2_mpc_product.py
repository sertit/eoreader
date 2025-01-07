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
"""Sentinel-2 MPC products"""

import difflib
import logging

import numpy as np
import xarray as xr
from lxml import etree
from sertit import AnyPath
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache
from eoreader.bands import BandNames
from eoreader.products import S2E84Product
from eoreader.products.optical.optical_product import RawUnits
from eoreader.products.stac_product import StacProduct
from eoreader.reader import Constellation

LOGGER = logging.getLogger(EOREADER_NAME)


class S2MpcStacProduct(StacProduct, S2E84Product):
    def __init__(
        self,
        product_path: AnyPathStrType = None,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.kwargs = kwargs
        """Custom kwargs"""

        self._processing_baseline = None

        # Copy the kwargs
        super_kwargs = kwargs.copy()

        # Get STAC Item
        self.item = self._set_item(product_path, **super_kwargs)
        """ STAC Item of the product """

        self.default_clients = []
        self.clients = super_kwargs.pop("client", self.default_clients)

        if product_path is None:
            # Canonical link is always the second one
            # TODO: check if ok
            product_path = AnyPath(self.item.links[1].target).parent

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.REFL
        self._has_cloud_cover = True
        self._use_filename = False
        self.needs_extraction = False

        self.stac_mtd = self.item.to_dict()

        # Pre init done by the super class
        super(S2E84Product, self)._pre_init(**kwargs)

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation: force S2."""
        return Constellation.S2

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Get processing baseline: N0213 -> 02.13
        pr_baseline = float(self.split_name[3][1:]) / 100
        self._processing_baseline = pr_baseline

        # Pre init done by the super class
        super(S2E84Product, self)._post_init(**kwargs)

    def _get_name(self) -> str:
        """
        Set product real name.

        Returns:
            str: True name of the product (from metadata)
        """
        return self.item.properties["s2:product_uri"]

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # TODO: use mtd for offset and quantif value
        offset = 0.0 if self._processing_baseline < 4.0 else -1000.0
        quantif_value = 10000.0

        # Compute the correct radiometry of the band
        band_arr = (band_arr + offset) / quantif_value

        return band_arr.astype(np.float32)

    def _get_path(self, file_id: str, ext="tif") -> str:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            AnyPathType: band path
        """
        if file_id.lower() in self.item.assets:
            asset_name = file_id.lower()
        elif file_id in [band.id for band in self.bands.values() if band is not None]:
            asset_name = [
                band.name
                for band in self.bands.values()
                if band is not None and f"{band.id}" == file_id
            ][0]
        else:
            try:
                asset_name = difflib.get_close_matches(
                    file_id, self.item.assets.keys(), cutoff=0.5, n=1
                )[0]
            except Exception as exc:
                raise FileNotFoundError(
                    f"Impossible to find an asset in {list(self.item.assets.keys())} close enough to '{file_id}'"
                ) from exc

        return self.sign_url(self.item.assets[asset_name].href)

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read mtd.

        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of an XML root + namespace

        Returns:
            Tuple[Union[pd.DataFrame, etree._Element], dict]:
                Metadata as a Pandas.DataFrame or as (etree._Element, dict): Metadata XML root and its namespaces
        """
        return self._read_mtd_xml_stac(self._get_path("granule-metadata"))

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        return self._get_path("rendered_preview")
