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
"""
Vision-1 products.
See `here <https://www.intelligence-airbusds.com/imagery/constellation/vision1/>`_
for more information.
"""

import io
import logging
from enum import unique

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio import crs as riocrs
from sertit import geometry, rasters
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    BLUE,
    GREEN,
    NARROW_NIR,
    NIR,
    PAN,
    RED,
    BandNames,
    SpectralBand,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.dimap_v1_product import DimapV1Product
from eoreader.products.optical.optical_product import RawUnits
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)

_VIS1_E0 = {
    PAN: 1828,
    BLUE: 2003,
    GREEN: 1828,
    RED: 1618,
    NIR: 1042,
    NARROW_NIR: 1042,
}
"""
Solar spectral irradiance, E0b, (commonly known as ESUN) is a constant value specific to each band of the Vision-1 imager.
It is determined by using well know models of Solar Irradiance with the measured spectral transmission of the imager for each incident wavelength.
It has units of Wm-2μm-1. The applicable values for Vision-1 are provided in the table.
"""


@unique
class Vis1BandCombination(ListEnum):
    """
    band combination of Vision-1 data
    See :code:`vision-1-imagery-user-guide-20210217.pdf` file for more information.
    """

    BUN = "Bundle"
    """
    BUN products provide both the 4-band multispectral, and the panchromatic data
    from the same acquisition in a single product package. Data is provided as 16-bit
    GeoTiffs with pixel sizes of 3.5m and 0.87m for MS and PAN data respectively.
    """

    PSH = "Pansharpened"
    """
    Pansharpened products combine the spectral information of the four multispectral
    bands with the high-resolution detail provided within the panchromatic data,
    resulting in a single 0.87m colour product.
    """

    MS4 = "Multispectral"
    """
    The single multispectral product includes four multispectral (colour) bands: Blue,
    Green, Red and Near Infrared. The product pixel size is 3.5m.
    """

    PAN = "Panchromatic"
    """
    The Vision-1 panchromatic product includes data contained within a single high-
    resolution black and white band. It covers wavelengths between 450 and 650nm
    within the visible spectrum. The product pixel size is 0.87m.
    """


@unique
class Vis1ProductType(ListEnum):
    """
    This is the processing level of the given product, either projected or orthorectified.
    See :code:`vision-1-imagery-user-guide-20210217.pdf` file for more information.
    """

    PRJ = "PROJECTED"
    """
    Projected (not ortho)
    """

    ORTP = "ORTHORECTIFIED"
    """
    Orthorectified
    """


class Vis1Product(DimapV1Product):
    """
    Class of Vision-1 products.
    See `here <https://www.intelligence-airbusds.com/imagery/constellation/vision1/>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._pan_res = 0.9
        self._ms_res = 3.5
        self.needs_extraction = False
        self._proj_prod_type = [Vis1ProductType.PRJ]
        self._raw_units = RawUnits.RAD

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.band_combi = getattr(Vis1BandCombination, self.split_name[1])

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Not Pansharpened images
        if self.band_combi == Vis1BandCombination.MS4:
            self.pixel_size = self._ms_res
        # Pansharpened images
        else:
            self.pixel_size = self._pan_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        Vision-1: https://earth.esa.int/eogateway/missions/vision-1
        """
        self.instrument = "Vision-1 optical sensor"

    def _set_product_type(self) -> None:
        """
        Set products type

        See Vision-1_web_201906.pdf for more information.
        """
        # Get MTD XML file
        prod_type = self.split_name[3]
        self.product_type = getattr(Vis1ProductType, prod_type)

        # Manage not orthorectified product
        if self.product_type == Vis1ProductType.PRJ:
            self.is_ortho = False

    def _map_bands(self) -> None:
        """
        Map bands
        """
        # Create spectral bands
        pan = SpectralBand(
            eoreader_name=PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 450, WV_MAX: 650},
        )

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self._ms_res, WV_MIN: 440, WV_MAX: 510},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self._ms_res, WV_MIN: 510, WV_MAX: 590},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 600, WV_MAX: 670},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 4, GSD: self._ms_res, WV_MIN: 760, WV_MAX: 910},
        )

        # Manage bands of the product
        if self.band_combi == Vis1BandCombination.PAN:
            self.bands.map_bands({PAN: pan})
        elif self.band_combi in [
            Vis1BandCombination.MS4,
            Vis1BandCombination.BUN,
        ]:
            self.bands.map_bands(
                {
                    BLUE: blue,
                    GREEN: green,
                    RED: red,
                    NIR: nir,
                    NARROW_NIR: nir,
                }
            )
            if self.band_combi == Vis1BandCombination.BUN:
                LOGGER.warning(
                    "Bundle mode has never been tested by EOReader, use it at your own risk!"
                )
        elif self.band_combi == Vis1BandCombination.PSH:
            self.bands.map_bands(
                {
                    BLUE: blue.update(gsd=self._pan_res),
                    GREEN: green.update(gsd=self._pan_res),
                    RED: red.update(gsd=self._pan_res),
                    NIR: nir.update(gsd=self._pan_res),
                    NARROW_NIR: nir.update(gsd=self._pan_res),
                }
            )
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        crs_name = root.findtext(".//HORIZONTAL_CS_CODE")
        if not crs_name:
            crs_name = root.findtext(".//GEOGRAPHIC_CS_CODE")
            if not crs_name:
                raise InvalidProductError(
                    "Cannot find the CRS name (from GEOGRAPHIC_CS_CODE or HORIZONTAL_CS_CODE) type in the metadata file"
                )

        return riocrs.CRS.from_string(crs_name)

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((707025.261 9688613.833, 707043.276 9...
            [1 rows x 3 columns]

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """

        # Get footprint of the preview
        ql_path = self.get_quicklook_path()
        if ql_path is not None:
            arr = rasters.read(ql_path, indexes=[1])

            # Vectorize the nodata band
            footprint = rasters.vectorize(
                arr, values=0, keep_values=False, dissolve=True
            )
            footprint = geometry.get_wider_exterior(footprint)
        else:
            # If ortho -> nodata is not set !
            if self.is_ortho:
                # Get footprint of the first band of the stack
                footprint_dezoom = 10
                arr = rasters.read(
                    self.get_default_band_path(),
                    resolution=self.pixel_size * footprint_dezoom,
                    indexes=[1],
                )

                # Vectorize the nodata band
                footprint = rasters.vectorize(
                    arr, values=0, keep_values=False, dissolve=True
                )
                footprint = geometry.get_wider_exterior(footprint)
            else:
                # If not ortho -> default band has been orthorectified and nodata will be set
                footprint = rasters.get_footprint(self.get_default_band_path())

        return footprint.to_crs(self.crs())

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

        # Compute the correct radiometry of the band
        if utils.is_uint16(band_arr):
            band_arr /= 100.0

        band_arr = self._toa_rad_to_toa_refl(band_arr, band, _VIS1_E0[band])

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "DIM_*.xml"
        mtd_archived = r"DIM_.*\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _get_tile_path(self) -> AnyPathType:
        """
        Get the DIMAP filepath

        Returns:
            AnyPathType: DIMAP filepath
        """
        return self._get_path("DIM_", "xml")

    def _get_ortho_path(self, **kwargs) -> AnyPathType:
        """
        Get the orthorectified path of the bands.

        Returns:
            AnyPathType: Orthorectified path
        """
        if self.product_type in self._proj_prod_type:
            # Compute RPCSs
            if self.is_archived:
                rpcs_file = io.BytesIO(self._read_archived_file(r".*\.rpc"))
            else:
                rpcs_file = self.path.joinpath(self.name + ".rpc")

            rpcs = utils.open_rpc_file(rpcs_file)
        else:
            rpcs = None
        return super()._get_ortho_path(rpcs=rpcs, **kwargs)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self._get_archived_rio_path(regex=r".*Preview\.tif")
            else:
                quicklook_path = str(next(self.path.glob("*Preview.tif")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path
