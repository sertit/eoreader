""" Landsat products """
import glob
import logging
import os
import tempfile
from datetime import datetime
from abc import abstractmethod
from enum import unique
from typing import Union, Tuple

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from lxml import etree
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
class LandsatProductType(ListEnum):
    """ Landsat products types """
    L1_OLCI = "OLCI"
    """OLCI Product Type, for Landsat-8 platform"""

    L1_ETM = "ETM"
    """ETM Product Type, for Landsat-7 platform"""

    L1_TM = "TM"
    """TM Product Type, for Landsat-5 and 4 platforms"""

    L1_MSS = "MSS"
    """MSS Product Type, for Landsat-5,4,3,2,1 platforms"""


@unique
class LandsatCollection(ListEnum):
    """
    Landsat collection number.
    See [here](https://www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary) for more information
    """
    COL_1 = "01"
    """Collection 1"""

    COL_2 = "02"
    """Collection 2"""


class LandsatProduct(OpticalProduct):
    """ Class of Landsat Products """

    def __init__(self, product_path: str, archive_path: str = None, output_path=None) -> None:
        # Private
        self._collection = None
        self._quality_id = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path)

    def _set_collection(self):
        """ Set Landsat collection """
        return LandsatCollection.from_value(self.split_name[-2])

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()
        self._collection = self._set_collection()
        # self.needs_extraction = False for col2 ?

        self._quality_id = "_BQA" if self._collection == LandsatCollection.COL_1 else "_QA_RADSAT"

        # Post init done by the super class
        super()._post_init()

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
        >>> prod = Reader().open(path)
        >>> prod.footprint()
           index                                           geometry
        0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...
        ```

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        **We keep the QA value**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # Load default band
        # We need to use that to get the correct nodata stored in the QA file
        default_band = self.get_default_band()
        band, meta = self._load_bands(default_band)

        # Create tmp dir and save here the default band
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_band_path = os.path.join(tmp_dir, f"{self.condensed_name}_DEF.tif")
            rasters.write(band[default_band], tmp_band_path, meta)

            # Vectorize the default band and clean the tmp dir
            footprint = rasters.get_footprint(tmp_band_path)

        # Get the footprint max (discard small holes)
        return footprint

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
        >>> prod = Reader().open(path)
        >>> prod.get_tile_name()
        '023030'
        ```

        Returns:
            str: Tile name
        """
        return self.split_name[2]

    @abstractmethod
    def _set_product_type(self) -> None:
        """ Get products type """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2020, 5, 18, 16, 34, 7)
        >>> prod.get_datetime(as_datetime=False)
        '20200518T163407'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        try:
            mtd = self.read_mtd(force_pd=True)
            date = mtd["DATE_ACQUIRED"].value  # 1982-09-06
            # "16:47:09.5990000Z": needs max 6 digits for ms
            hours = mtd["SCENE_CENTER_TIME"].value.replace("\"", "")[:-3]

            date = f"{datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')}" \
                   f"T{datetime.strptime(hours, '%H:%M:%S.%f').strftime('%H%M%S')}"
        except (FileNotFoundError, KeyError):
            date = datetime.strptime(self.split_name[3], "%Y%m%d").strftime(DATETIME_FMT)

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_band_paths([GREEN, RED])
        {
            <OpticalBandNames.GREEN: 'GREEN'>:
                'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',
            <OpticalBandNames.RED: 'RED'>:
                'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF'
        }

        ```

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

    def read_mtd(self, force_pd=False) -> Union[pd.DataFrame, Tuple[etree._Element, str]]:
        """
        Read Landsat metadata as:

         - a `pandas.DataFrame` whatever its collection is (by default for collection 1)
         - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
        >>> prod = Reader().open(path)

        >>> # COLLECTION 1 : Open metadata as panda DataFrame
        >>> prod.read_mtd()
        NAME                                           ORIGIN  ...    RESAMPLING_OPTION
        value  "Image courtesy of the U.S. Geological Survey"  ...  "CUBIC_CONVOLUTION"
        [1 rows x 197 columns]

        >>> # COLLECTION 2 : Open metadata as XML
        >>> path = r"LC08_L1TP_200030_20201220_20210310_02_T1"  # Collection 2
        >>> prod = Reader().open(path)
        >>> prod.read_mtd()
        (<Element LANDSAT_METADATA_FILE at 0x19229016048>, '')

        >>> # COLLECTION 2 : Force to pandas.DataFrame
        >>> prod.read_mtd(force_pd=True)
        NAME                                           ORIGIN  ...    RESAMPLING_OPTION
        value  "Image courtesy of the U.S. Geological Survey"  ...  "CUBIC_CONVOLUTION"
        [1 rows x 263 columns]
        ```
        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace
        Returns:
            pd.DataFrame: Metadata as a Pandas DataFrame
        """
        # WARNING: always use force_pd in this class !
        as_pd = (self._collection == LandsatCollection.COL_1) or force_pd

        if as_pd:
            # FOR COLLECTION 1 AND 2
            mtd_path = os.path.join(self.path, f"{self.name}_MTL.txt")
            if not os.path.isfile(mtd_path):
                raise FileNotFoundError(f"Unable to find the metadata file associated with {self.path}")

            # Parse
            mtd_data = pd.read_table(mtd_path,
                                     sep="\s=\s",
                                     names=["NAME", "value"],
                                     skipinitialspace=True,
                                     engine="python")

            # Workaround an unexpected behaviour in pandas !
            if any(mtd_data.NAME == "="):
                mtd_data = pd.read_table(mtd_path,
                                         sep="=",
                                         names=["NAME", "=", "value"],
                                         usecols=[0, 2],
                                         skipinitialspace=True)

            # Remove useless rows
            mtd_data = mtd_data[~mtd_data["NAME"].isin(["GROUP", "END_GROUP", "END"])]

            # Set index
            mtd_data = mtd_data.set_index("NAME").T
        else:
            # ONLY FOR COLLECTION 2
            try:
                mtd_file = glob.glob(os.path.join(self.path, f"{self.name}_MTL.xml"))[0]

                # pylint: disable=I1101:
                # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                xml_tree = etree.parse(mtd_file)
                root = xml_tree.getroot()
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file ({self.name}.xml) not found in {self.path}") from ex

            # Get namespace
            namespace = ""  # No namespace here

            mtd_data = (root, namespace)

        return mtd_data

    def _read_band(self,
                   dataset,
                   resolution: Union[tuple, list, float] = None,
                   size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset.

        **WARNING**: Invalid pixels are not managed here, please consider using `load` or use it at your own risk!

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> with rasterio.open(prod.get_default_band_path()) as dst:
        >>>     band, meta = prod.read_band(dst, x_res=20, y_res=20)  # You can create not square pixels here
        >>> band
        masked_array(
          data=[[[-0.1, ..., -0.1]]],
          mask=False,
          fill_value=1e+20,
          dtype=float32)
        >>> meta
        {
            'driver': 'GTiff',
            'dtype': <class 'numpy.float32'>,
            'nodata': None,
            'width': 11746,
            'height': 11912,
            'count': 1,
            'crs': CRS.from_epsg(32616),
            'transform': Affine(20.00085135365231, 0.0, 314985.0, 0.0, -19.999160510409673, 4900215.0)
        }
        ```

        Args:
            dataset (Dataset): Band dataset
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            np.ma.masked_array, dict: Radiometrically coherent band, saved as float 32 and its metadata

        """

        # Get band name: the last number before the .TIF:
        # ie: 'LC08_L1TP_200030_20191218_20191226_01_T1_B1.TIF'
        band_name = dataset.name[-5:-4]
        if self._quality_id in dataset.name:
            band, dst_meta = rasters.read(dataset,
                                          resolution=resolution,
                                          size=size,
                                          resampling=Resampling.nearest,  # NEAREST TO KEEP THE FLAGS
                                          masked=False)  # No need to get masked_array
        else:
            # Read band (call superclass generic method)
            band, dst_meta = rasters.read(dataset,
                                          resolution=resolution,
                                          size=size,
                                          resampling=Resampling.bilinear)

            # Open mtd
            mtd_data = self.read_mtd(force_pd=True)

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
    def _manage_invalid_pixels(self,
                               band_arr: np.ma.masked_array,
                               band: obn,
                               meta: dict,
                               resolution: float = None,
                               size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ma.masked_array, dict: Cleaned band array and its metadata
        """
        # Get QA file path
        landsat_qa_path = files.get_file_in_dir(self.path, f"*{self._quality_id}.TIF", exact_name=True)

        # Open QA band
        with rasterio.open(landsat_qa_path) as dataset:
            qa_arr, meta = self._read_band(dataset,
                                           resolution=resolution,
                                           size=size)

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
                nodata, dropped, sat_1, sat_2 = rasters.read_bit_array(qa_arr,
                                                                       [nodata_id, dropped_id, sat_id_1, sat_id_2])
                mask = nodata | dropped | sat_1 | sat_2
            else:
                # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands
                band_nb = int(self.band_names[band])

                # Bit ids
                nodata_id = 0  # Fill value
                sat_id = band_nb - 1  # Saturated pixel
                if self.product_type != LandsatProductType.L1_OLCI:
                    other_id = 11  # Terrain occlusion
                else:
                    other_id = 9  # Dropped pixels

                nodata, sat, other = rasters.read_bit_array(qa_arr,
                                                            [nodata_id, sat_id, other_id])
                mask = nodata | sat | other

        return self._create_band_masked_array(band_arr, mask, meta)

    def _load_bands(self,
                    band_list: Union[list, BandNames],
                    resolution: float = None,
                    size: Union[list, tuple] = None) -> (dict, dict):
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            band_list (list, BandNames): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)
        """
        # Get band paths
        if not isinstance(band_list, list):
            band_list = [band_list]
        band_paths = self.get_band_paths(band_list)

        # Open bands and get array (resampled if needed)
        band_arrays, meta = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays, meta

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_mean_sun_angles()
        (140.80752656, 61.93065805)
        ```

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Retrieve angles
        mtd_data = self.read_mtd(force_pd=True)
        azimuth_angle = float(mtd_data.SUN_AZIMUTH.value)
        zenith_angle = float(mtd_data.SUN_ELEVATION.value)

        return azimuth_angle, zenith_angle

    @abstractmethod
    def _set_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_Lx_{tile}_{product_type}).

        Returns:
            str: Condensed Landsat name
        """
        raise NotImplementedError("This method should be implemented by a child class")
