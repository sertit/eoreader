"""
RADARSAT-2 products
More info here:
https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs
"""
import glob
import logging
import os
import difflib
import re
import warnings
import zipfile
from datetime import datetime
from enum import unique
from typing import Union

from lxml import etree
import rasterio.transform
import geopandas as gpd
from sertit.misc import ListEnum
from sertit import vectors
from sertit.vectors import WGS84

from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.products.sar_product import SarProduct
from eoreader.utils import EEO_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EEO_NAME)
RS2_NAME = "RADARSAT-2"

# Disable georef warnings here as the SAR eoreader are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class Rs2ProductType(ListEnum):
    """
    RADARSAT-2 projection identifier. Take a look here:
    https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs
    """
    SLC = "SLC"  # Single-look complex
    SGX = "SGX"  # SAR georeferenced extra
    SGF = "SGF"  # SAR georeferenced fine
    SCN = "SCN"  # ScanSAR narrow beam
    SCW = "SCW"  # ScanSAR wide beam
    SCF = "SCF"  # ScanSAR fine
    SCS = "SCS"  # ScanSAR sampled
    SSG = "SSG"  # SAR systematic geocorrected
    SPG = "SPG"  # SAR precision geocorrected


# WARNING ! The name in the metadata may vary !!!
@unique
class Rs2SensorMode(ListEnum):
    """
    RADARSAT-2 sensor mode. Take a look here:
    https://mdacorporation.com/docs/default-source/technical-documents/geospatial-services/52-1238_rs2_product_description.pdf
    """
    # Single Beam Modes
    S = "Standard"
    W = "Wide"
    F = "Fine"
    WF = "Wide Fine"
    MF = "Multi-Look Fine"
    WMF = "Wide Multi-Look Fine"
    XF = "Extra-Fine"
    U = "Ultra-Fine"
    WU = "Wide Ultra-Fine"
    EH = "Extended High"
    EL = "Extended Low"
    SQ = "Standard Quad-Pol"
    WSQ = "Wide Standard Quad-Pol"
    FQ = "Fine Quad-Pol"
    WFQ = "Wide Fine Quad-Pol"

    # ScanSAR Modes
    SCN = "ScanSAR Narrow"
    SCW = "ScanSAR Wide"
    OSVN = "Ocean Surveillance"
    DVWF = "Ship Detection"

    # Spotlight Mode
    SLA = "Spotlight"


@unique
class Rs2Polarization(ListEnum):
    """
    RADARSAT-2 polarization mode. Take a look here:
    https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs
    """
    HH = "HH"
    VV = "VV"
    VH = "VH"
    HV = "HV"


class Rs2Product(SarProduct):
    """ Class for RADARSAT-2 Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.raw_band_regex = "*imagery_{}.tif"
        self.band_folder = self.path
        self.snap_path = self.path
        self.pol_channels = self.get_raw_bands()

        # Zipped and SNAP can process its archive
        self.needs_extraction = False

    def get_wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        # Open extent KML file
        try:
            if self.is_archived:
                # Open the zip file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    # Get the correct band path
                    filenames = [f.filename for f in zip_ds.filelist]
                    regex = re.compile(f".*products.kml")
                    extent_file = zip_ds.open(list(filter(regex.match, filenames))[0])
            else:
                extent_file = glob.glob(os.path.join(self.path, "products.kml"))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Extent file (products.kml) not found in {self.path}") from ex

        vectors.set_kml_driver()
        product_kml = gpd.read_file(extent_file)
        extent_wgs84 = product_kml[product_kml.Name == "Polygon Outline"].envelope.to_crs(WGS84)

        return extent_wgs84

    def get_product_type(self) -> None:
        """ Get products type """
        self.get_sar_product_type(prod_type_pos=-1,
                                  gdrg_types=Rs2ProductType.SGF,
                                  cplx_types=Rs2ProductType.SLC)
        if self.product_type != Rs2ProductType.SGF:
            LOGGER.warning("Other products type than SGF has not been tested for %s data. "
                           "Use it at your own risks !", RS2_NAME)

    def get_sensor_mode(self) -> None:
        """
        Get products type from RADARSAT-2 products name (could check the metadata too)
        """
        # Get MTD XML file
        if self.is_archived:
            # Open the zip file
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                # Get the correct band path
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*products.xml")
                xml_zip = zip_ds.read(list(filter(regex.match, filenames))[0])
                root = etree.fromstring(xml_zip)
        else:
            # Open metadata file
            try:
                mtd_file = glob.glob(os.path.join(self.path, "products.xml"))[0]

                # pylint: disable=I1101:
                # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                xml_tree = etree.parse(mtd_file)
                root = xml_tree.getroot()
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file (products.xml) not found in {self.path}") from ex

        idx = root.tag.rindex("}")
        namespace = root.tag[:idx + 1]

        # Get sensor mode
        sensor_mode_xml = None
        for element in root:
            if element.tag == namespace + 'sourceAttributes':
                radar_param = element.find(namespace + 'radarParameters')

                # WARNING: this word may differ from the Enum !!! (no doc available)
                # Get the closest match
                sensor_mode_xml = radar_param.findtext(namespace + 'acquisitionType')
                break

        if sensor_mode_xml:
            sensor_mode = difflib.get_close_matches(sensor_mode_xml, Rs2SensorMode.list_values())[0]
            try:
                self.sensor_mode = Rs2SensorMode.from_value(sensor_mode)
            except ValueError as ex:
                raise InvalidTypeError(f"Invalid sensor mode for {self.name}") from ex
        else:
            raise InvalidTypeError(f"Invalid sensor mode for {self.name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        split_name = self.get_split_name()

        date = f"{split_name[5]}T{split_name[6]}"

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """

        return f"{self.get_datetime()}_RS2_{self.sensor_mode.name}_{self.product_type.value}"
