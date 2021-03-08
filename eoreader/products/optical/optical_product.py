""" Super class for optical eoreader """

import logging
from abc import abstractmethod
from typing import Callable
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.features
import rasterio.warp
import rasterio.crs
from sertit import rasters

from eoreader.exceptions import InvalidIndexError, InvalidBandError, InvalidTypeError
from eoreader.bands import OpticalBands, OpticalBandNames as obn, BandNames
from eoreader.bands import index
from eoreader.products.product import Product, SensorType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


class OpticalProduct(Product):
    """ Super class for optical eoreader """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.band_names = OpticalBands()
        self.get_product_type()
        self.sensor_type = SensorType.Optical

    def get_default_band(self) -> BandNames:
        """
        Get default band

        Returns:
            str: Default band
        """
        return obn.GREEN

    def get_default_band_path(self) -> str:
        """
        Get default band path (among the existing ones)

        Returns:
            str: Default band path
        """
        default_band = self.get_default_band()
        return self.get_band_paths([default_band])[default_band]

    @property
    def utm_crs(self) -> rasterio.crs.CRS:
        """
        Get UTM projection

        Returns:
            rasterio.crs.CRS: CRS object
        """
        band_path = self.get_default_band_path()
        with rasterio.open(band_path) as dst:
            utm = dst.crs

        return utm

    @property
    def utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # Get extent
        return rasters.get_extent(self.get_default_band_path())

    @abstractmethod
    def get_product_type(self) -> None:
        """ Get products type """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_existing_bands(self) -> list:
        """
        Return the existing band paths.

        Returns:
            list: List of existing bands in the products
        """
        return [name for name, nb in self.band_names.items() if nb]

    def get_existing_band_paths(self) -> dict:
        """
        Return the existing band paths.

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        existing_bands = self.get_existing_bands()
        return self.get_band_paths(band_list=existing_bands)

    @abstractmethod
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
        raise NotImplementedError("This method should be implemented by a child class")

    def open_bands(self, band_paths: dict, resolution: float = None) -> (dict, dict):
        """
        Open bands from their paths.

        Args:
            band_paths (dict): Band dict: {band_enum: band_path}
            resolution (float): Band resolution in meters

        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)

        """
        # Open bands and get array (resampled if needed)
        band_arrays = {}
        meta = None
        for band_name, band_path in band_paths.items():
            with rasterio.open(band_path) as band_ds:
                # Read band
                band_arrays[band_name], ds_meta = self.read_band(band_ds, resolution, resolution)
                band_arrays[band_name], ds_meta = self.manage_invalid_pixels(band_arrays[band_name], band_name, ds_meta,
                                                                             resolution, resolution)

                # Meta
                if not meta:
                    meta = ds_meta.copy()

        return band_arrays, meta

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    @abstractmethod
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
        raise NotImplementedError("This method should be implemented by a child class")

    def create_band_masked_array(self,
                                 band_arr: np.ma.masked_array,
                                 mask: np.ndarray,
                                 meta: dict) -> (np.ma.masked_array, dict):
        """
        Create the correct masked array with well positioned nodata and values properly set to nodata

        Args:
            band_arr (np.ma.masked_array): Band array
                (should already be a masked array as it comes from rasterio.read(..., masked=True)
            mask (np.ndarray): Mask array, should be the same size as band_arr (in 2D)
            meta (dict): Metadata of the band array

        Returns:
            (np.ma.masked_array, dict): Corrected band array and updated metadata
        """
        # Binary mask
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        if len(mask.shape) < len(band_arr.shape):
            mask = np.expand_dims(mask, axis=0)

        # Set ok pixels that have 0 value to epsilon
        eps = 0.0001  # min value to be set to 1 when saved as uint16 (*10000)
        # band_arr[band_arr.data == self.nodata] = eps  # Do not let not nodata pixels to 0
        # band_arr[mask == 1] = self.nodata  # Set no data pixels to the correct value
        # band_arr.mask = mask
        # band_arr.fill_value = self.nodata

        band_arr_mask = np.ma.masked_array(np.where(band_arr == self.nodata, eps, band_arr),
                                           mask=mask,
                                           fill_value=self.nodata,
                                           dtype=band_arr.dtype)
        meta["nodata"] = self.nodata

        return band_arr_mask, meta

    def load(self,
             index_list: [list, index] = None,
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
        # We should have at least one band or index
        assert index_list is not None or band_list is not None

        # Convert index_list into list if needed
        if index_list is None:
            index_list = []
        else:
            if isinstance(index_list, Callable):
                index_list = [index_list]
            elif isinstance(index_list, list):
                pass
            else:
                raise InvalidTypeError("index_list should be a list of index or an index")

        # Check if all index are valid
        for idx in index_list:
            if not self.has_index(idx):
                raise InvalidIndexError(f"{idx} cannot be computed from {self.condensed_name()}.")

        # Convert band_list into list if needed
        if band_list is None:
            band_list = []
        else:
            if isinstance(band_list, obn):
                band_list = [band_list]
            elif isinstance(band_list, list):
                pass
            else:
                raise InvalidTypeError("band_list should be a list of obn or a obn")

        # Check if all bands are valid
        for band in band_list:
            if not self.has_band(band):
                raise InvalidBandError(f"{band} cannot be retrieved from {self.condensed_name()}.")

        # Get all bands to be open
        index_bands = []
        for idx in index_list:
            index_bands += index.NEEDED_BANDS[idx]
        index_bands += band_list

        # Only keep unique bands (open them only one time !)
        index_bands = list(set(index_bands))

        # Load band arrays -> All needed bands are loaded, if not a FileNotFoundError in thrown here
        bands, meta = self.load_bands(index_bands, resolution=resolution)

        # Compute index (they conserve the nodata)
        idx_dict = {}
        for idx in index_list:
            idx_dict[idx] = idx(bands)

        # Add bands
        for band in band_list:
            idx_dict[band] = bands[band]

        return idx_dict, meta

    @abstractmethod
    def condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile]_{product_type}).

        Returns:
            str: Condensed S2 name
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Zenith and Azimuth angles)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        raise NotImplementedError("This method should be implemented by a child class")
