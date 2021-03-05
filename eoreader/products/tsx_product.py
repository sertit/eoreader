"""
TerraSAR-X products
More info here:
https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf
"""
import glob
import logging
import os
from datetime import datetime
from enum import unique
import warnings
from typing import Union

import rasterio.transform
import geopandas as gpd
from sertit import vectors
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.products.sar_product import SarProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)
TSX_NAME = "TerraSAR-X"

# Disable georef warnings here as the SAR eoreader are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class TsxProductType(ListEnum):
    """
    TerraSAR-X projection identifier. Take a look here:
    https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf
    """
    SSC = "SSC"  # Single Look Slant Range, Complex representation
    MGD = "MGD"  # Multi Look Ground Range, Detected representation
    GEC = "GEC"  # Geocoded Ellipsoid Corrected, detected representation
    EEC = "EEC"  # Enhanced Ellipsoid Corrected, detected representation


@unique
class TsxSensorMode(ListEnum):
    """
    TerraSAR-X sensor mode. Take a look here:
    https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf
    """
    HS = "HS"  # High Resolution Spotlight
    SL = "SL"  # Spotlight
    ST = "ST"  # Staring Spotlight
    SM = "SM"  # Stripmap
    SC = "SC"  # ScanSAR


@unique
class TsxPolarization(ListEnum):
    """
    TerraSAR-X polarization mode. Take a look here:
    https://tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf
    """
    SINGLE = "S"  # Single
    DUAL = "D"  # Dual
    QUAD = "Q"  # Quad
    TWIN = "T"  # Twin


class TsxProduct(SarProduct):
    """ Class for TerraSAR-X Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.raw_band_regex = "IMAGE_{}_*.tif"
        self.band_folder = os.path.join(self.path, "IMAGEDATA")
        self.snap_path = os.path.join(self.path, self.name + ".xml")
        self.pol_channels = self.get_raw_bands()

    def get_wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

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

        return extent_wgs84

    def get_product_type(self) -> None:
        """ Get products type """
        self.get_sar_product_type(prod_type_pos=2,
                                  gdrg_types=TsxProductType.MGD,
                                  cplx_types=TsxProductType.SSC)
        if self.product_type != TsxProductType.MGD:
            LOGGER.warning("Other products type than MGD has not been tested for %s data. "
                           "Use it at your own risks !", TSX_NAME)

    def get_sensor_mode(self) -> None:
        """
        Get products type from TerraSAR-X products name (could check the metadata too)
        """
        # Get sensor mode
        try:
            self.sensor_mode = TsxSensorMode.from_value(self.get_split_name()[4])
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        date = self.get_split_name()[7]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        return f"{self.get_datetime()}_TSX_{self.sensor_mode.value}_{self.product_type.value}"
