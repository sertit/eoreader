"""
TerraSAR-X products.
More info [here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf).
"""
import glob
import logging
import os
from datetime import datetime
from enum import unique
import warnings
from typing import Union

import rasterio
import geopandas as gpd
from sertit import vectors
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.products.sar.sar_product import SarProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)
TSX_NAME = "TerraSAR-X"

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class TsxProductType(ListEnum):
    """
    TerraSAR-X projection identifier.
    Take a look [here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)
    """
    SSC = "SSC"
    """Single Look Slant Range, Complex representation"""

    MGD = "MGD"
    """Multi Look Ground Range, Detected representation"""

    GEC = "GEC"
    """Geocoded Ellipsoid Corrected, Detected representation"""

    EEC = "EEC"
    """Enhanced Ellipsoid Corrected, Detected representation"""


@unique
class TsxSensorMode(ListEnum):
    """
    TerraSAR-X sensor mode.
    Take a look [here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)
    """
    HS = "HS"
    """High Resolution Spotlight"""

    SL = "SL"
    """Spotlight"""

    ST = "ST"
    """Staring Spotlight"""

    SM = "SM"
    """Stripmap"""

    SC = "SC"
    """ScanSAR"""


@unique
class TsxPolarization(ListEnum):
    """
    TerraSAR-X polarization mode.
    Take a look [here](https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)
    """
    SINGLE = "S"
    """"Single Polarization"""

    DUAL = "D"
    """"Dual Polarization"""

    QUAD = "Q"
    """"Quad Polarization"""

    TWIN = "T"
    """"Twin Polarization"""


class TsxProduct(SarProduct):
    """ Class for TerraSAR-X Products """

    def __init__(self, product_path: str, archive_path: str = None, output_path=None) -> None:
        super().__init__(product_path, archive_path, output_path)
        self._raw_band_regex = "IMAGE_{}_*.tif"
        self._band_folder = os.path.join(self.path, "IMAGEDATA")
        self._snap_path = os.path.join(self.path, self.name + ".xml")
        self.pol_channels = self._get_raw_bands()
        self.condensed_name = self._get_condensed_name()

    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023"
        >>> prod = Reader().open(path)
        >>> prod.wgs84_extent()
                                                    geometry
        0  POLYGON ((106.65491 -6.39693, 106.96233 -6.396...
        ```

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open extent KML file
        vectors.set_kml_driver()
        try:
            extent_file = glob.glob(os.path.join(self.path, "SUPPORT", "GEARTH_POLY.kml"))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Extent file (products.kml) not found in {self.path}") from ex

        extent_wgs84 = gpd.read_file(extent_file).envelope.to_crs(vectors.WGS84)

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_product_type(self) -> None:
        """ Get products type """
        self._get_sar_product_type(prod_type_pos=2,
                                   gdrg_types=TsxProductType.MGD,
                                   cplx_types=TsxProductType.SSC)
        if self.product_type != TsxProductType.MGD:
            LOGGER.warning("Other products type than MGD has not been tested for %s data. "
                           "Use it at your own risks !", TSX_NAME)

    def _set_sensor_mode(self) -> None:
        """
        Get products type from TerraSAR-X products name (could check the metadata too)
        """
        # Get sensor mode
        try:
            self.sensor_mode = TsxSensorMode.from_value(self.split_name[4])
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2016, 2, 29, 22, 30, 18)
        >>> prod.get_datetime(as_datetime=False)
        '20160229T223018'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        date = self.split_name[7]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        return f"{self.get_datetime()}_TSX_{self.sensor_mode.value}_{self.product_type.value}"
