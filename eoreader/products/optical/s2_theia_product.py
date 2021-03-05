""" Sentinel-2 Theia products """

import glob
import logging
import os
import datetime
from typing import Union

import rasterio
from lxml import etree
import numpy as np
from rasterio.enums import Resampling
from sertit import files
from sertit import rasters

from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.s2_product import S2ProductType
from eoreader.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)


class S2TheiaProduct(OpticalProduct):
    """
    Class of Sentinel-2 Theia Products
    https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/
    """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.tile_name = self.retrieve_tile_names()

    def retrieve_tile_names(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """

        return self.get_split_name()[3]

    def get_product_type(self) -> None:
        """ Get products type """
        self.product_type = S2ProductType.L2A
        self.band_names.map_bands({
            obn.BLUE: '2',
            obn.GREEN: '3',
            obn.RED: '4',
            obn.VRE_1: '5',
            obn.VRE_2: '6',
            obn.VRE_3: '7',
            obn.NIR: '8',
            obn.NNIR: '8A',
            obn.SWIR_1: '11',
            obn.SWIR_2: '12'
        })

        # TODO: bands 1 and 9 are in ATB_R1 (10m) and ATB_R2 (20m)
        # B1 to be divided by 20
        # B9 to be divided by 200

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime.datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        # 20200624-105726-971
        date = datetime.datetime.strptime(self.get_split_name()[1], "%Y%m%d-%H%M%S-%f")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            assert band in obn
            try:
                band_paths[band] = files.get_file_in_dir(self.path, f"FRE_B{self.band_names[band]}.tif")
            except FileNotFoundError as ex:
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

        # Compute the correct radiometry of the band
        band = band.astype(np.float32) / 10000.
        dst_meta["dtype"] = np.float32

        return band, dst_meta

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def manage_invalid_pixels(self,
                              band_arr: np.ma.masked_array,
                              band: obn,
                              meta: dict,
                              res_x: float = None,
                              res_y: float = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See there:
        https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf

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

        # https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/
        # For r_1, the band order is: B2, B3, B4, B8 and for r_2: B5, B6, B7, B8a, B11, B12
        r_1 = [obn.BLUE, obn.GREEN, obn.RED, obn.NIR]
        r_2 = [obn.VRE_1, obn.VRE_2, obn.VRE_3, obn.NNIR, obn.SWIR_1, obn.SWIR_2]
        if band in r_1:
            r_x = "R1"
            bit_id = r_1.index(band)
        elif band in r_2:
            r_x = "R2"
            bit_id = r_2.index(band)
        else:
            raise InvalidProductError(f"Invalid band: {band.value}")

        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        theia_nodata = -1.
        no_data_mask = np.where(band == theia_nodata, nodata_true, nodata_false).astype(np.uint8)

        # -- Manage NODATA pixels
        # Get EDG file path
        edg_path = files.get_file_in_dir(os.path.join(self.path, "MASKS"), f"*EDG_{r_x}.tif", exact_name=True)

        # Open EDG band
        with rasterio.open(edg_path) as edg_dst:
            # Nearest to keep the flags
            edg_arr, _ = rasters.read(edg_dst, [res_x, res_y], Resampling.nearest, masked=False)
            edg_mask = rasters.read_bit_array(edg_arr, bit_id)

        # -- Manage saturated pixels
        # Get SAT file path
        sat_path = files.get_file_in_dir(os.path.join(self.path, "MASKS"), f"*SAT_{r_x}.tif", exact_name=True)

        # Open SAT band
        with rasterio.open(sat_path) as sat_dst:
            # Nearest to keep the flags
            sat_arr, _ = rasters.read(sat_dst, [res_x, res_y], Resampling.nearest, masked=False)
            sat_mask = rasters.read_bit_array(sat_arr, bit_id)

        # Combine masks
        mask = no_data_mask | edg_mask | sat_mask

        # -- Merge masks
        return self.create_band_masked_array(band_arr, mask, meta)

    def load_bands(self, band_list: [list, BandNames], resolution: float = 20) -> (dict, dict):
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
        band_paths = self.get_band_paths(band_list)

        # Open bands and get array (resampled if needed)
        band_arrays, meta = self.open_bands(band_paths, resolution)
        meta["driver"] = "GTiff"

        return band_arrays, meta

    def get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile]_{product_type}).

        Returns:
            str: Condensed S2 name
        """
        return f"{self.get_datetime()}_S2THEIA_{self.tile_name}_{self.product_type.value}"

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
        try:
            mtd_xml = glob.glob(os.path.join(self.path, '*MTD_ALL.xml'))[0]
        except IndexError as ex:
            raise InvalidProductError(f"Metadata file not found in {self.path}") from ex

        # Open and parse XML
        # pylint: disable=I1101
        xml_tree = etree.parse(mtd_xml)
        root = xml_tree.getroot()

        # Open zenith and azimuth angle
        for element in root:
            if element.tag == 'Geometric_Informations':
                for node in element:
                    if node.tag == 'Mean_Value_List':
                        mean_sun_angles = node.find('Sun_Angles')
                        zenith_angle = float(mean_sun_angles.findtext('ZENITH_ANGLE'))
                        azimuth_angle = float(mean_sun_angles.findtext('AZIMUTH_ANGLE'))
                        break  # Only one Mean_Sun_Angle
                break  # Only one Geometric_Info

        if not zenith_angle or not azimuth_angle:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        return azimuth_angle, zenith_angle
