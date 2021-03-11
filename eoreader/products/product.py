""" Product, superclass of all EOReader satellites products """
# pylint: disable=W0107
from __future__ import annotations
import logging
import os
from enum import Enum, unique
from abc import abstractmethod
from typing import Union, Callable, Any
import datetime as dt
import numpy as np
import geopandas as gpd
import rasterio
from rasterio import crs, warp
from rasterio.enums import Resampling
from sertit import files, strings, rasters
from sertit.snap import MAX_CORES
from sertit.misc import ListEnum

from eoreader.bands import index
from eoreader import utils
from eoreader.reader import Reader, Platform
from eoreader.bands.bands import OpticalBandNames as obn, SarBandNames as sbn, BandNames
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM = os.path.join(utils.get_db_dir(), 'GLOBAL', "MERIT_Hydrologically_Adjusted_Elevations", "MERIT_DEM.vrt")
EUDEM_PATH = os.path.join(utils.get_db_dir(), 'GLOBAL', "EUDEM_v2", "eudem_wgs84.tif")

PRODUCT_FACTORY = Reader()


@unique
class SensorType(ListEnum):
    """
    Sensor type of the products, optical or SAR
    """
    OPTICAL = "Optical"
    """For optical data"""

    SAR = "SAR"
    """For SAR data"""


class Product:
    """ Super class of EOReader Products """

    def __init__(self, product_path: str, archive_path: str = None, output_path: str = None) -> None:
        self.name = files.get_filename(product_path)
        """Product name (its filename without any extension)."""

        self.split_name = self._get_split_name()
        """Split name, to retrieve every information from its filename (dates, tile, product type...)."""

        self.archive_path = archive_path if archive_path else product_path
        """Archive path, same as the product path if not specified. 
        Useful when you want to know where both the extracted and archived version of your product are stored."""

        self.path = product_path
        """Usable path to the product, either extracted or archived path, according to the satellite."""

        self.is_archived = os.path.isfile(self.path)
        """ Is the archived product is processed 
        (a products is considered as archived if its products path is a directory)."""

        self.needs_extraction = True
        """Does this products needs to be extracted to be processed ? (`True` by default)."""

        # The output will be given later
        self._output = output_path
        if output_path:
            os.makedirs(output_path, exist_ok=True)
        """Output directory of the product, to write orthorectified data for example."""

        # Get the products date and datetime
        self.date = self.get_date(as_date=True)
        """Acquisition date."""
        self.datetime = self.get_datetime(as_datetime=True)
        """Acquisition datetime."""

        self.tile_name = None
        """Tile if possible (for data that can be piled, for example S2 and Landsats)."""

        self.sensor_type = None
        """Sensor type, SAR or optical."""

        self.product_type = None
        """Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."""

        self.band_names = None
        """Band mapping between band wrapping names such as `GREEN` and band real number such as `03` for Sentinel-2."""

        self.is_reference = False
        """If the product is a reference, used for algorithms that need pre and post data, such as fire detection."""

        self.corresponding_ref = []
        """The corresponding reference products to the current one
         (if the product is not a reference but has a reference data corresponding to it).
         A list because of multiple ref in case of non-stackable products (S3, S1...)"""

        self.nodata = 0
        """ Product nodata, set to 0 by default. Please do not touch this or all index will fail. """

        self.sat_id = PRODUCT_FACTORY.get_platform_id(self.path)
        """Satellite ID, i.e. `S2` for Sentinel-2"""

        self.platform = getattr(Platform, self.sat_id)
        """Product platform, such as Sentinel-2"""

        # Post initialization
        self._post_init()

        # Set product type, needs to be done after the post-initialization
        self._set_product_type()

        # Set the resolution, needs to be done when knowing the product type
        self.resolution = self._set_resolution()
        """
        Default resolution in meters of the current product. 
        For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles.
        """

        self.condensed_name = self._set_condensed_name()
        """Condensed name, the filename with only useful data to keep the name unique 
        (ie. `20191215T110441_S2_30TXP_L2A_122756`). 
        Used to shorten names and paths."""

    @abstractmethod
    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.footprint()
           index                                           geometry
        0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...
        ```

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return rasters.get_footprint(self.get_default_band_path())

    @abstractmethod
    def utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.utm_extent()
                                                    geometry
        0  POLYGON ((309780.000 4390200.000, 309780.000 4...
        ```

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def utm_crs(self) -> crs.CRS:
        """
        Get UTM projection of the tile

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.utm_crs()
        CRS.from_epsg(32630)
        ```

        Returns:
            crs.CRS: CRS object
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _set_product_type(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _set_condensed_name(self) -> str:
        """
        Set product condensed name.

        Returns:
            str: Condensed name
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _get_split_name(self) -> list:
        """
        Get split name (erasing empty strings in it by precaution, especially for S1 and S3 data)

        Returns:
            list: Split products name
        """
        return [x for x in self.name.split('_') if x]

    @abstractmethod
    def get_datetime(self, as_datetime: bool = False) -> Union[str, dt.datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2020, 8, 24, 11, 6, 31)
        >>> prod.get_datetime(as_datetime=False)
        '20200824T110631'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_date(self, as_date: bool = False) -> Union[str, dt.date]:
        """
        Get the product's acquisition date.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_date(as_date=True)
        datetime.datetime(2020, 8, 24, 0, 0)
        >>> prod.get_date(as_date=False)
        '20200824'
        ```

        Args:
            as_date (bool): Return the date as a datetime.date. If false, returns a string.

        Returns:
            str: Its acquisition date
        """
        date = self.get_datetime().split('T')[0]

        if as_date:
            date = strings.str_to_date(date, date_format="%Y%m%d")

        return date

    @abstractmethod
    def get_default_band_path(self) -> str:
        """
        Get default band path (among the existing ones).

        Usually `GREEN` band for optical data and the first existing one between `VV` and `HH` for SAR data.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_default_band_path()
        'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'
        ```
        Returns:
            str: Default band path
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_default_band(self) -> BandNames:
        """
        Get default band:
        Usually `GREEN` band for optical data and the first existing one between `VV` and `HH` for SAR data.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_default_band()
        <OpticalBandNames.GREEN: 'GREEN'>
        ```

        Returns:
            str: Default band
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_existing_bands(self) -> list:
        """
        Return the existing bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_existing_bands()
        [<OpticalBandNames.CA: 'COASTAL_AEROSOL'>,
        <OpticalBandNames.BLUE: 'BLUE'>,
        <OpticalBandNames.GREEN: 'GREEN'>,
        <OpticalBandNames.RED: 'RED'>,
        <OpticalBandNames.VRE_1: 'VEGETATION_RED_EDGE_1'>,
        <OpticalBandNames.VRE_2: 'VEGETATION_RED_EDGE_2'>,
        <OpticalBandNames.VRE_3: 'VEGETATION_RED_EDGE_3'>,
        <OpticalBandNames.NIR: 'NIR'>,
        <OpticalBandNames.NNIR: 'NARROW_NIR'>,
        <OpticalBandNames.WV: 'WATER_VAPOUR'>,
        <OpticalBandNames.CIRRUS: 'CIRRUS'>,
        <OpticalBandNames.SWIR_1: 'SWIR_1'>,
        <OpticalBandNames.SWIR_2: 'SWIR_2'>]
        ```

        Returns:
            list: List of existing bands in the products
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_existing_band_paths(self) -> dict:
        """
        Return the existing band paths.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_existing_band_paths()
        {
            <OpticalBandNames.CA: 'COASTAL_AEROSOL'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',
            ...,
            <OpticalBandNames.SWIR_2: 'SWIR_2'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2'
        }
        ```

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError("This method should be implemented by a child class")

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
            <OpticalBandNames.GREEN: 'GREEN'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',
            <OpticalBandNames.RED: 'RED'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2'
        }
        ```

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def read_mtd(self) -> Any:
        """
        Read metadata and outputs the metadata XML root and its namespace most of the time,
        except from L8-collection 1 data which outputs a pandas DataFrame

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.read_mtd()
        (<Element product at 0x1832895d788>, '')
        ```

        Returns:
            Any: Metadata XML root and its namespace or pd.DataFrame
        """
        raise NotImplementedError("This method should be implemented by a child class")

    # pylint: disable=W0613
    def _read_band(self, dataset, x_res: float = None, y_res: float = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset.

        **WARNING**: For optical data, invalid pixels are not managed here,
        so please consider using `load` or use this function at your own risk!

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> with rasterio.open(prod.get_default_band_path()) as dst:
        >>>     band, meta = prod.read_band(dst, x_res=20, y_res=20)  # You can create not square pixels here
        >>> band
        masked_array(
          data=[[[0.0614, ..., 0.15799999]]],
          mask=False,
          fill_value=1e+20,
          dtype=float32)
        >>> meta
        {
            'driver': 'JP2OpenJPEG',
            'dtype': <class 'numpy.float32'>,
            'nodata': None,
            'width': 5490,
            'height': 5490,
            'count': 1,
            'crs': CRS.from_epsg(32630),
            'transform': Affine(20.0, 0.0, 199980.0,0.0, -20.0, 4500000.0)
        }
        ```

        Args:
            dataset (Dataset): Band dataset
            x_res (float): Resolution for X axis
            y_res (float): Resolution for Y axis
        Returns:
            np.ma.masked_array, dict: Radar band, saved as float 32 and its metadata

        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _load_bands(self, band_list: Union[list, BandNames], resolution: float = None) -> (dict, dict):
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            band_list (Union[list, BandNames]): List of the wanted bands
            resolution (int): Band resolution in meters
        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def load(self,
             band_and_idx_list: Union[list, BandNames, Callable],
             resolution: float = 20) -> (dict, dict):
        """
        Open the bands and compute the wanted index.
        You can add some bands in the dict.

        The bands will be purged of nodata and invalid pixels,
        the nodata will be set to 0 and the bands will be masked arrays in float.

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> bands, meta = prod.load([GREEN, NDVI], resolution=20)  # Always square pixels here
        >>> bands
        {<function NDVI at 0x00000227FBB929D8>: masked_array(
          data=[[[-0.02004455029964447, ..., 0.11663568764925003]]],
          mask=[[[False, ..., False]]],
          fill_value=0.0,
          dtype=float32),
          <OpticalBandNames.GREEN: 'GREEN'>: masked_array(
          data=[[[0.061400000005960464, ..., 0.15799999237060547]]],
          mask=[[[False, ..., False]]],
          fill_value=0.0,
          dtype=float32)}
        >>> meta
        {
            'driver': 'GTiff',
            'dtype': <class 'numpy.float32'>,
            'nodata': 0,
            'width': 5490,
            'height': 5490,
            'count': 1,
            'crs': CRS.from_epsg(32630),
            'transform': Affine(20.0, 0.0, 199980.0,0.0, -20.0, 4500000.0)
        }
        ```

        Args:
            band_and_idx_list (Union[list, BandNames, Callable]): Index list
            resolution (float): Resolution of the band, in meters

        Returns:
            dict, dict: Index and band dict, metadata
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def has_band(self, band: Union[BandNames, obn, sbn]) -> bool:
        """
        Does this products has the specified band ?

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.has_band(GREEN)
        True
        >>> prod.has_band(TIR_2)
        False
        ```

        Args:
            band (Union[obn, sbn]): Optical or SAR band

        Returns:
            bool: True if the products has the specified band
        """
        return band in self.get_existing_bands()

    def has_index(self, idx: Callable) -> bool:
        """
        Cen the specified index be computed from this products ?

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.has_index(NDVI)
        True
        ```

        Args:
            idx (Callable): Index

        Returns:
            bool: True if the specified index can be computed with this products's bands
        """
        index_bands = index.get_needed_bands(idx)
        return all(np.isin(index_bands, self.get_existing_bands()))

    def __gt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired after the other

        """
        return self.date > other.date

    def __ge__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired after or in the same time than the other

        """
        return self.date >= other.date

    def __eq__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired in the same time than the other

        """
        return self.date == other.date

    def __ne__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired not in the same time than the other

        """
        return self.date != other.date

    def __le__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired before or in the same time than the other

        """
        return self.date <= other.date

    def __lt__(self, other: Product) -> bool:
        """
        Overload greater than for eoreader -> compare the dates:
        The greater products is the one acquired the last.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this products has been acquired before the other

        """
        return self.date < other.date

    @property
    def output(self) -> str:
        """ Output directory of the product, to write orthorectified data for example. """
        if not self._output:
            self._output = os.path.join(os.path.dirname(self.path), self.condensed_name)
            os.makedirs(self._output, exist_ok=True)

        return self._output

    @output.setter
    def output(self, value: str):
        """ Output directory of the product, to write orthorectified data for example. """
        self._output = value
        if not os.path.isdir(self._output):
            os.makedirs(self._output, exist_ok=True)

    def warp_dem(self,
                 dem_path: str = "",
                 resolution: Union[float, tuple] = 20.,
                 resampling: Resampling = Resampling.bilinear) -> str:
        """
        Get this products DEM, warped to this products footprint and CRS.

        If no DEM is giving (or non existing or non intersecting the products):

        - Using EUDEM over Europe
        - Using MERIT DEM everwhere else

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.warp_dem(resolution=20)  # In meters
        '/path/to/20200824T110631_S2_T30TTK_L1C_150432_DEM.tif'
        ```

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters
            resampling (Resampling): Resampling method

        Returns:
            str: DEM path (as a VRT)

        """
        warped_dem_path = os.path.join(self.output, f"{self.condensed_name}_DEM.tif")
        if os.path.isfile(warped_dem_path):
            LOGGER.info("Already existing DEM for %s. Skipping process.", self.name)
        else:
            LOGGER.info("Warping DEM for %s", self.name)

            # Get products extent
            prod_extent_df = self.utm_extent()

            # The MERIT is the default DEM as it covers almost the entire Earth
            if not dem_path:
                dem_path = MERIT_DEM
            else:
                if not os.path.isfile(dem_path):
                    LOGGER.warning("Non existing DEM file: %s. Using default ones (EUDEM or MERIT)", dem_path)
                    dem_path = MERIT_DEM
                else:
                    dem_extent_df = rasters.get_extent(dem_path).to_crs(prod_extent_df.crs)
                    if not dem_extent_df.contains(prod_extent_df)[0]:
                        LOGGER.warning("Input DEM file does not intersect %s. Using default ones (EUDEM or MERIT)",
                                       self.name)
                        dem_path = MERIT_DEM

            # Use EUDEM if the products is contained in it
            if dem_path == MERIT_DEM and os.path.isfile(EUDEM_PATH):
                dem_extent_df = rasters.get_extent(EUDEM_PATH)
                if dem_extent_df.contains(prod_extent_df.to_crs(dem_extent_df.crs))[0]:
                    dem_path = EUDEM_PATH

            # Check existence (SRTM)
            if not os.path.isfile(dem_path):
                raise FileNotFoundError(f"DEM file does not exist here: {dem_path}")

            # Reproject DEM into products CRS
            with rasterio.open(self.get_default_band_path()) as prod_dst:
                LOGGER.debug("Using DEM: %s", dem_path)
                with rasterio.open(dem_path) as dem_ds:
                    # Get adjusted transform and shape (with new resolution)
                    res_x = resolution[0] if isinstance(resolution, (tuple, list)) else resolution
                    res_y = resolution[1] if isinstance(resolution, (tuple, list)) else resolution
                    dst_tr = prod_dst.transform
                    coeff_x = np.abs(res_x / dst_tr.a)
                    coeff_y = np.abs(res_y / dst_tr.e)
                    dst_tr *= dst_tr.scale(coeff_x, coeff_y)
                    out_w = int(np.round(prod_dst.width / coeff_x))
                    out_h = int(np.round(prod_dst.height / coeff_y))

                    # Get empty output
                    reprojected_array = np.zeros((prod_dst.count, out_h, out_w), dtype=np.float32)

                    # Write reprojected DEM: here do not use utils.write()
                    out_meta = prod_dst.meta.copy()
                    out_meta["dtype"] = reprojected_array.dtype
                    out_meta["transform"] = dst_tr
                    out_meta["driver"] = "GTiff"
                    out_meta["width"] = out_w
                    out_meta["height"] = out_h
                    with rasterio.open(warped_dem_path, "w", **out_meta) as out_dst:
                        out_dst.write(reprojected_array)

                        # Reproject
                        warp.reproject(
                            source=rasterio.band(dem_ds, range(1, dem_ds.count + 1)),
                            destination=rasterio.band(out_dst, range(1, out_dst.count + 1)),
                            resampling=resampling,
                            num_threads=MAX_CORES)

        return warped_dem_path

    # pylint: disable=R0913
    # Too many arguments (6/5)
    def stack(self,
              band_and_idx_combination: list,
              resolution: float,
              stack_path: str = None,
              save_as_int: bool = False) -> (np.ma.masked_array, dict):
        """
        Stack bands and index of a products.

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> stack, stk_meta = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  # In meters
        >>> stack
        masked_array(
          data=[[[-0.02004455029964447, ..., 0.15799999237060547]]],
          mask=[[[False, ..., False]]],
          fill_value=1e+20,
          dtype=float32)
        >>> stk_meta
        {
            'driver': 'GTiff',
            'dtype': <class 'numpy.float32'>,
            'nodata': 0,
            'width': 5490,
            'height': 5490,
            'count': 3,
            'crs': CRS.from_epsg(32630),
            'transform': Affine(20.0, 0.0, 199980.0,0.0, -20.0, 4500000.0)
        }
        ```

        Args:
            band_and_idx_combination (list): Bands and index combination
            resolution (float): Stack resolution
            stack_path (str): Stack path
            save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000)
        """
        # Create the analysis stack
        bands, meta = self.load(band_and_idx_combination, resolution)
        stack_list = [bands[bd_or_idx] for bd_or_idx in band_and_idx_combination]
        stack = np.ma.vstack(stack_list)

        # Force nodata
        stack[stack.mask] = meta["nodata"]

        # Save as integer
        if save_as_int:
            stack = (stack * 10000).astype(np.uint16)

        # Here do not use utils.write()
        meta.update({"count": len(stack_list),
                     "dtype": stack.dtype})

        if stack_path:
            with rasterio.open(stack_path, "w", **meta) as out_dst:
                for i, band in enumerate(band_and_idx_combination):
                    # Band name is either a value or a function
                    band_name = band.value if isinstance(band, Enum) else band.__name__
                    out_dst.set_band_description(i + 1, band_name)
                out_dst.write(stack)

        return stack, meta
