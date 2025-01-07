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
"""Landsat products"""

import difflib
import logging
import tarfile
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from lxml import etree
from lxml.builder import E
from rasterio.enums import Resampling
from sertit import AnyPath, dask, path, rasters, types
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    BLUE,
    CA,
    CIRRUS,
    CLOUDS,
    EOREADER_STAC_MAP,
    GREEN,
    NARROW_NIR,
    NIR,
    PAN,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SWIR_1,
    SWIR_2,
    SWIR_CIRRUS,
    TIR_1,
    TIR_2,
    VRE_1,
    VRE_2,
    VRE_3,
    BandNames,
    SpectralBand,
    to_str,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import OpticalProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.products.stac_product import StacProduct
from eoreader.reader import Constellation
from eoreader.stac import ASSET_ROLE, BT, DESCRIPTION, GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class LandsatProductType(ListEnum):
    """
    `Landsat products types <https://www.usgs.gov/faqs/what-landsat-data-products-are-available>`_
    """

    L1 = "L1"
    """
    Ensures that the data in the Landsat Level-1 archive are consistent in processing and data quality to support time-series analyses and data stacking.
    Each Level-1 data product includes individual spectral band files, a metadata file, and additional ancillary files.
    """

    L2 = "L2"
    """
    Level-2 Science Products are time-series observational data of sufficient length, consistency, and continuity to record effects of climate change,
    and serve as input into Landsat Level-3 Science Products.

    Only for Landsat 4 to 9.

    Only Surface Reflectances and Temperatures are handled by EOReader
    """

    L3 = "L3"
    """
    Level-3 science products represent biophysical properties of the Earth's surface and are generated from Landsat U.S. Analysis Ready Data (ARD) inputs.

    Not handled by EOReader.
    """

    ARD = "ARD"
    """
    Uses Landsat Collections Level-1 data as input
    to provide data that is processed to the highest scientific standards and placed in a tile-based structure to support time-series analysis.

    Not handled by EOReader.
    """


@unique
class LandsatInstrument(ListEnum):
    """Landsat instruments"""

    OLI_TIRS = "OLI-TIRS"
    """OLI-TIRS instruments combined, for Landsat-8 and 9 constellation"""

    OLI = "OLI"
    """OLI Instrument, for Landsat-8 and 9 constellation"""

    TIRS = "TIRS"
    """TIRS Instrument, for Landsat-8 and 9 constellation"""

    ETM = "ETM+"
    """ETM+ Instrument, for Landsat-7 constellation"""

    TM = "TM"
    """TM Instrument, for Landsat-5 and 4 constellation"""

    MSS = "MSS"
    """MSS Instrument, for Landsat-5, 4, 3, 2, 1 constellation"""


_LETTER_TO_INSTRUMENT = {
    "C": LandsatInstrument.OLI_TIRS,
    "O": LandsatInstrument.OLI,
    "T": LandsatInstrument.TM,
    "E": LandsatInstrument.ETM,
    "M": LandsatInstrument.MSS,
}


@unique
class LandsatCollection(ListEnum):
    """
    Landsat collection number.
    See `here <https://www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary>`_ for more information
    """

    COL_1 = "01"
    """Collection 1"""

    COL_2 = "02"
    """Collection 2"""


class LandsatProduct(OpticalProduct):
    """
    Class for Landsat Products

    You can use directly the .tar file in case of collection 2 products.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        # Private
        self._collection = None
        self._pixel_quality_id = None
        self._pan_res = None
        self._ms_res = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

        # Resolutions (useful only for Landsat with PAN band, i.e. OLI and ETM+)
        if self.has_band(PAN):
            self._pan_res = 15.0
            self._ms_res = self.pixel_size

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.DN
        self._has_cloud_cover = True
        self._use_filename = True

        mtd, _ = self.read_mtd()

        # Open identifier
        name = mtd.findtext(".//LANDSAT_PRODUCT_ID")
        if not name:
            raise InvalidProductError("LANDSAT_PRODUCT_ID not found in metadata !")

        # Collections are not set yet
        col_nb = mtd.findtext(".//COLLECTION_NUMBER")
        if not col_nb:
            raise InvalidProductError("COLLECTION_NUMBER not found in metadata!")
        self._collection = LandsatCollection.from_value(col_nb)

        # Collection 2 do not need to be extracted. Set True by default
        if utils.get_split_name(name)[-2] == "02":
            self.needs_extraction = False  # Fine to read .tar files
        else:
            self._collection = LandsatCollection.COL_1
            self.needs_extraction = True  # Too slow to read directly tar.gz files

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()
        if self._collection == LandsatCollection.COL_1:
            self._pixel_quality_id = "_BQA"
            self._radsat_id = "_BQA"
        else:
            self._pixel_quality_id = "_QA_PIXEL"
            self._radsat_id = "_QA_RADSAT"

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _get_path(self, band_id: str) -> AnyPathType:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            AnyPathType: band path

        """
        if self.is_archived:
            # Because of gap_mask files that have the same name structure and exists only for L7
            if self.instrument == LandsatInstrument.ETM:
                regex = rf".*(RT|T1|T2)(_SR|_ST|){band_id}\."
            else:
                regex = rf".*{band_id}\."
            prod_path = self._get_archived_rio_path(regex)
        else:
            prod_path = path.get_file_in_dir(
                self.path, f"*{band_id}.TIF", exact_name=True
            )

        return prod_path

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        if self.constellation in [
            Constellation.L8,
            Constellation.L9,
            Constellation.L7,
        ] or (
            self.constellation in [Constellation.L4, Constellation.L5]
            and self.instrument == LandsatInstrument.TM
        ):
            pixel_size = 30.0
        else:
            pixel_size = 60.0

        self.pixel_size = pixel_size

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint
               index                                           geometry
            0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        Indeed, nodata pixels vary according to the band sensor footprint,
        whereas QA nodata is where at least one band has nodata.

        We chose to keep QA nodata values for the footprint in order to show where all bands are valid.

        **TL;DR: We use the QA nodata value to determine the product's footprint**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        if self.instrument == LandsatInstrument.ETM:
            LOGGER.warning(
                "Due to the Landsat-7 gaps, this function returns a rounded footprint on the corners. "
                "Sorry for the inconvenience."
            )
            footprint_dezoom = 50
        else:
            footprint_dezoom = 1

        # Read the file with a very low resolution
        qa_path = self._get_path(self._pixel_quality_id)
        if (
            not self.is_archived
            and path.is_cloud_path(qa_path)
            and dask.get_client() is not None
        ):
            # Workaround...
            qa_path = qa_path.download_to(self.output)

        nodata_band = utils.read(
            qa_path,
            pixel_size=self.pixel_size * footprint_dezoom,
            masked=False,
        )

        # Vectorize the nodata band
        footprint = rasters.vectorize(
            nodata_band, values=1, keep_values=False, dissolve=True
        )
        # footprint = geometry.get_wider_exterior(footprint)  # No need here

        # Keep only the convex hull
        footprint.geometry = footprint.geometry.convex_hull

        return footprint

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.get_tile_name()
            '023030'

        Returns:
            str: Tile name
        """
        return self.split_name[2]

    def _set_product_type(self) -> None:
        """
        Set landsat product type.

        More on spectral bands `here <https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites>`_.
        See also the `description <https://www.usgs.gov/faqs/what-are-best-landsat-spectral-bands-use-my-research>`_.

        The naming convention of L1 data can be found
        `here <https://www.usgs.gov/faqs/what-naming-convention-landsat-collections-level-1-scenes>`_.
        """
        # Processing level
        proc_lvl = self.split_name[1]

        try:
            # ARD:  LC09_CU_016007_20220503_20220508_02, LT04_CU_017009_19821113_20210421_02
            # Level3: LC08_CU_015007_20220416_20220423_02_BA
            # Level2: LC09_L2SP_024031_20220507_20220509_02_T1

            self.product_type = LandsatProductType.from_value(proc_lvl[:-2])

            if self.product_type not in [LandsatProductType.L1, LandsatProductType.L2]:
                raise NotImplementedError(
                    "Only Landsat level 1 and 2 are implemented EOReader."
                )
            else:
                # Warning if GS (L1 only)
                if "GS" in proc_lvl:
                    LOGGER.warning(
                        "This Landsat product %s could be badly georeferenced "
                        "as only systematic geometric corrections have been applied "
                        "(using the spacecraft ephemeris data).",
                        self.name,
                    )

        except ValueError as exc:
            raise InvalidProductError(
                "Landsat level 3 and ARD are not handled by EOReader!"
            ) from exc

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        instrument_letter = self.split_name[0][1]
        if instrument_letter == "T" and self.constellation in [
            Constellation.L8,
            Constellation.L9,
        ]:
            self.instrument = LandsatInstrument.TIRS
        else:
            self.instrument = _LETTER_TO_INSTRUMENT[instrument_letter]

        if self.instrument in [LandsatInstrument.OLI, LandsatInstrument.TIRS]:
            LOGGER.warning(
                "Product with TIRS or OLI only have not been tested in EOReader, use it at tour own risk."
            )

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation"""
        constellation_id = f"L{int(self.split_name[0][2:4])}"
        return getattr(Constellation, constellation_id)

    def _map_bands(self) -> None:
        """
        Map bands
        """
        if self.instrument == LandsatInstrument.MSS:
            self._map_bands_mss(version=int(self.constellation_id[-1]))
        elif self.instrument == LandsatInstrument.TM:
            self._map_bands_tm()
        elif self.instrument == LandsatInstrument.ETM:
            self._map_bands_etm()
        elif self.instrument in [
            LandsatInstrument.OLI_TIRS,
            LandsatInstrument.OLI,
            LandsatInstrument.TIRS,
        ]:
            self._map_bands_oli()

    def _map_bands_mss(self, version: int) -> None:
        """
        Map bands MSS

        Args:
            version (int): Landsat version
        """
        vre_dict = {
            NAME: "B6" if version < 4 else "B3",
            ID: "6" if version < 4 else "3",
            GSD: 60,
            WV_MIN: 700,
            WV_MAX: 800,
            DESCRIPTION: "Vegetation boundary between land and water, and landforms",
        }

        nir_dict = {
            NAME: "B7" if version < 4 else "B4",
            ID: "7" if version < 4 else "4",
            GSD: 60,
            WV_MIN: 800,
            WV_MAX: 1100,
            DESCRIPTION: "Penetrates atmospheric haze best, emphasizes vegetation, boundary between land and water, and landforms",
        }

        mss_bands = {
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "B4" if version < 4 else "B1",
                    ID: "4" if version < 4 else "1",
                    GSD: 60,
                    WV_MIN: 500,
                    WV_MAX: 600,
                    DESCRIPTION: "Sediment-laden water, delineates areas of shallow water",
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "B5" if version < 4 else "B2",
                    ID: "5" if version < 4 else "2",
                    GSD: 60,
                    WV_MIN: 600,
                    WV_MAX: 700,
                    DESCRIPTION: "Cultural features",
                },
            ),
            VRE_1: SpectralBand(eoreader_name=VRE_1, **vre_dict),
            VRE_2: SpectralBand(eoreader_name=VRE_2, **vre_dict),
            VRE_3: SpectralBand(eoreader_name=VRE_3, **vre_dict),
            NARROW_NIR: SpectralBand(eoreader_name=NARROW_NIR, **nir_dict),
            NIR: SpectralBand(eoreader_name=NIR, **nir_dict),
        }
        self.bands.map_bands(mss_bands)

    def _map_bands_tm(self) -> None:
        """
        Map bands TM
        """
        tm_bands = {
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "B1",
                    ID: "1",
                    GSD: 30,
                    WV_MIN: 450,
                    WV_MAX: 520,
                    DESCRIPTION: "Bathymetric mapping, distinguishing soil from vegetation and deciduous from coniferous vegetation",
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "B2",
                    ID: "2",
                    GSD: 30,
                    WV_MIN: 520,
                    WV_MAX: 600,
                    DESCRIPTION: "Emphasizes peak vegetation, which is useful for assessing plant vigor",
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "B3",
                    ID: "3",
                    GSD: 30,
                    WV_MIN: 630,
                    WV_MAX: 690,
                    DESCRIPTION: "Discriminates vegetation slopes",
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "B4",
                    ID: "4",
                    GSD: 30,
                    WV_MIN: 760,
                    WV_MAX: 900,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "B4",
                    ID: "4",
                    GSD: 30,
                    WV_MIN: 760,
                    WV_MAX: 900,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "B5",
                    ID: "5",
                    GSD: 30,
                    WV_MIN: 1550,
                    WV_MAX: 1750,
                    DESCRIPTION: "Discriminates moisture content of soil and vegetation; penetrates thin clouds",
                },
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{
                    NAME: "B7",
                    ID: "7",
                    GSD: 30,
                    WV_MIN: 2080,
                    WV_MAX: 2350,
                    DESCRIPTION: "Hydrothermally altered rocks associated with mineral deposits",
                },
            ),
            TIR_1: SpectralBand(
                eoreader_name=TIR_1,
                **{
                    NAME: "B6",
                    ID: "6",
                    GSD: 120,
                    WV_MIN: 10400,
                    WV_MAX: 12500,
                    DESCRIPTION: "Spatial resolution for Band 6 (thermal infrared) is 120 meters, but is resampled to 30-meter pixels. Thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
            TIR_2: SpectralBand(
                eoreader_name=TIR_2,
                **{
                    NAME: "B6",
                    ID: "6",
                    GSD: 120,
                    WV_MIN: 10400,
                    WV_MAX: 12500,
                    DESCRIPTION: "Spatial resolution for Band 6 (thermal infrared) is 120 meters, but is resampled to 30-meter pixels. Thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
        }

        self.bands.map_bands(tm_bands)

    def _map_bands_etm(self) -> None:
        """
        Map bands ETM
        """
        etm_bands = {
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "B1",
                    ID: "1",
                    GSD: 30,
                    WV_MIN: 450,
                    WV_MAX: 520,
                    DESCRIPTION: "Bathymetric mapping, distinguishing soil from vegetation and deciduous from coniferous vegetation",
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "B2",
                    ID: "2",
                    GSD: 30,
                    WV_MIN: 520,
                    WV_MAX: 600,
                    DESCRIPTION: "Emphasizes peak vegetation, which is useful for assessing plant vigor",
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "B3",
                    ID: "3",
                    GSD: 30,
                    WV_MIN: 630,
                    WV_MAX: 690,
                    DESCRIPTION: "Discriminates vegetation slopes",
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "B4",
                    ID: "4",
                    GSD: 30,
                    WV_MIN: 770,
                    WV_MAX: 900,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "B4",
                    ID: "4",
                    GSD: 30,
                    WV_MIN: 770,
                    WV_MAX: 900,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "B5",
                    ID: "5",
                    GSD: 30,
                    WV_MIN: 1550,
                    WV_MAX: 1750,
                    DESCRIPTION: "Discriminates moisture content of soil and vegetation; penetrates thin clouds",
                },
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{
                    NAME: "B7",
                    ID: "7",
                    GSD: 30,
                    WV_MIN: 2090,
                    WV_MAX: 2350,
                    DESCRIPTION: "Hydrothermally altered rocks associated with mineral deposits",
                },
            ),
            PAN: SpectralBand(
                eoreader_name=PAN,
                **{
                    NAME: "B8",
                    ID: "8",
                    GSD: 15,
                    WV_MIN: 520,
                    WV_MAX: 900,
                    DESCRIPTION: "15 meter resolution, sharper image definition",
                },
            ),
            # TODO: better manage L-7 TIR bands ?
            # The band 61 (low gain mode) is used when surface brightness is high (e.g., desert, or less vegetated areas),
            # and band 62 (high gain mode) when surface brightness is lower (e.g., vegetated areas)
            # (According to the gain setting rule of Landsat Project Science Ofﬁce (2001)).
            TIR_1: SpectralBand(
                eoreader_name=TIR_1,
                **{
                    NAME: "B6_VCID_1",
                    ID: "6_VCID_1",
                    GSD: 60,
                    WV_MIN: 10400,
                    WV_MAX: 12500,
                    DESCRIPTION: "Spatial resolution for Band 6 (thermal infrared) is 60 meters, but is resampled to 30-meter pixels. Thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
            TIR_2: SpectralBand(
                eoreader_name=TIR_2,
                **{
                    NAME: "B6_VCID_2",
                    ID: "6_VCID_2",
                    GSD: 60,
                    WV_MIN: 10400,
                    WV_MAX: 12500,
                    DESCRIPTION: "Spatial resolution for Band 6 (thermal infrared) is 60 meters, but is resampled to 30-meter pixels. Thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
        }

        if self.product_type == LandsatProductType.L2:
            etm_bands.pop(PAN)
            etm_bands.pop(TIR_2)
            etm_bands[TIR_1] = etm_bands[TIR_1].update(name="B6", id="6")

        self.bands.map_bands(etm_bands)

    def _map_bands_oli(self) -> None:
        """
        Map bands OLI-TIRS
        """
        oli_bands = {
            CA: SpectralBand(
                eoreader_name=CA,
                **{
                    NAME: "Coastal aerosol",
                    ID: "1",
                    GSD: 30,
                    WV_MIN: 430,
                    WV_MAX: 450,
                    DESCRIPTION: "Coastal and aerosol studies",
                },
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "Blue",
                    ID: "2",
                    GSD: 30,
                    WV_MIN: 450,
                    WV_MAX: 510,
                    DESCRIPTION: "Bathymetric mapping, distinguishing soil from vegetation and deciduous from coniferous vegetation",
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "Green",
                    ID: "3",
                    GSD: 30,
                    WV_MIN: 530,
                    WV_MAX: 590,
                    DESCRIPTION: "Emphasizes peak vegetation, which is useful for assessing plant vigor",
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "Red",
                    ID: "4",
                    GSD: 30,
                    WV_MIN: 640,
                    WV_MAX: 670,
                    DESCRIPTION: "Discriminates vegetation slopes",
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "Near Infrared (NIR)",
                    ID: "5",
                    GSD: 30,
                    WV_MIN: 850,
                    WV_MAX: 880,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "Near Infrared (NIR)",
                    ID: "5",
                    GSD: 30,
                    WV_MIN: 850,
                    WV_MAX: 880,
                    DESCRIPTION: "Emphasizes biomass content and shorelines",
                },
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "SWIR 1",
                    ID: "6",
                    GSD: 30,
                    WV_MIN: 1570,
                    WV_MAX: 1650,
                    DESCRIPTION: "Discriminates moisture content of soil and vegetation; penetrates thin clouds",
                },
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{
                    NAME: "SWIR 2",
                    ID: "7",
                    GSD: 30,
                    WV_MIN: 2110,
                    WV_MAX: 2290,
                    DESCRIPTION: "Improved moisture content of soil and vegetation; penetrates thin clouds",
                },
            ),
            PAN: SpectralBand(
                eoreader_name=PAN,
                **{
                    NAME: "Panchromatic",
                    ID: "8",
                    GSD: 15,
                    WV_MIN: 500,
                    WV_MAX: 680,
                    DESCRIPTION: "15 meter resolution, sharper image definition",
                },
            ),
            SWIR_CIRRUS: SpectralBand(
                eoreader_name=SWIR_CIRRUS,
                **{
                    NAME: "Cirrus",
                    ID: "9",
                    GSD: 30,
                    WV_MIN: 1360,
                    WV_MAX: 1380,
                    DESCRIPTION: "Improved detection of cirrus cloud contamination",
                },
            ),
            TIR_1: SpectralBand(
                eoreader_name=TIR_1,
                **{
                    NAME: "Thermal Infrared (TIRS) 1",
                    ID: "10",
                    GSD: 100,
                    WV_MIN: 10600,
                    WV_MAX: 11190,
                    DESCRIPTION: "100 meter resolution, thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
            TIR_2: SpectralBand(
                eoreader_name=TIR_2,
                **{
                    NAME: "Thermal Infrared (TIRS) 2",
                    ID: "11",
                    GSD: 100,
                    WV_MIN: 11500,
                    WV_MAX: 12510,
                    DESCRIPTION: "100 meter resolution, improved thermal mapping and estimated soil moisture",
                    ASSET_ROLE: BT,
                },
            ),
        }

        if self.product_type == LandsatProductType.L2:
            oli_bands.pop(SWIR_CIRRUS)
            oli_bands.pop(TIR_2)
            oli_bands.pop(PAN)

        self.bands.map_bands(oli_bands)

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 5, 18, 16, 34, 7)
            >>> prod.get_datetime(as_datetime=False)
            '20200518T163407'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            mtd_data, _ = self._read_mtd()

            date = mtd_data.findtext(".//DATE_ACQUIRED")
            hours = mtd_data.findtext(".//SCENE_CENTER_TIME").replace('"', "")[:-3]
            if not date or not hours:
                raise InvalidProductError(
                    "DATE_ACQUIRED or SCENE_CENTER_TIME not found in metadata!"
                )

            date = (
                f"{datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')}"
                f"T{datetime.strptime(hours, '%H:%M:%S.%f').strftime('%H%M%S')}"
            )

            if as_datetime:
                date = datetime.strptime(date, DATETIME_FMT)

        else:
            date = self.datetime
            if not as_datetime:
                date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier (replace for txt files)
        name = root.findtext(".//LANDSAT_PRODUCT_ID").replace('"', "")
        if not name:
            raise InvalidProductError("LANDSAT_PRODUCT_ID not found in metadata!")

        return name

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2/LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',
                <SpectralBandNames.RED: 'RED'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2/LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF'
            }

        Args:
            band_list (list): List of the wanted bands
            pixel_size (float): Useless here
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            if not self.has_band(band):
                raise InvalidProductError(
                    f"Non existing band ({band.name}) "
                    f"for Landsat-{self.product_type.name} products"
                )
            band_id = self.bands[band].id

            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, pixel_size=pixel_size, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                try:
                    band_paths[band] = self._get_path(f"_B{band_id}")
                except FileNotFoundError as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({band_id}) band for {self.path}"
                    ) from ex

        return band_paths

    @cache
    def _read_mtd(self, force_pd=False) -> (etree._Element, dict):
        """
        Read Landsat metadata as:

         - :code:`pandas.DataFrame` whatever its collection is (by default for collection 1)
         - XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)

        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of an XML root + namespace
        Returns:
            Tuple[Union[pd.DataFrame, etree._Element], dict]:
                Metadata as a Pandas.DataFrame or as (etree._Element, dict): Metadata XML root and its namespaces
        """
        # Try with XML (we don't know what collection it is)
        try:
            # Open XML metadata
            mtd_from_path = "_MTL.xml"
            mtd_archived = r"_MTL\.xml"
            mtd_data = self._read_mtd_xml(mtd_from_path, mtd_archived)
        except (InvalidProductError, FileNotFoundError):
            mtd_name = "_MTL.txt"
            if self.is_archived:
                # We need to extract the file in memory to be used with pandas
                with tarfile.open(self.path, "r") as tar_ds:
                    info = [f.name for f in tar_ds.getmembers() if mtd_name in f.name][
                        0
                    ]
                    mtd_path = tar_ds.extractfile(info)
            else:
                # FOR COLLECTION 1 AND 2
                tar_ds = None
                try:
                    try:
                        mtd_path = next(self.path.glob(f"**/*{mtd_name}"))
                    except ValueError:
                        mtd_path = next(self.path.glob(f"*{mtd_name}"))

                    if not mtd_path.is_file():
                        raise InvalidProductError(
                            f"No metadata file found in {self.name} !"
                        )
                except StopIteration as exc:
                    raise InvalidProductError(
                        f"No metadata file found in {self.name} !"
                    ) from exc

            # Parse
            mtd_data = pd.read_table(
                mtd_path,
                sep=r"\s=\s",
                names=["NAME", "value"],
                skipinitialspace=True,
                engine="python",
            )

            # Workaround an unexpected behaviour in pandas !
            if any(mtd_data.NAME == "="):
                mtd_data = pd.read_table(
                    mtd_path,
                    sep="=",
                    names=["NAME", "=", "value"],
                    usecols=[0, 2],
                    skipinitialspace=True,
                )

            # Remove useless rows
            mtd_data = mtd_data[~mtd_data["NAME"].isin(["GROUP", "END_GROUP", "END"])]

            # Set index
            mtd_data = mtd_data.set_index("NAME").T

            # Create XML
            attr_names = mtd_data.columns.to_list()
            global_attr = [
                E(str(attr), str(mtd_data[attr].iat[0])) for attr in attr_names
            ]
            mtd = E.landsat_global_attributes(*global_attr)
            mtd_el = etree.fromstring(
                etree.tostring(
                    mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
                )
            )
            mtd_data = (mtd_el, {})

            # Close if needed
            if tar_ds:
                tar_ds.close()

        return mtd_data

    def _read_band(
        self,
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            pixel_size (Union[tuple, list, float]): Size of the pixels of the wanted band, in dataset unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray
        """
        if self.is_archived:
            filename = path.get_filename(str(band_path).split("!")[-1])
        else:
            filename = path.get_filename(band_path)

        if self._pixel_quality_id in filename or self._radsat_id in filename:
            band_arr = utils.read(
                band_path,
                pixel_size=pixel_size,
                size=size,
                resampling=Resampling.nearest,  # NEAREST TO KEEP THE FLAGS
                masked=False,
                as_type=np.uint16,
                **kwargs,
            )
        else:
            # Read band (call superclass generic method)
            band_arr = utils.read(
                band_path,
                pixel_size=pixel_size,
                size=size,
                as_type=np.float32,
                resampling=Resampling.bilinear,
                **kwargs,
            )

        return band_arr

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
        # Get band name: the last number of the filename:
        # ie: 'LC08_L1TP_200030_20191218_20191226_01_T1_B1'
        if self.is_archived:
            filename = path.get_filename(str(band_path).split("!")[-1])
        else:
            filename = path.get_filename(band_path)

            # Convert raw bands from DN to correct reflectance
        if not (
            self._pixel_quality_id in filename or self._radsat_id in filename
        ) and not filename.startswith(self.condensed_name):
            # Open mtd
            mtd, _ = self._read_mtd()

            # Get band nb and corresponding coeff
            band_name = self.bands[band].id
            try:
                # Thermal (10/11)
                if band in [TIR_1, TIR_2]:
                    band_arr = self._to_tb(band_arr, mtd, band_name)

                else:
                    # Original band name
                    band_arr = self._to_refl(band_arr, mtd, band_name)
            except TypeError as exc:
                raise InvalidProductError(
                    f"Cannot find additive or multiplicative "
                    f"rescaling factor for bands ({band.name}, "
                    f"number {band_name}) in metadata"
                ) from exc

        return band_arr

    def _to_tb(
        self,
        band_arr: xr.DataArray,
        mtd: etree._Element,
        band_name: str,
    ) -> xr.DataArray:
        """
        Converts band to brightness temperature

        https://www.usna.edu/Users/oceano/pguth/md_help/remote_sensing_course/landsat_thermal.htm

        Args:
            band_arr (xr.DataArray): Band array
            mtd (etree._Element): Metadata
            band_name (str): Band name

        Returns:
            xr.DataArray: Band in brightness temperature
        """
        if self.product_type == LandsatProductType.L1:
            # Get coeffs to convert DN to radiance
            c_mul_str = "RADIANCE_MULT_BAND_" + band_name
            c_add_str = "RADIANCE_ADD_BAND_" + band_name
            c_mul = mtd.findtext(f".//{c_mul_str}")
            c_add = mtd.findtext(f".//{c_add_str}")

            # Manage NULL values
            try:
                c_mul = float(c_mul)
            except ValueError:
                c_mul = 1.0
            try:
                c_add = float(c_add)
            except ValueError:
                c_add = 0.0

            band_arr = c_mul * band_arr + c_add

            # Get coeffs to convert radiance to TB
            k1_str = "K1_CONSTANT_BAND_" + band_name
            k2_str = "K2_CONSTANT_BAND_" + band_name
            k1 = float(mtd.findtext(f".//{k1_str}"))
            k2 = float(mtd.findtext(f".//{k2_str}"))
            band_arr = k2 / np.log(k1 / band_arr + 1)
        elif self.product_type == LandsatProductType.L2:
            c_mul_str = "TEMPERATURE_MULT_BAND_ST_B" + band_name
            c_add_str = "TEMPERATURE_ADD_BAND_ST_B" + band_name

            # Get coeffs to convert DN to reflectance
            c_mul = mtd.findtext(f".//{c_mul_str}")
            c_add = mtd.findtext(f".//{c_add_str}")

            # Manage NULL values
            try:
                c_mul = float(c_mul)
            except ValueError:
                c_mul = 0.00341802
            try:
                c_add = float(c_add)
            except ValueError:
                c_add = 149.0

            # Compute the correct reflectance of the band and set no data to 0
            band_arr = c_mul * band_arr + c_add  # Already in float
        else:
            raise NotImplementedError

        return band_arr

    def _to_refl(
        self,
        band_arr: xr.DataArray,
        mtd: etree._Element,
        band_name: str,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array
            mtd (etree._Element): Metadata
            band_name (str): Band name

        Returns:
            xr.DataArray: Band in reflectance
        """
        if self.product_type == LandsatProductType.L1:
            # Only one coeff field here
            coeff_mtd = mtd
        elif self.product_type == LandsatProductType.L2:
            coeff_mtd = mtd.find(".//LEVEL2_SURFACE_REFLECTANCE_PARAMETERS")
        else:
            raise NotImplementedError

        c_mul_str = "REFLECTANCE_MULT_BAND_" + band_name
        c_add_str = "REFLECTANCE_ADD_BAND_" + band_name

        # Get coeffs to convert DN to reflectance
        c_mul = coeff_mtd.findtext(f".//{c_mul_str}")
        c_add = coeff_mtd.findtext(f".//{c_add_str}")

        # Manage NULL values
        try:
            c_mul = float(c_mul)
        except ValueError:
            c_mul = 1.0 if self.product_type == LandsatProductType.L1 else 2.75e-05

        try:
            c_add = float(c_add)
        except ValueError:
            c_add = 0.0 if self.product_type == LandsatProductType.L1 else -0.2

        # Compute the correct reflectance of the band and set no data to 0
        band_arr = c_mul * band_arr + c_add  # Already in float

        return band_arr

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as a SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # Open QA band
        landsat_qa_path = self._get_path(self._radsat_id)
        qa_arr = self._read_band(
            landsat_qa_path, size=(band_arr.rio.width, band_arr.rio.height), **kwargs
        )

        if self._collection == LandsatCollection.COL_1:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band
            # Bit ids
            nodata_id = 0  # Fill value
            dropped_id = 1  # Dropped pixel or terrain occlusion
            # Set nodata to every saturated pixel, even if only 1-2 bands are touched by it
            # -> 01 or 10 or 11
            # -> bit 2 or bit 3
            sat_id_1 = 2
            sat_id_2 = 3
            nodata, dropped, sat_1, sat_2 = rasters.read_bit_array(
                qa_arr, [nodata_id, dropped_id, sat_id_1, sat_id_2]
            )
            mask = nodata | dropped | sat_1 | sat_2
        else:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands
            # SATURATED & OTHER PIXELS
            try:
                band_id = int(self.bands[band].id)
            except ValueError as exc:
                if (
                    band in [TIR_1, TIR_2]
                    and self.constellation_id == Constellation.L7.name
                ):
                    band_id = 6
                else:
                    raise InvalidProductError(
                        f"Cannot convert {self.bands[band].id} to integer."
                    ) from exc

            # Bit ids
            sat_id = band_id - 1  # Saturated pixel
            if self.instrument not in [
                LandsatInstrument.OLI,
                LandsatInstrument.TIRS,
                LandsatInstrument.OLI_TIRS,
            ]:
                other_id = 11  # Terrain occlusion
            else:
                other_id = 9  # Dropped pixels

            sat, other = rasters.read_bit_array(qa_arr, [sat_id, other_id])

            # If collection 2, nodata has to be found in pixel QA file
            landsat_stat_path = self._get_path(self._pixel_quality_id)
            pixel_arr = self._read_band(
                landsat_stat_path,
                size=(band_arr.rio.width, band_arr.rio.height),
                **kwargs,
            )
            nodata = xr.where(pixel_arr == 1, 1, 0)

            mask = sat | other | nodata

        return self._set_nodata_mask(band_arr, mask)

    def _manage_nodata(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage only nodata pixels

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """

        if self._collection == LandsatCollection.COL_1:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band
            # Open QA band
            landsat_qa_path = self._get_path(self._radsat_id)
            qa_arr = self._read_band(
                landsat_qa_path,
                size=(band_arr.rio.width, band_arr.rio.height),
                **kwargs,
            )

            # Bit ids
            nodata_id = 0  # Fill value
            nodata = rasters.read_bit_array(qa_arr, nodata_id)
        else:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands
            # If collection 2, nodata has to be found in pixel QA file
            landsat_stat_path = self._get_path(self._pixel_quality_id)
            pixel_arr = self._read_band(
                landsat_stat_path,
                size=(band_arr.rio.width, band_arr.rio.height),
                **kwargs,
            )
            nodata = xr.where(pixel_arr == 1, 1, 0).astype(np.uint8)

        return self._set_nodata_mask(band_arr, nodata)

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        bands = types.make_iterable(bands)

        if pixel_size is None and size is not None:
            pixel_size = self._pixel_size_from_img_size(size)
        band_paths = self.get_band_paths(bands, pixel_size=pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
        )

        return band_arrays

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (140.80752656, 61.93065805)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Retrieve angles
        mtd_data, _ = self._read_mtd()
        try:
            azimuth_angle = float(mtd_data.findtext(".//SUN_AZIMUTH"))
            zenith_angle = 90.0 - float(mtd_data.findtext(".//SUN_ELEVATION"))
        except TypeError as exc:
            raise InvalidProductError(
                "SUN_AZIMUTH or SUN_ELEVATION not found in metadata!"
            ) from exc

        return azimuth_angle, zenith_angle

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_Lx{instrument}_{tile}_{product_type}).

        Returns:
            str: Condensed Landsat name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.tile_name}_{self.instrument.name}"

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands]
        """
        if self.instrument in [
            LandsatInstrument.OLI,
            LandsatInstrument.TIRS,
            LandsatInstrument.OLI_TIRS,
        ]:
            has_band = True
        elif self.instrument in [LandsatInstrument.ETM, LandsatInstrument.TM]:
            has_band = self._e_tm_has_cloud_band(band)
        elif self.instrument == LandsatInstrument.MSS:
            has_band = self._mss_has_cloud_band(band)
        else:
            raise InvalidProductError(f"Invalid product type: {self.instrument}")

        return has_band

    @staticmethod
    def _mss_has_cloud_band(band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        """
        return band in [RAW_CLOUDS, CLOUDS, ALL_CLOUDS]

    @staticmethod
    def _e_tm_has_cloud_band(band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        """
        return band in [RAW_CLOUDS, CLOUDS, ALL_CLOUDS, SHADOWS]

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands]


        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            # Open QA band
            landsat_qa_path = self._get_path(self._pixel_quality_id)
            qa_arr = self._read_band(landsat_qa_path, pixel_size=pixel_size, size=size)

            if self.instrument in [
                LandsatInstrument.OLI,
                LandsatInstrument.TIRS,
                LandsatInstrument.OLI_TIRS,
            ]:
                band_dict = self._open_oli_clouds(qa_arr, bands)
            elif self.instrument in [
                LandsatInstrument.ETM,
                LandsatInstrument.TM,
            ]:
                band_dict = self._open_e_tm_clouds(qa_arr, bands)
            elif self.instrument == LandsatInstrument.MSS:
                band_dict = self._open_mss_clouds(qa_arr, bands)
            else:
                raise InvalidProductError(f"Invalid product type: {self.instrument}")

        return band_dict

    def _open_mss_clouds(self, qa_arr: xr.DataArray, band_list: list) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-MSS clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/media/files/landsat-1-5-mss-collection-2-level-1-data-format-control-book]


        Args:
            qa_arr (xr.DataArray): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        band_dict = {}

        # Get clouds and nodata
        nodata_id = 0
        cloud_id = (
            4 if self._collection == LandsatCollection.COL_1 else 3
        )  # Clouds with high confidence

        clouds = None
        if ALL_CLOUDS in band_list or CLOUDS in band_list:
            nodata, cld = rasters.read_bit_array(qa_arr, [nodata_id, cloud_id])
            clouds = self._create_mask(qa_arr, cld, nodata)

        for band in band_list:
            if band in [ALL_CLOUDS, CLOUDS]:
                cloud = clouds
            elif band == RAW_CLOUDS:
                cloud = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for Landsat-MSS constellation: {band}"
                )

            # Rename
            band_name = to_str(band)[0]

            # Multi bands -> do not change long name
            if band != RAW_CLOUDS:
                cloud.attrs["long_name"] = band_name
            band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _open_e_tm_clouds(
        self, qa_arr: xr.DataArray, band_list: Union[list, BandNames]
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-(E)TM clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2 TM)[https://www.usgs.gov/media/files/landsat-4-5-tm-collection-2-level-1-data-format-control-book]
        - (COL 2 ETM)[https://www.usgs.gov/media/files/landsat-7-etm-collection-2-level-1-data-format-control-book]


        Args:
            qa_arr (xr.DataArray): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        band_dict = {}

        # Get clouds and nodata
        nodata = None
        cld = None
        shd = None
        if any(band in [ALL_CLOUDS, CLOUDS, SHADOWS] for band in band_list):
            if self._collection == LandsatCollection.COL_1:
                # Bit id
                nodata_id = 0
                cloud_id = 4  # Clouds with high confidence
                shd_conf_1_id = 7
                shd_conf_2_id = 8
                nodata, cld, shd_conf_1, shd_conf_2 = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_conf_1_id, shd_conf_2_id]
                )
                shd = shd_conf_1 & shd_conf_2
            else:
                # Bit ids
                nodata_id = 0
                cloud_id = 3  # Clouds with high confidence
                shd_id = 4  # Shadows with high confidence
                nodata, cld, shd = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_id]
                )

        for band in band_list:
            if band == ALL_CLOUDS:
                cloud = self._create_mask(qa_arr, cld | shd, nodata)
            elif band == SHADOWS:
                cloud = self._create_mask(qa_arr, shd, nodata)
            elif band == CLOUDS:
                cloud = self._create_mask(qa_arr, cld, nodata)
            elif band == RAW_CLOUDS:
                cloud = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for Landsat-(E)TM constellations: {band}"
                )

            # Rename
            band_name = to_str(band)[0]

            # Multi bands -> do not change long name
            if band != RAW_CLOUDS:
                cloud.attrs["long_name"] = band_name
            band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _open_oli_clouds(
        self, qa_arr: xr.DataArray, band_list: Union[list, BandNames]
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-OLI clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/media/files/landsat-8-level-1-data-format-control-book]


        Args:
            qa_arr (xr.DataArray): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        band_dict = {}

        # Get clouds and nodata
        nodata = None
        cld = None
        shd = None
        cir = None
        if any(band in [ALL_CLOUDS, CLOUDS, SHADOWS] for band in band_list):
            if self._collection == LandsatCollection.COL_1:
                # Bit ids
                nodata_id = 0
                cloud_id = 4  # Clouds with high confidence
                shd_conf_1_id = 7
                shd_conf_2_id = 8
                cir_conf_1_id = 11
                cir_conf_2_id = 12

                # Read binary mask
                (
                    nodata,
                    cld,
                    shd_conf_1,
                    shd_conf_2,
                    cir_conf_1,
                    cir_conf_2,
                ) = rasters.read_bit_array(
                    qa_arr,
                    [
                        nodata_id,
                        cloud_id,
                        shd_conf_1_id,
                        shd_conf_2_id,
                        cir_conf_1_id,
                        cir_conf_2_id,
                    ],
                )

                shd = shd_conf_1 & shd_conf_2
                cir = cir_conf_1 & cir_conf_2
            else:
                # Bit ids
                nodata_id = 0
                cloud_id = 3  # Clouds with high confidence
                shd_id = 4  # Shadows with high confidence
                cir_id = 2  # Cirrus with high confidence
                nodata, cld, shd, cir = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_id, cir_id]
                )

        for band in band_list:
            if band == ALL_CLOUDS:
                cloud = self._create_mask(qa_arr, cld | shd | cir, nodata)
            elif band == SHADOWS:
                cloud = self._create_mask(qa_arr, shd, nodata)
            elif band == CLOUDS:
                cloud = self._create_mask(qa_arr, cld, nodata)
            elif band == CIRRUS:
                cloud = self._create_mask(qa_arr, cir, nodata)
            elif band == RAW_CLOUDS:
                cloud = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for {self.instrument.value} constellations: {band}"
                )

            # Rename
            band_name = to_str(band)[0]

            # Multi bands -> do not change long name
            if band != RAW_CLOUDS:
                cloud.attrs["long_name"] = band_name
            band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    @cache
    def get_cloud_cover(self) -> float:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_cloud_cover()
            55.5

        Returns:
            float: Cloud cover as given in the metadata
        """

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(".//CLOUD_COVER"))
        except (InvalidProductError, TypeError):
            LOGGER.warning("'CLOUD_COVER' not found in metadata!")
            cc = 0

        return cc

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(
                    regex=r".*thumb_large\.jpeg"
                )
            else:
                quicklook_path = next(self.path.glob("*thumb_large.jpeg"))
            quicklook_path = str(quicklook_path)
        except (StopIteration, FileNotFoundError):
            # Thumbnail only exists for collection 2, not for one: do not throw a warning in this case
            if self._collection == LandsatCollection.COL_2:
                LOGGER.warning(f"No quicklook found in {self.condensed_name}")
            else:
                LOGGER.debug(
                    f"No quicklook available for {self.constellation.value} Collection-1 data!"
                )

        return quicklook_path


class LandsatStacProduct(StacProduct, LandsatProduct):
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

        # Copy the kwargs
        super_kwargs = kwargs.copy()

        # Get STAC Item
        self.item = self._set_item(product_path, **super_kwargs)
        """ STAC Item of the product """

        if not self._is_mpc():
            self.default_clients = [
                self.get_e84_client(),
                self.get_usgs_client(),
                # Not yet handled
                # HttpClient(ClientSession(base_url="https://landsatlook.usgs.gov", auth=BasicAuth(login="", password="")))
            ]
        self.clients = super_kwargs.pop("client", self.default_clients)

        if product_path is None:
            # Canonical link is always the second one
            # TODO: check if ok
            product_path = AnyPath(self.item.links[1].target).parent

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _get_path(self, band_id: str) -> str:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            AnyPathType: band path

        """
        if band_id.startswith("_"):
            band_id = band_id[1:]

        if band_id.lower() in self.item.assets:
            asset_name = band_id.lower()
        elif band_id.startswith("B"):
            band_name = [
                band_name
                for band_name, band in self.bands.items()
                if band is not None and f"B{band.id}" == band_id
            ][0]
            asset_name = EOREADER_STAC_MAP[band_name].value
        else:
            try:
                asset_name = difflib.get_close_matches(
                    band_id, self.item.assets.keys(), cutoff=0.5, n=1
                )[0]
            except Exception as exc:
                raise FileNotFoundError(
                    f"Impossible to find an asset in {list(self.item.assets.keys())} close enough to '{band_id}'"
                ) from exc

        return self.sign_url(self.item.assets[asset_name].href)

    def _read_mtd(self, force_pd=False) -> (etree._Element, dict):
        """
        Read Landsat metadata as:

         - :code:`pandas.DataFrame` whatever its collection is (by default for collection 1)
         - XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)

        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of an XML root + namespace
        Returns:
            Tuple[Union[pd.DataFrame, etree._Element], dict]:
                Metadata as a Pandas.DataFrame or as (etree._Element, dict): Metadata XML root and its namespaces
        """
        return self._read_mtd_xml_stac(self._get_path("mtl.xml"))

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        return self._get_path("rendered_preview")


class LandsatMpcStacProduct(LandsatStacProduct):
    pass
