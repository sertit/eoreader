""" Product, superclass of all eoreader satellites eoreader """
# pylint: disable=W0107
from __future__ import annotations
import logging
import os
from enum import Enum, unique
from abc import abstractmethod
from typing import Union, Callable
import datetime
import numpy as np
import geopandas as gpd
import rasterio
from rasterio import crs
from rasterio import warp
from rasterio.enums import Resampling
from sertit import files, strings
from sertit import rasters

from eoreader import index
from eoreader.utils import MAX_CORES
from eoreader import utils
from eoreader.reader import Reader, Platform
from eoreader.bands import OpticalBandNames as obn, SarBandNames as sbn, BandNames
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

MERIT_DEM = os.path.join(utils.get_db_dir(), 'GLOBAL', "MERIT_Hydrologically_Adjusted_Elevations", "MERIT_DEM.vrt")
EUDEM_PATH = os.path.join(utils.get_db_dir(), 'GLOBAL', "EUDEM_v2", "eudem_wgs84.tif")

PRODUCT_FACTORY = Reader()


@unique
class SensorType(Enum):
    """
    Sensor type of the products, optical or radar
    """
    Optical = "optical"
    SAR = "radar"


class Product:
    """ Super class of eoreader Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        # The products name is its filename without any extension
        self.name = files.get_filename(product_path)

        # The archive path ios the products path if not given
        self.archive_path = archive_path if archive_path else product_path
        self.path = product_path

        # A products is considered as archived if its products path is a directory
        self.is_archived = os.path.isfile(self.path)

        # Does this products needs to be extracted to be processed ? (by default, True)
        self.needs_extraction = True

        # The output will be given later
        self.output = None

        # Get the products date and datetime
        self.date = self.get_date(as_date=True)
        self.datetime = self.get_datetime(as_datetime=True)

        # Used to distinguish eoreader that can be piled (for S2 and L8)
        self.tile_name = None

        # SAR or optical
        self.sensor_type = None

        # Others
        self.product_type = None
        self.band_names = None
        self.is_reference = False

        # A list because of multiple ref in case of non-stackable eoreader (S3, S1...)
        self.corresponding_ref = []
        self.nodata = 0
        self.sat_id = PRODUCT_FACTORY.get_platform_name(self.path)
        self.platform = getattr(Platform, self.sat_id)

    def get_footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return rasters.get_footprint(self.get_default_band_path())

    @abstractmethod
    def get_utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_utm_proj(self) -> crs.CRS:
        """
        Get UTM projection

        Returns:
            crs.CRS: CRS object
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_product_type(self) -> None:
        """
        Get products type
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime.datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_date(self, as_date: bool = False) -> Union[str, datetime.date]:
        """
        Get the products's acquisition date.

        Args:
            as_date (bool): Return the date as a datetime.date. If false, returns a string.

        Returns:
            str: Its acquisition date
        """
        date = self.get_datetime().split('T')[0]

        if as_date:
            date = strings.str_to_date(date, date_format="%Y%m%d")

        return date

    def get_existing_bands(self) -> list:
        """
        Return the existing band paths.

        Returns:
            list: List of existing bands in the products
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_existing_band_paths(self) -> dict:
        """
        Return the existing band paths.

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError("This method should be implemented by a child class")

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
    def read_band(self, dataset, x_res: float = None, y_res: float = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset

        Args:
            dataset (Dataset): Band dataset
            x_res (float): Resolution for X axis
            y_res (float): Resolution for Y axis
        Returns:
            np.ma.masked_array, dict: Radar band, saved as float 32 and its metadata

        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def load_bands(self, band_list: [list, BandNames], resolution: float = None) -> (dict, dict):
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            band_list (list, BandNames): List of the wanted bands
            resolution (int): Band resolution in meters
        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def load(self,
             index_list: [list, Callable] = None,
             band_list: [list, BandNames] = None,
             resolution: float = 20) -> (dict, dict):
        """
        Open the bands and compute the wanted index.
        You can add some bands in the dict.

        Args:
            index_list (list, index): Index list
            band_list (list, BandNames): Band list
            resolution (float): Resolution of the band, in meters

        Returns:
            dict, dict: Index and band dict, metadata
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_condensed_name(self) -> str:
        """
        Get products condensed name.

        Returns:
            str: Condensed name
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def has_band(self, band: Union[obn, sbn]) -> bool:
        """
        Does this products has the specified band ?

        Args:
            band (Union[obn, sbn]): Optical or SAR band

        Returns:
            bool: True if the products has the specified band
        """
        return band in self.get_existing_bands()

    def has_index(self, idx: Callable) -> bool:
        """
        Cen the specified index be computed from this products ?

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

    def get_split_name(self) -> list:
        """
        Get split name (erasing empty strings in it by precaution, especially for S1 data)

        Returns:
            list: Split products name
        """
        return [x for x in self.name.split('_') if x]

    @abstractmethod
    def get_default_band_path(self) -> str:
        """
        Get default band path (among the existing ones)

        Returns:
            str: Default band path
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_default_band(self) -> BandNames:
        """
        Get default band

        Returns:
            str: Default band
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def warp_dem(self,
                 dem_path: str = "",
                 resolution: Union[float, tuple] = 20.,
                 resampling: Resampling = Resampling.bilinear) -> str:
        """
        Get this products DEM, warped to this products footprint and CRS.

        If no DEM is giving (or non existing or non intersecting the products):

        - Using EUDEM over Europe
        - Using MERIT DEM everwhere else

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters
            resampling (Resampling): Resampling method

        Returns:
            str: DEM path (as a VRT)

        """
        warped_dem_path = os.path.join(self.output, f"{self.get_condensed_name()}_DEM.tif")
        if os.path.isfile(warped_dem_path):
            LOGGER.info("Already existing DEM for %s. Skipping process.", self.name)
        else:
            LOGGER.info("Warping DEM for %s", self.name)

            # Get products extent
            prod_extent_df = self.get_utm_extent()

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
                        LOGGER.warning("Input DEM file does nor intersect %s. Using default ones (EUDEM or MERIT)",
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
              band_combination: list,
              idx_combination: list,
              resolution: float,
              stack_path: str,
              save_as_int: bool = False) -> None:
        """
        Stack bands and index of a products.
        # TODO: merge band and idx to keep the correct stacking order asked by the user

        Args:
            band_combination (list): Bands combination
            idx_combination (list): Index combination
            resolution (float): Stack resolution
            stack_path (str): Stack path
            save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000)
        """

        # Get band combination
        if self.sensor_type == SensorType.Optical:
            band_combi = obn.from_list(band_combination)
        else:
            band_combi = sbn.from_list(band_combination)
        idx_bands = band_combi + idx_combination

        # Create the analysis stack
        bands, meta = self.load(idx_combination, band_combi, resolution)
        stack_list = [bands[band] for band in idx_bands]
        stack = np.ma.vstack(stack_list)

        # Force nodata
        stack[stack.mask] = meta["nodata"]

        # Save as integer
        if save_as_int:
            stack = (stack * 10000).astype(np.uint16)

        # Here do not use utils.write()
        meta.update({"count": len(stack_list),
                     "dtype": stack.dtype})
        with rasterio.open(stack_path, "w", **meta) as out_dst:
            for i, band in enumerate(idx_bands):
                # Band name is either a value or a function
                band_name = band.value if isinstance(band, Enum) else band.__name__
                out_dst.set_band_description(i + 1, band_name)
            out_dst.write(stack)
