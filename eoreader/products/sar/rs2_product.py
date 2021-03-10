"""
RADARSAT-2 products.
More info [here](https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs).
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
import rasterio
import geopandas as gpd
from sertit.misc import ListEnum
from sertit import vectors
from sertit.vectors import WGS84

from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.products.sar.sar_product import SarProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)
RS2_NAME = "RADARSAT-2"

# Disable georef warnings here as the SAR products are not georeferenced
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


@unique
class Rs2ProductType(ListEnum):
    """
    RADARSAT-2 projection identifier.
    Take a look [here](https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs)
    """
    SLC = "SLC"
    """Single-look complex"""

    SGX = "SGX"
    """SAR georeferenced extra"""

    SGF = "SGF"
    """SAR georeferenced fine"""

    SCN = "SCN"
    """ScanSAR narrow beam"""

    SCW = "SCW"
    """ScanSAR wide beam"""

    SCF = "SCF"
    """ScanSAR fine"""

    SCS = "SCS"
    """ScanSAR sampled"""

    SSG = "SSG"
    """SAR systematic geocorrected"""

    SPG = "SPG"
    """SAR precision geocorrected"""


@unique
class Rs2SensorMode(ListEnum):
    """
    RADARSAT-2 sensor mode.
    Take a look [here](https://mdacorporation.com/docs/default-source/technical-documents/geospatial-services/52-1238_rs2_product_description.pdf)

    **WARNING**: The name in the metadata may vary !
    """
    # Single Beam Modes
    S = "Standard"
    """Standard Mode"""

    W = "Wide"
    """Spotlight Mode"""

    F = "Fine"
    """Wide Mode"""

    WF = "Wide Fine"
    """Wide Fine Mode"""

    MF = "Multi-Look Fine"
    """Multi-Look Fine Mode"""

    WMF = "Wide Multi-Look Fine"
    """Wide Multi-Look Fine Mode"""

    XF = "Extra-Fine"
    """Extra-Fine Mode"""

    U = "Ultra-Fine"
    """Ultra-Fine Mode"""

    WU = "Wide Ultra-Fine"
    """Wide Ultra-Fine Mode"""

    EH = "Extended High"
    """Extended High Mode"""

    EL = "Extended Low"
    """Extended Low Mode"""

    SQ = "Standard Quad-Pol"
    """Standard Quad-Pol Mode"""

    WSQ = "Wide Standard Quad-Pol"
    """Wide Standard Quad-Pol Mode"""

    FQ = "Fine Quad-Pol"
    """Fine Quad-Pol Mode"""

    WFQ = "Wide Fine Quad-Pol"
    """Spotlight Mode"""

    # ScanSAR Modes
    SCN = "ScanSAR Narrow"
    """Spotlight Mode"""

    SCW = "ScanSAR Wide"
    """Spotlight Mode"""

    OSVN = "Ocean Surveillance"
    """Ocean Surveillance Mode"""

    DVWF = "Ship Detection"
    """Ship Detection Mode"""

    # Spotlight Mode
    SLA = "Spotlight"
    """Spotlight Mode"""


@unique
class Rs2Polarization(ListEnum):
    """
    RADARSAT-2 polarization mode.
    Take a look [here](https://www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html#RADARSAT2__rs2_sfs)
    """
    HH = "HH"
    VV = "VV"
    VH = "VH"
    HV = "HV"


class Rs2Product(SarProduct):
    """
    Class for RADARSAT-2 Products

    You can use directly the .zip file
    """

    def __init__(self, product_path: str, archive_path: str = None, output_path=None) -> None:
        super().__init__(product_path, archive_path, output_path)
        self._raw_band_regex = "*imagery_{}.tif"
        self._band_folder = self.path
        self._snap_path = self.path
        self.pol_channels = self._get_raw_bands()
        self.condensed_name = self._get_condensed_name()

        # Zipped and SNAP can process its archive
        self.needs_extraction = False

    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip"
        >>> prod = Reader().open(path)
        >>> prod.wgs84_extent()
                                                    geometry
        1  POLYGON ((106.57999 -6.47363, 107.06926 -6.473...
        ```

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
                    regex = re.compile(f".*product.kml")
                    extent_file = zip_ds.open(list(filter(regex.match, filenames))[0])
            else:
                extent_file = glob.glob(os.path.join(self.path, "product.kml"))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Extent file (product.kml) not found in {self.path}") from ex

        vectors.set_kml_driver()
        product_kml = gpd.read_file(extent_file)
        extent_wgs84 = product_kml[product_kml.Name == "Polygon Outline"].envelope.to_crs(WGS84)

        return gpd.GeoDataFrame(geometry=extent_wgs84.geometry, crs=extent_wgs84.crs)

    def _set_product_type(self) -> None:
        """ Get products type """
        self._get_sar_product_type(prod_type_pos=-1,
                                   gdrg_types=Rs2ProductType.SGF,
                                   cplx_types=Rs2ProductType.SLC)
        if self.product_type != Rs2ProductType.SGF:
            LOGGER.warning("Other products type than SGF has not been tested for %s data. "
                           "Use it at your own risks !", RS2_NAME)

    def _set_sensor_mode(self) -> None:
        """
        Get products type from RADARSAT-2 products name (could check the metadata too)
        """
        # Get MTD XML file
        if self.is_archived:
            # Open the zip file
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                # Get the correct band path
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*product.xml")
                xml_zip = zip_ds.read(list(filter(regex.match, filenames))[0])
                root = etree.fromstring(xml_zip)
        else:
            # Open metadata file
            try:
                mtd_file = glob.glob(os.path.join(self.path, "product.xml"))[0]

                # pylint: disable=I1101:
                # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                xml_tree = etree.parse(mtd_file)
                root = xml_tree.getroot()
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file (product.xml) not found in {self.path}") from ex

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
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2016, 2, 28, 11, 24, 18)
        >>> prod.get_datetime(as_datetime=False)
        '20160228T112418'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        split_name = self.split_name

        date = f"{split_name[5]}T{split_name[6]}"

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """

        return f"{self.get_datetime()}_RS2_{self.sensor_mode.name}_{self.product_type.value}"
