""" Sentinel-2 products """

import glob
import logging
import os
import re
import zipfile
from datetime import datetime
from enum import unique
from typing import Union

from lxml import etree
import numpy as np
import geopandas as gpd
from rasterio import features
from rasterio.enums import Resampling
from sertit import files
from sertit import rasters
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S2ProductType(ListEnum):
    """ Sentinel-2 products types (L1C or L2A) """
    L1C = "L1C"
    L2A = "L2A"


BAND_DIR_NAMES = {S2ProductType.L1C: 'IMG_DATA',
                  S2ProductType.L2A: {'01': ['R60m'],
                                      '02': ['R10m', 'R20m', 'R60m'],
                                      '03': ['R10m', 'R20m', 'R60m'],
                                      '04': ['R10m', 'R20m', 'R60m'],
                                      '05': ['R20m', 'R60m'],
                                      '06': ['R20m', 'R60m'],
                                      '07': ['R20m', 'R60m'],
                                      '08': ['R10m'],
                                      '8A': ['R20m', 'R60m'],
                                      '09': ['R60m'],
                                      '11': ['R20m', 'R60m'],
                                      '12': ['R20m', 'R60m']}}


class S2Product(OpticalProduct):
    """ Class of Sentinel-2 Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.tile_name = self.retrieve_tile_names()
        self.condensed_name = self.get_condensed_name()

        # Zipped
        self.needs_extraction = False

    def retrieve_tile_names(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """
        return self.split_name[-2]

    def get_product_type(self) -> None:
        """ Get products type """
        if "MSIL2A" in self.name:
            self.product_type = S2ProductType.L2A
            self.band_names.map_bands({
                obn.CA: '01',
                obn.BLUE: '02',
                obn.GREEN: '03',
                obn.RED: '04',
                obn.VRE_1: '05',
                obn.VRE_2: '06',
                obn.VRE_3: '07',
                obn.NIR: '08',
                obn.NNIR: '8A',
                obn.WV: '09',
                obn.SWIR_1: '11',
                obn.SWIR_2: '12'
            })
        elif "MSIL1C" in self.name:
            self.product_type = S2ProductType.L1C
            self.band_names.map_bands({
                obn.CA: '01',
                obn.BLUE: '02',
                obn.GREEN: '03',
                obn.RED: '04',
                obn.VRE_1: '05',
                obn.VRE_2: '06',
                obn.VRE_3: '07',
                obn.NIR: '08',
                obn.NNIR: '8A',
                obn.WV: '09',
                obn.CIRRUS: '10',
                obn.SWIR_1: '11',
                obn.SWIR_2: '12'
            })
        else:
            raise InvalidProductError(f"Invalid Sentinel-2 name: {self.name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """

        date = self.split_name[2]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_band_folder(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.

        Args:
            band_list (list): Wanted bands (listed as 01, 02...)
            resolution (float): Band resolution for Sentinel-2 products {R10m, R20m, R60m}.
                                The wanted bands will be chosen in this proper folder.

        Returns:
            dict: Dictionary containing the folder path for each queried band
        """
        # Open the band directory names
        s2_bands_folder = {}

        # Manage L2A
        band_dir = BAND_DIR_NAMES[self.product_type]
        for band in band_list:
            assert band in obn
            band_nb = self.band_names[band]
            if band_nb is None:
                raise InvalidProductError(f"Non existing band ({band.name}) for S2-{self.product_type.name} products")

            # If L2A products, we care about the resolution
            if self.product_type == S2ProductType.L2A:
                # If we got a true S2 resolution, open the corresponding band
                if resolution and f"R{resolution}m" in band_dir[band_nb]:
                    dir_name = f"R{resolution}m"

                # Else open the first one, it will be resampled when the ban will be read
                else:
                    dir_name = band_dir[band_nb][0]
            # If L1C, we do not
            else:
                dir_name = band_dir

            if self.is_archived:
                # Open the zip file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    # Get the band folder (use dirname is the first of the list is a band)
                    s2_bands_folder[band] = [os.path.dirname(f.filename) for f in zip_ds.filelist
                                             if dir_name in f.filename][0]
            else:
                # Search for the name of the folder into the S2 products
                for root, folders, _ in os.walk(os.path.abspath(self.path)):
                    for folder in folders:
                        if folder == dir_name:
                            s2_bands_folder[band] = os.path.join(root, folder)

        for band in band_list:
            if band not in s2_bands_folder:
                raise InvalidProductError(f"Band folder for band {band.value} not found in {self.path}")

        return s2_bands_folder

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_folders = self.get_band_folder(band_list, resolution)
        band_paths = {}
        for band in band_list:
            assert band in obn
            try:
                if self.is_archived:
                    # Open the zip file
                    with zipfile.ZipFile(self.path, "r") as zip_ds:
                        # Get all files from inside the band folder
                        folder_paths = [f.filename for f in zip_ds.filelist if band_folders[band] in f.filename]

                        # Get the correct band path
                        regex = re.compile(f".*_B{self.band_names[band]}.*.jp2")
                        band_path = list(filter(regex.match, folder_paths))[0]

                    # Create the zip band path (readable from rasterio)
                    band_paths[band] = f"zip+file://{self.path}!/{band_path}"
                else:
                    band_paths[band] = files.get_file_in_dir(band_folders[band],
                                                             "_B" + self.band_names[band],
                                                             extension="jp2")
            except (FileNotFoundError, IndexError) as ex:
                raise InvalidProductError(f"Non existing {band} ({self.band_names[band]}) band for {self.path}") from ex

        return band_paths

    def read_band(self, dataset, x_res: float = None, y_res: float = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset -> Manage if they need to be divided by 10k or not.

        Args:
            dataset (Dataset): Band dataset
            x_res (float): Resolution for X axis
            y_res (float): Resolution for Y axis
        Returns:
            np.ma.masked_array, dict: Radiometrically coherent band, saved as float 32 and its metadata

        """
        # Read band
        band, dst_meta = rasters.read(dataset, [x_res, y_res], Resampling.bilinear)

        # Get resolution
        coeff = 1 / 10000. if dataset.meta['dtype'] == 'uint16' else 1

        # Compute the correct radiometry of the band
        band = band.astype(np.float32) * coeff
        dst_meta["dtype"] = np.float32

        return band, dst_meta

    def open_mask(self, mask_str: str, band: Union[obn, str]) -> gpd.GeoDataFrame:
        """
        Open S2 mask (GML files stored in QI_DATA)

        Args:
            mask_str (str): Mask name, such as DEFECT, NODATA, SATURA...
            band (Union[obn, str]): Band number as an OpticalBandNames or str (for clouds: 00)

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        def open_mask(mask_path):
            # Read the GML file
            try:
                # Discard some weird error concerning a NULL pointer that outputs a ValueError (as we already except it)
                fiona_logger = logging.getLogger("fiona._env")
                fiona_logger.setLevel(logging.CRITICAL)

                # Read mask
                mask = gpd.read_file(mask_path)

                # Set fiona logger back to what it was
                fiona_logger.setLevel(logging.INFO)
            except ValueError:
                mask = gpd.GeoDataFrame(geometry=[], crs=self.utm_crs())

            return mask

        # Get QI_DATA path
        if isinstance(band, obn):
            band_name = self.band_names[band]
        else:
            band_name = band

        if self.is_archived:
            # Open the zip file
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                # Get the correct band path
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*GRANULE.*QI_DATA.*MSK_{mask_str}_B{band_name}.gml")
                with zip_ds.open(list(filter(regex.match, filenames))[0]) as mask_path:
                    mask = open_mask(mask_path)
        else:
            qi_data_path = os.path.join(self.path, 'GRANULE', '*', 'QI_DATA')

            # Get mask path
            mask_path = files.get_file_in_dir(qi_data_path,
                                              f"MSK_{mask_str}_B{band_name}.gml",
                                              exact_name=True)

            mask = open_mask(mask_path)

        return mask

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(self,
                               band_arr: np.ma.masked_array,
                               band: obn,
                               meta: dict,
                               res_x: float = None,
                               res_y: float = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See there: https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf

        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            res_x (float): Resolution for X axis
            res_y (float): Resolution for Y axis

        Returns:
            np.ma.masked_array, dict: Cleaned band array and its metadata
        """
        nodata_true = 1
        nodata_false = 0

        # Get detector footprint to deduce the outside nodata
        nodata_det = self.open_mask("DETFOO", band)  # Detector nodata, -> pixels that are outside of the detectors

        # Rasterize nodata
        mask = features.rasterize(nodata_det.geometry,
                                  out_shape=(meta["width"], meta["height"]),
                                  fill=nodata_true,  # Outside detector = nodata
                                  default_value=nodata_false,  # Inside detector = acceptable value
                                  transform=meta["transform"],
                                  dtype=np.uint8)

        #  Load masks and merge them into the nodata
        nodata_pix = self.open_mask("NODATA", band)  # Pixel nodata, not pixels that are outside of the detectors !!!
        if len(nodata_pix) > 0:
            # Discard pixels corrected during crosstalk
            nodata_pix = nodata_pix[nodata_pix.gml_id == "QT_NODATA_PIXELS"]
        nodata_pix.append(self.open_mask("DEFECT", band))
        nodata_pix.append(self.open_mask("SATURA", band))

        # Technical quality mask
        tecqua = self.open_mask("TECQUA", band)
        if len(tecqua) > 0:
            # Do not take into account ancillary data
            tecqua = tecqua[tecqua.gml_id.isin(["MSI_LOST", "MSI_DEG"])]
        nodata_pix.append(tecqua)

        if len(nodata_pix) > 0:
            # Rasterize mask
            mask_pix = features.rasterize(nodata_pix.geometry,
                                          out_shape=(meta["width"], meta["height"]),
                                          fill=nodata_false,  # OK pixels = OK value
                                          default_value=nodata_true,  # Discarded pixels = nodata
                                          transform=meta["transform"],
                                          dtype=np.uint8)

            mask[mask_pix] = nodata_true

        return self._create_band_masked_array(band_arr, mask, meta)

    def _load_bands(self, band_list: [list, BandNames], resolution: float = 20) -> (dict, dict):
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            band_list (list, BandNames): List of the wanted bands
            resolution (float): Band resolution in meters
        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)
        """
        # Get band paths
        if not isinstance(band_list, list):
            band_list = [band_list]
        band_paths = self.get_band_paths(band_list, resolution)

        # Open bands and get array (resampled if needed)
        band_arrays, meta = self._open_bands(band_paths, resolution)
        meta["driver"] = "GTiff"

        return band_arrays, meta

    def get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile}_{product_type}_{processed_hours}).

        Returns:
            str: Condensed S2 name
        """
        # Used to make the difference between 2 eoreader acquired on the same tile at the same date but cut differently
        proc_time = self.split_name[-1].split("T")[-1]
        return f"{self.datetime}_S2_{self.tile_name}_{self.product_type.value}_{proc_time}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Zenith and Azimuth angles)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Init angles
        zenith_angle = None
        azimuth_angle = None

        # Get MTD XML file
        if self.is_archived:
            # Open the zip file
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                # Get the correct band path
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*GRANULE.*.xml")
                mtd_xml = list(filter(regex.match, filenames))[0]
                root = etree.fromstring(zip_ds.read(mtd_xml))
        else:
            granule_dir = os.path.join(self.path, 'GRANULE')
            try:
                mtd_xml = glob.glob(os.path.join(granule_dir, '*', '*.xml'))[0]
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file not found in {self.path}") from ex

            # Open and parse XML
            # pylint: disable=I1101
            xml_tree = etree.parse(mtd_xml)
            root = xml_tree.getroot()

        idx = root.tag.rindex("}")
        namespace = root.tag[:idx + 1]

        # Open zenith and azimuth angle
        for element in root:
            if element.tag == namespace + 'Geometric_Info':
                for node in element:
                    if node.tag == 'Tile_Angles':
                        mean_sun_angles = node.find('Mean_Sun_Angle')
                        zenith_angle = float(mean_sun_angles.findtext('ZENITH_ANGLE'))
                        azimuth_angle = float(mean_sun_angles.findtext('AZIMUTH_ANGLE'))
                        break  # Only one Mean_Sun_Angle
                break  # Only one Geometric_Info

        if not zenith_angle or not azimuth_angle:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        return azimuth_angle, zenith_angle
