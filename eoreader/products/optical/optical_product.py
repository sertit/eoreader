""" Super class for optical products """

import logging
import os
from abc import abstractmethod
from typing import Callable, Union
import numpy as np
import geopandas as gpd
import rasterio
from rasterio import crs
from rasterio.enums import Resampling
from sertit import rasters, strings, misc
from sertit.snap import MAX_CORES

from eoreader.bands.alias import is_dem
from eoreader.exceptions import InvalidIndexError, InvalidBandError
from eoreader.bands.bands import OpticalBands, OpticalBandNames as obn, BandNames
from eoreader.bands import index, alias
from eoreader.products.product import Product, SensorType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


class OpticalProduct(Product):
    """ Super class for optical products """

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.band_names = OpticalBands()
        self._set_product_type()
        self.sensor_type = SensorType.OPTICAL

    def get_default_band(self) -> BandNames:
        """
        Get default band: `GREEN` for optical data as every optical satellite has a GREEN band.

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
        return obn.GREEN

    def get_default_band_path(self) -> str:
        """
        Get default band (`GREEN` for optical data) path.

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
        default_band = self.get_default_band()
        return self.get_band_paths([default_band])[default_band]

    def utm_crs(self) -> rasterio.crs.CRS:
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
            rasterio.crs.CRS: CRS object
        """
        band_path = self.get_default_band_path()
        with rasterio.open(band_path) as dst:
            utm = dst.crs

        return utm

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
        # Get extent
        return rasters.get_extent(self.get_default_band_path())

    def get_existing_bands(self) -> list:
        """
        Return the existing band paths.

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
        return [name for name, nb in self.band_names.items() if nb]

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
        existing_bands = self.get_existing_bands()
        return self.get_band_paths(band_list=existing_bands)

    def _open_bands(self,
                    band_paths: dict,
                    resolution: float = None,
                    size: Union[list, tuple] = None) -> (dict, dict):
        """
        Open bands from their paths.

        Args:
            band_paths (dict): Band dict: {band_enum: band_path}
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)

        """
        # Open bands and get array (resampled if needed)
        band_arrays = {}
        meta = {}
        for band_name, band_path in band_paths.items():
            with rasterio.open(band_path) as band_ds:
                # Read band
                band_arrays[band_name], ds_meta = self._read_band(band_ds, resolution=resolution, size=size)
                band_arrays[band_name], ds_meta = self._manage_invalid_pixels(band_arrays[band_name],
                                                                              band_name, ds_meta,
                                                                              resolution=resolution,
                                                                              size=size)

                # Meta
                if not meta:
                    meta = ds_meta.copy()

        return band_arrays, meta

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    @abstractmethod
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
        raise NotImplementedError("This method should be implemented by a child class")

    def _create_band_masked_array(self,
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
             band_and_idx_list: Union[list, BandNames, Callable],
             resolution: float = None,
             size: Union[list, tuple] = None) -> (dict, dict):
        """
        Open the bands and compute the wanted index.

        The bands will be purged of nodata and invalid pixels,
        the nodata will be set to 0 and the bands will be masked arrays in float.

        Bands that come out this function at the same time are collocated and therefore have the same shapes.
        This can be broken if you load data separately. Its is best to always load DEM data with some real bands.

        If neither resolution nor size is given, bands will be loaded at the product's default resolution.

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
            band_and_idx_list (list, index): Index list
            resolution (float): Resolution of the band, in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            dict, dict: Index and band dict, metadata
        """
        if not resolution and not size:
            resolution = self.resolution

        if not isinstance(band_and_idx_list, list):
            band_and_idx_list = [band_and_idx_list]

        if len(band_and_idx_list) == 0:
            return {}, {}

        band_list = []
        index_list = []
        dem_list = []

        # Check if everything is valid
        for idx_or_band in band_and_idx_list:
            if alias.is_index(idx_or_band):
                if self.has_index(idx_or_band):
                    index_list.append(idx_or_band)
                else:
                    raise InvalidIndexError(f"{idx_or_band} cannot be computed from {self.condensed_name}.")
            elif alias.is_sar_band(idx_or_band):
                raise TypeError(f"You should ask for Optical bands as {self.name} is an optical product.")
            elif alias.is_optical_band(idx_or_band):
                if self.has_band(idx_or_band):
                    band_list.append(idx_or_band)
                else:
                    raise InvalidBandError(f"{idx_or_band} cannot be retrieved from {self.condensed_name}.")
            elif is_dem(idx_or_band):
                dem_list.append(idx_or_band)

        # Get all bands to be open
        bands_to_load = band_list.copy()
        for idx in index_list:
            bands_to_load += index.NEEDED_BANDS[idx]

        # Load band arrays (only keep unique bands: open them only one time !)
        bands, meta = self._load_bands(list(set(bands_to_load)), resolution=resolution, size=size)

        # Compute index (they conserve the nodata)
        idx_and_bands_dict = {idx: idx(bands) for idx in index_list}

        # Add bands
        idx_and_bands_dict.update({band: bands[band] for band in band_list})

        # Add DEM
        dem_bands, dem_meta = self._load_dem(dem_list, resolution=resolution, size=size)
        idx_and_bands_dict.update(dem_bands)
        if not meta:
            meta = dem_meta

        # Manage the case of arrays of different size -> collocate arrays if needed
        idx_and_bands_dict = self._collocate_bands(idx_and_bands_dict, meta)

        return idx_and_bands_dict, meta

    @abstractmethod
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_mean_sun_angles()
        (149.148155074489, 32.6627897525474)
        ```

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _compute_hillshade(self,
                           dem_path: str = "",
                           resolution: Union[float, tuple] = None,
                           size: Union[list, tuple] = None,
                           resampling: Resampling = Resampling.bilinear) -> str:
        """
        Compute Hillshade mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters. If not specified, use the product resolution.
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            resampling (Resampling): Resampling method

        Returns:
            str: Hillshade mask path

        """
        # Warp DEM
        warped_dem_path = self._warp_dem(dem_path, resolution, size, resampling)

        # Get Hillshade path
        hillshade_dem = os.path.join(self.output, f"{self.condensed_name}_HILLSHADE.tif")
        if os.path.isfile(hillshade_dem):
            LOGGER.debug("Already existing hillshade DEM for %s. Skipping process.", self.name)
        else:
            LOGGER.debug("Computing hillshade DEM for %s", self.name)

            # Get angles
            mean_azimuth_angle, mean_zenith_angle = self.get_mean_sun_angles()
            zenith = 90.0 - mean_zenith_angle
            azimuth = mean_azimuth_angle

            # Run cmd
            cmd_hillshade = ["gdaldem", "--config",
                             "NUM_THREADS", MAX_CORES,
                             "hillshade", strings.to_cmd_string(warped_dem_path),
                             "-compute_edges",
                             "-z", "1",
                             "-az", azimuth,
                             "-alt", zenith,
                             "-of", "GTiff",
                             strings.to_cmd_string(hillshade_dem)]
            # Run command
            misc.run_cli(cmd_hillshade)

        return hillshade_dem
