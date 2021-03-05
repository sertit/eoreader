"""
COSMO-SkyMed products
More info here:
https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
"""
import logging
import os
import re
import zipfile
from abc import abstractmethod
from datetime import datetime
from enum import unique
from string import Formatter
from typing import Union, Callable

import rasterio
import rasterio.features
import rasterio.warp
import rasterio.crs
import rasterio.transform
import geopandas as gpd
import numpy as np
from rasterio.enums import Resampling
from sertit import files
from sertit.misc import ListEnum
from sertit import rasters, vectors

from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError, EoReaderError
from eoreader.bands import SarBands, SarBandNames as sbn, BandNames
from eoreader.products.product import Product, SensorType
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class SarProductType(ListEnum):
    """
    Generic products types to chose a SNAP graph
    """
    CPLX = "COMPLEX"  # Single Look Complex
    GDRG = "GROUND"  # Ground Range
    OTHER = "OTHER"  # Other products types, no used in EEO
    # Add ortho eoreader ?


class ExtendedFormatter(Formatter):
    """An extended format string formatter

    Formatter with extended conversion symbol
    """

    def convert_field(self, value, conversion):
        """ Extend conversion symbol
        Following additional symbol has been added
        * l: convert to string and low case
        * u: convert to string and up case

        default are:
        * s: convert with str()
        * r: convert with repr()
        * a: convert with ascii()
        """

        if conversion == "u":
            cv_field = str(value).upper()
        elif conversion == "l":
            cv_field = str(value).lower()
        else:
            cv_field = super().convert_field(value, conversion)

        return cv_field


class SarProduct(Product):
    """ Super class for SAR Products """

    def __init__(self, product_path: str, archive_path: str = None) -> None:
        super().__init__(product_path, archive_path)
        self.tile_name = None
        self.sar_prod_type = None
        self.get_product_type()
        self.sensor_type = SensorType.SAR
        self.sensor_mode = None
        self.get_sensor_mode()
        self.band_folder = None
        self.band_names = SarBands()
        self.snap_path = None
        self.raw_band_regex = None
        self.pol_channels = None

    def get_default_band(self) -> BandNames:
        """
        Get default band

        Returns:
            str: Default band
        """
        existing_bands = self.get_raw_bands()
        if not existing_bands:
            raise InvalidProductError(f"No band exists for products: {self.name}")

        # The order matters, as we almost always prefer VV and HH
        if sbn.VV in existing_bands:
            default_band = sbn.VV
        elif sbn.HH in existing_bands:
            default_band = sbn.HH
        elif sbn.VH in existing_bands:
            default_band = sbn.VH
        elif sbn.HV in existing_bands:
            default_band = sbn.HV
        else:
            raise InvalidTypeError(f"Invalid bands for products: {existing_bands}")

        return default_band

    # Parameters differ from overridden 'get_default_band_path' method (arguments-differ)
    # pylint: disable=W0221
    def get_default_band_path(self, fail_if_non_existing: bool = False, only_ortho_bands: bool = True) -> str:
        """
        Get default band path (among the existing ones)

        Args:
            fail_if_non_existing (bool): Fail if a non existing band is asked
            only_ortho_bands (bool): Return only orthorectified bands

        Returns:
            str: Default band path
        """
        default_band = self.get_default_band()
        band_path = self.get_band_paths([default_band],
                                        fail_if_non_existing=fail_if_non_existing,
                                        only_ortho_bands=only_ortho_bands)

        return band_path[default_band]

    @abstractmethod
    def get_wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        try:
            # Get extent from orthorectified bands
            extent = rasters.get_extent(self.get_default_band_path(only_ortho_bands=True,
                                                                   fail_if_non_existing=True))
        except (FileNotFoundError, TypeError):
            # Get WGS84 extent
            extent_wgs84 = self.get_wgs84_extent()

            # Get upper-left corner and deduce UTM proj from it
            utm = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy)
            extent = extent_wgs84.to_crs(utm)

        return extent

    def get_utm_proj(self) -> rasterio.crs.CRS:
        """
        Get UTM projection

        Returns:
            rasterio.crs.CRS: CRS object
        """
        try:
            # Get extent from orthorectified bands
            band_path = self.get_default_band_path(only_ortho_bands=True,
                                                   fail_if_non_existing=True)
            with rasterio.open(band_path) as dst:
                utm = dst.crs
        except FileNotFoundError:
            # Get WGS84 extent
            extent_wgs84 = self.get_wgs84_extent()

            # Get upper-left corner and deduce UTM proj from it
            utm = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy)

        return utm

    @abstractmethod
    def get_product_type(self) -> None:
        """ Get products type """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_sar_product_type(self,
                             prod_type_pos: int,
                             gdrg_types: Union[ListEnum, list],
                             cplx_types: Union[ListEnum, list]) -> None:
        """
        Get products type, special function for SAR satellites.

        Args:
            prod_type_pos (int): Position of the products type in the file name
            gdrg_types (Union[ListEnum, list]): Ground Range products types
            cplx_types (Union[ListEnum, list]): Complex products types
        """
        # Get and check products type class
        if not isinstance(gdrg_types, list):
            gdrg_types = [gdrg_types]
        if not isinstance(cplx_types, list):
            cplx_types = [cplx_types]

        all_types = gdrg_types + cplx_types
        prod_type_class = all_types[0].__class__
        assert all(isinstance(prod_type, prod_type_class) for prod_type in all_types)

        # Get products type
        try:
            # All products types can be found in the filename and are 3 characters long
            self.product_type = prod_type_class.from_value(self.get_split_name()[prod_type_pos][:3])
        except ValueError as ex:
            raise InvalidTypeError(f"Invalid products type for {self.name}") from ex

        # Link to SAR generic products types
        if self.product_type in gdrg_types:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type in cplx_types:
            self.sar_prod_type = SarProductType.CPLX
        else:
            self.sar_prod_type = SarProductType.OTHER

        # Discard invalid products types
        if self.product_type == SarProductType.OTHER:
            raise NotImplementedError(f"For now, {self.product_type.value} products type "
                                      f"is not used in eoreader processes: {self.name}")

    @abstractmethod
    def get_sensor_mode(self) -> None:
        """
        Get products type from S2 products name (could check the metadata too)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the products's acquisition datetime, with format YYYYMMDDTHHMMSS <-> %Y%m%dT%H%M%S

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_band_paths(self,
                       band_list: list,
                       fail_if_non_existing: bool = False,
                       only_ortho_bands: bool = False) -> dict:
        """
        Return the band paths.

        Args:
            band_list (list): List of the wanted bands
            fail_if_non_existing (bool): Fail if non existing band
            only_ortho_bands (bool): Outputs only orthorectified bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            assert band in sbn
            bname = self.band_names[band]
            if bname is None:
                raise InvalidProductError(f"Non existing band ({band.name}) for {self.name}")
            try:
                # Try to load orthorectified bands
                band_paths[band] = files.get_file_in_dir(self.output,
                                                         f"{self.get_condensed_name()}_{bname}.tif",
                                                         exact_name=True)
            except FileNotFoundError as ex:
                if not only_ortho_bands:
                    try:
                        band_paths[band] = self.get_raw_band_paths()[band]
                    except IndexError:
                        if fail_if_non_existing:
                            raise InvalidProductError(f"Non existing band {bname} in {self.output}") from ex
                        # Else
                        continue
                else:
                    if fail_if_non_existing:
                        raise FileNotFoundError(f"Non existing orthorectified band {bname} in {self.output}") from ex
                    # Else
                    continue

        return band_paths

    def get_raw_band_paths(self) -> dict:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            dict: Dictionary containing the path of every band existing in the raw products
        """
        extended_fmt = ExtendedFormatter()
        band_paths = {}
        for band, band_name in self.band_names.items():
            band_regex = extended_fmt.format(self.raw_band_regex, band_name)

            if self.is_archived:
                if self.path.endswith(".zip"):
                    # Open the zip file
                    with zipfile.ZipFile(self.path, "r") as zip_ds:
                        # Get the correct band path
                        regex = re.compile(band_regex.replace("*", ".*"))
                        try:
                            band_paths[band] = list(filter(regex.match, [f.filename for f in zip_ds.filelist]))[0]
                        except IndexError:
                            continue
                else:
                    raise InvalidProductError(f"Only zipped eoreader can be processed without extraction: {self.path}")
            else:
                try:
                    band_paths[band] = files.get_file_in_dir(self.band_folder, band_regex, exact_name=True)
                except FileNotFoundError:
                    continue

        return band_paths

    def get_raw_bands(self) -> list:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            list: List of existing bands in the raw products (vv, hh, vh, hv)
        """
        band_paths = self.get_raw_band_paths()
        return list(band_paths.keys())

    def get_existing_band_paths(self) -> dict:
        """
        Return the existing orthorectified band paths (including despeckle bands).

        Returns:
            dict: Dictionary containing the path of every orthorectified bands
        """
        return self.get_band_paths(list(sbn), only_ortho_bands=True)

    def get_existing_bands(self) -> list:
        """
        Return the existing orthorectified bands (including despeckle bands).

        Returns:
            list: List of existing bands in the products
        """
        band_paths = self.get_existing_band_paths()
        return list(band_paths.keys())

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
        # Read band
        band_array, dst_meta = rasters.read(dataset, [x_res, y_res], Resampling.bilinear)

        # Set correct nodata
        masked_array = np.ma.masked_array(band_array,
                                          mask=np.where(band_array == self.nodata, 1, 0).astype(np.uint8),
                                          fill_value=self.nodata)

        return masked_array, dst_meta

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
        band_arrays = {}
        meta = None
        for band_name, band_path in band_paths.items():
            # Signature of a processing: image starting with the condensed name
            if not os.path.basename(band_path).startswith(self.get_condensed_name()):
                raise EoReaderError("You need to add a terrain correction step before using SAR images.")

            with rasterio.open(band_path) as band_ds:
                # Read CSK band
                band_arrays[band_name], ds_meta = self.read_band(band_ds, resolution, resolution)

                # Meta
                if not meta:
                    meta = ds_meta.copy()

        return band_arrays, meta

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
        if index_list:
            raise NotImplementedError("For now, no index is implemented for SAR data.")

        # Check if all bands are valid
        if not isinstance(band_list, list):
            band_list = [band_list]

        for band in band_list:
            if not self.has_band(band):
                raise InvalidBandError(f"{band} cannot be retrieved from {self.get_condensed_name()}")

        return self.load_bands(band_list, resolution)

    @abstractmethod
    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        raise NotImplementedError("This method should be implemented by a child class")
