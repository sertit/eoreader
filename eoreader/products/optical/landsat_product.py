""" Landsat products """

import logging
import os
import tempfile
from datetime import datetime
from abc import abstractmethod
from enum import unique
from typing import Union

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
from sertit import files
from sertit import rasters
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidProductError
from eoreader.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class LandsatProductType(ListEnum):
    """ Landsat products types """
    L1_OLCI = "OLCI"
    L1_ETM = "ETM"
    L1_TM = "TM"
    L1_MSS = "MSS"


class LandsatProduct(OpticalProduct):
    """ Class of Landsat Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.tile_name = self.retrieve_tile_names()

    @property
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

        Overload of the generic function because for landsat eoreader,
        the no data seems to be different in QA than in regular bands.
        We keep the QA value.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # Load default band
        # We need to use that to get the correct nodata stored in the QA file
        default_band = self.get_default_band()
        band, meta = self.load_bands(default_band)

        # Create tmp dir and save here the default band
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_band_path = os.path.join(tmp_dir.name, f"{self.condensed_name()}_DEF.tif")
        rasters.write(band[default_band], tmp_band_path, meta)

        # Vectorize the default band and clean the tmp dir
        footprint = rasters.get_footprint(tmp_band_path)
        tmp_dir.cleanup()

        # Get the footprint max (discard small holes)
        return footprint

    def retrieve_tile_names(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """
        return self.split_name[2]

    @abstractmethod
    def get_product_type(self) -> None:
        """ Get products type """
        raise NotImplementedError("This method should be implemented by a child class")

    def datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        try:
            mtd = self.read_mtd()
            date = mtd["DATE_ACQUIRED"].value  # 1982-09-06
            # "16:47:09.5990000Z": needs max 6 digits for ms
            hours = mtd["SCENE_CENTER_TIME"].value.replace("\"", "")[:-3]

            date = f"{datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')}" \
                   f"T{datetime.strptime(hours, '%H:%M:%S.%f').strftime('%H%M%S')}"
        except FileNotFoundError:
            date = datetime.strptime(self.split_name[3], "%Y%m%d").strftime(DATETIME_FMT)

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            assert band in obn
            band_nb = self.band_names[band]
            if band_nb is None:
                raise InvalidProductError(f"Non existing band ({band.name}) "
                                          f"for Landsat-{self.product_type.name} products")
            try:
                band_paths[band] = files.get_file_in_dir(self.path, f"_B{band_nb}.TIF")
            except FileNotFoundError as ex:
                raise InvalidProductError(f"Non existing {band} ({band_nb}) band for {self.path}") from ex

        return band_paths

    def read_mtd(self) -> pd.DataFrame:
        """
        Read Landsat metadata

        Returns:
            pd.DataFrame: Metadata as a Pandas DataFrame
        """
        mtd_path = os.path.join(self.path, f"{self.name}_MTL.txt")
        if not os.path.isfile(mtd_path):
            raise FileNotFoundError(f"Unable to find the metadata file associated with {self.path}")

        # Parse
        mtd_data = pd.read_table(mtd_path,
                                 sep="=",
                                 names=["NAME", "value"],
                                 skipinitialspace=True,
                                 parse_dates=True,
                                 infer_datetime_format=True)

        # Workaround an unexpected behaviour in pandas !
        if any(mtd_data.NAME == "="):
            mtd_data = pd.read_table(mtd_path,
                                     sep="=",
                                     names=["NAME", "=", "value"],
                                     usecols=[0, 2],
                                     skipinitialspace=True,
                                     parse_dates=True,
                                     infer_datetime_format=True)

        # Remove useless rows
        mtd_data = mtd_data[~mtd_data["NAME"].isin(["GROUP", "END_GROUP", "END"])]

        # Set index
        mtd_data = mtd_data.set_index("NAME").T

        return mtd_data

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

        # Get band name: the last number before the .TIF:
        # ie: 'LC08_L1TP_200030_20191218_20191226_01_T1_B1.TIF'
        band_name = dataset.name[-5:-4]
        if "_BQA" in dataset.name:
            band, dst_meta = rasters.read(dataset,
                                          [x_res, y_res],
                                          Resampling.nearest,  # NEAREST TO KEEP THE FLAGS
                                          masked=False)  # No need to get masked_array
        else:
            # Read band (call superclass generic method)
            band, dst_meta = rasters.read(dataset, [x_res, y_res], Resampling.bilinear)

            # Open mtd
            mtd_data = self.read_mtd()

            # Get band nb and corresponding coeff
            c_mul_str = 'REFLECTANCE_MULT_BAND_' + band_name
            c_add_str = 'REFLECTANCE_ADD_BAND_' + band_name

            # Get coeffs to convert DN to reflectance
            c_mul = mtd_data[c_mul_str].value
            c_add = mtd_data[c_add_str].value

            # Manage NULL values
            try:
                c_mul = float(c_mul)
            except ValueError:
                c_mul = 1
            try:
                c_add = float(c_add)
            except ValueError:
                c_add = 0

            # Compute the correct radiometry of the band and set no data to 0
            band = c_mul * band.astype(np.float32) + c_add

            # Update MTD
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
        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            res_x (float): Resolution for X axis
            res_y (float): Resolution for Y axis

        Returns:
            np.ma.masked_array, dict: Cleaned band array and its metadata
        """
        # Get QA file path
        landsat_qa_path = files.get_file_in_dir(self.path, "*BQA.TIF", exact_name=True)

        # Open QA band
        with rasterio.open(landsat_qa_path) as dataset:
            qa_arr, meta = self.read_band(dataset, res_x, res_y)

            # Get clouds and nodata
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band
            nodata_id = 0  # Fill value
            dropped_id = 1  # Dropped pixel or terrain occlusion
            # Set nodata to every saturated pixel, even if only 1-2 bands are touched by it
            # -> 01 or 10 or 11
            # -> bit 2 or bit 3
            sat_id_1 = 2
            sat_id_2 = 3
            nodata, dropped, sat_1, sat_2 = rasters.read_bit_array(qa_arr, [nodata_id, dropped_id, sat_id_1, sat_id_2])
            mask = nodata | dropped | sat_1 | sat_2

        return self.create_band_masked_array(band_arr, mask, meta)

    def load_bands(self, band_list: [list, BandNames], resolution: float = None) -> (dict, dict):
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

        return band_arrays, meta

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Zenith and Azimuth angles)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Retrieve angles
        mtd_data = self.read_mtd()
        azimuth_angle = float(mtd_data.SUN_AZIMUTH.value)
        zenith_angle = float(mtd_data.SUN_ELEVATION.value)

        return azimuth_angle, zenith_angle

    @abstractmethod
    def condensed_name(self) -> str:
        """
        Get products condensed name ({date}_Lx_{tile}_{product_type}).

        Returns:
            str: Condensed Landsat name
        """
        raise NotImplementedError("This method should be implemented by a child class")
