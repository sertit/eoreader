"""
COSMO-SkyMed products
More info here:
https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
"""
import glob
import logging
import os
import warnings
import datetime
from enum import unique
from typing import Union

from lxml import etree
import rasterio.transform
import geopandas as gpd
import numpy as np
from sertit import files, strings
from sertit.misc import ListEnum
from sertit import vectors
from shapely.geometry import Polygon

from eoreader.exceptions import InvalidProductError
from eoreader.products.sar_product import SarProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)
CSK_NAME = "COSMO-Skymed"

# Disable georef warnings here as the SAR eoreader are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class CskProductType(ListEnum):
    """
    COSMO-SkyMed products types. Take a look here:
    https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
    """
    RAW = "RAW"  # Level 0
    SCS = "SCS"  # Level 1A, Single-look Complex Slant, (un)balanced
    DGM = "DGM"  # Level 1B, Detected  Ground  Multi-look
    GEC = "GEC"  # Level 1C, Geocoded Ellipsoid Corrected
    GTC = "GTC"  # Level 1D, Geocoded Terrain Corrected


@unique
class CskSensorMode(ListEnum):
    """
    COSMO-SkyMed sensor mode. Take a look here:
    https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
    """
    HI = "HI"  # Himage
    PP = "PP"  # PingPong
    WR = "WR"  # Wide Region
    HR = "HR"  # Huge Region
    S2 = "S2"  # Spotlight 2


@unique
class CskPolarization(ListEnum):
    """
    COSMO-SkyMed polarizations  used  during  the acquisition. Take a look here:
    https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
    """
    HH = "HH"  # Horizontal  Tx/Horizontal  Rx for  Himage,  ScanSAR  and Spotlight modes
    VV = "VV"  # Vertical  Tx/  Vertical  Rx  for Himage, ScanSAR and Spotlight modes
    HV = "HV"  # Horizontal Tx/ Vertical Rx for Himage, ScanSAR
    VH = "VH"  # Vertical Tx/ Horizontal Rx for Himage, ScanSAR
    CO = "CO"  # Co-polar acquisition (HH/VV) for PingPong mode
    CH = "CH"  # Cross polar acquisition (HH/HV) with Horizontal Tx polarization for PingPong mode
    CV = "CV"  # Cross polar acquisition (VV/VH) with Vertical Tx polarization for PingPong mode


class CskProduct(SarProduct):
    """ Class for COSMO-SkyMed Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        # Rename with a more explicit one
        try:
            img = glob.glob(os.path.join(product_path, "*.h5"))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Image file (*.h5) not found in {product_path}") from ex
        self.real_name = files.get_filename(img)

        super().__init__(product_path, archive_path)
        self.raw_band_regex = "*_{}_*.h5"
        self.band_folder = self.path
        self.snap_path = img
        self.pol_channels = self.get_raw_bands()

    def get_wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open metadata file
        try:
            mtd_file = glob.glob(os.path.join(self.path, "*.h5.xml"))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Metadata file ({self.real_name}.h5.xml) not found in {self.path}") from ex

        # Open and parse XML
        # pylint: disable=I1101
        xml_tree = etree.parse(mtd_file)
        root = xml_tree.getroot()

        # Open zenith and azimuth angle
        def from_str_to_arr(geo_coord: str):
            return np.array(strings.str_to_list(geo_coord), dtype=float)[:2][::-1]

        bl_corner = br_corner = tr_corner = tl_corner = None
        for element in root:
            if element.tag == 'ProductDefinitionData':
                bl_corner = from_str_to_arr(element.findtext('GeoCoordBottomLeft'))
                br_corner = from_str_to_arr(element.findtext('GeoCoordBottomRight'))
                tl_corner = from_str_to_arr(element.findtext('GeoCoordTopLeft'))
                tr_corner = from_str_to_arr(element.findtext('GeoCoordTopRight'))
                break

        if bl_corner is None:
            raise InvalidProductError("Invalid XML: missing extent.")

        extent_wgs84 = gpd.GeoDataFrame(geometry=[Polygon([tl_corner, tr_corner, br_corner, bl_corner])],
                                        crs=vectors.WGS84)

        return extent_wgs84

    def get_product_type(self) -> None:
        """ Get products type """
        self.get_sar_product_type(prod_type_pos=1,
                                  gdrg_types=CskProductType.DGM,
                                  cplx_types=CskProductType.SCS)

    def get_sensor_mode(self) -> None:
        """
        Get products type from S2 products name (could check the metadata too)
        """
        sensor_mode_name = self.get_split_name()[3]

        # Get sensor mode
        for sens_mode in CskSensorMode:
            if sens_mode.value in sensor_mode_name:
                self.sensor_mode = sens_mode

        if not self.sensor_mode:
            raise InvalidProductError(f"Invalid {CSK_NAME} name: {self.real_name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime.datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        # 20201008224018
        date = datetime.datetime.strptime(self.get_split_name()[8], "%Y%m%d%H%M%S")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        return f"{self.get_datetime()}_CSK_{self.sensor_mode.value}_{self.product_type.value}"

    def get_split_name(self) -> list:
        """
        Get split name (erasing empty strings in it by precaution, especially for S1 data)

        Returns:
            list: Split products name
        """
        # Use the real name
        return [x for x in self.real_name.split('_') if x]
