"""
COSMO-SkyMed products
More info here:
https://earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description
"""
import logging
import os
import re
import tempfile
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
from sertit import files, strings, misc
from sertit.misc import ListEnum
from sertit import rasters, vectors

from eoreader import utils
from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError
from eoreader.bands.bands import SarBands, SarBandNames as sbn, BandNames
from eoreader.bands.alias import is_index, is_sar_band, is_optical_band
from eoreader.products.product import Product, SensorType
from eoreader.reader import Platform
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

PP_ENV = "EOREADER_PP_GRAPH"
DSPK_ENV = "EOREADER_DSPK_GRAPH"
SAR_DEF_RES = "EOREADER_SAR_DEFAULT_RES"


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

    def __init__(self, product_path: str, archive_path: str = None, output_path=None) -> None:
        super().__init__(product_path, archive_path, output_path)
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
        existing_bands = self._get_raw_bands()
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
    def get_default_band_path(self) -> str:
        """
        Get default band path (among the existing ones)

        Returns:
            str: Default band path
        """
        default_band = self.get_default_band()
        band_path = self.get_band_paths([default_band])

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

    def utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # Get WGS84 extent
        extent_wgs84 = self.get_wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        utm = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx,
                                                   extent_wgs84.bounds.maxy)
        extent = extent_wgs84.to_crs(utm)

        return extent

    def utm_crs(self) -> str:
        """
        Get UTM projection

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Get WGS84 extent
        extent_wgs84 = self.get_wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        return vectors.corresponding_utm_projection(extent_wgs84.bounds.minx,
                                                    extent_wgs84.bounds.maxy)

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
            self.product_type = prod_type_class.from_value(self.split_name[prod_type_pos][:3])
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
            bname = self.band_names[band]
            if bname is None:
                raise InvalidProductError(f"Non existing band ({band.name}) for {self.name}")
            try:
                # Try to load orthorectified bands
                band_paths[band] = files.get_file_in_dir(self.output,
                                                         f"{self.condensed_name}_{bname}.tif",
                                                         exact_name=True)
            except FileNotFoundError:
                if sbn.is_despeckle(band):
                    # Despeckle the noisy band
                    band_paths[band] = self._despeckle_sar(sbn.corresponding_speckle(band))
                else:
                    all_band_paths = self._pre_process_sar(resolution)
                    band_paths = {band: path for band, path in all_band_paths.items() if band in band_list}

        return band_paths

    def _get_raw_band_paths(self) -> dict:
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

    def _get_raw_bands(self) -> list:
        """
        Return the existing band paths (as they come with th archived products).

        Returns:
            list: List of existing bands in the raw products (vv, hh, vh, hv)
        """
        band_paths = self._get_raw_band_paths()
        return list(band_paths.keys())

    def get_existing_band_paths(self) -> dict:
        """
        Return the existing orthorectified band paths (including despeckle bands).

        Returns:
            dict: Dictionary containing the path of every orthorectified bands
        """
        # Get raw bands (maximum number of bands)
        raw_bands = self._get_raw_bands()
        possible_bands = raw_bands + [sbn.corresponding_despeckle(band) for band in raw_bands]

        return self.get_band_paths(possible_bands)

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

    def _load_bands(self, band_list: [list, BandNames], resolution: float = None) -> (dict, dict):
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
        band_arrays = {}
        meta = None
        for band_name, band_path in band_paths.items():
            with rasterio.open(band_path) as band_ds:
                # Read CSK band
                band_arrays[band_name], ds_meta = self.read_band(band_ds, resolution, resolution)

                # Meta
                if not meta:
                    meta = ds_meta.copy()

        return band_arrays, meta

    def load(self,
             band_and_idx_list: Union[list, BandNames, Callable],
             resolution: float = 20) -> (dict, dict):
        """
        Open the bands and compute the wanted index.
        You can add some bands in the dict.

        Args:
            band_and_idx_list (list, index): Index list
            resolution (float): Resolution of the band, in meters

        Returns:
            dict, dict: Index and band dict, metadata
        """
        # Check if all bands are valid
        if not isinstance(band_and_idx_list, list):
            band_and_idx_list = [band_and_idx_list]

        for band in band_and_idx_list:
            if is_index(band):
                raise NotImplementedError("For now, no index is implemented for SAR data.")
            elif is_optical_band(band):
                raise TypeError(f"You should ask for SAR bands as {self.name} is a SAR product.")
            elif is_sar_band(band):
                if not self.has_band(band):
                    raise InvalidBandError(f"{band} cannot be retrieved from {self.condensed_name}")
            else:
                raise InvalidTypeError(f"{band} is neither a band nor an index !")

        return self._load_bands(band_and_idx_list, resolution)

    @abstractmethod
    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({acq_datetime}_S1_{sensor_mode}_{product_type}).

        Returns:
            str: Condensed S1 name
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _pre_process_sar(self, resolution: float = None) -> dict:
        """
        Pre-process SAR data (orthorectify...)

        Args:
            resolution (float): Resolution

        Returns:
            dict: Dictionary containing {band: path}
        """
        out = {}

        # Create target dir (tmp dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Set command as a list
            target_file = os.path.join(tmp_dir, f"{self.get_condensed_name()}")

            # Use dimap for speed and security (ie. GeoTiff's broken georef)
            pp_target = f"{target_file}"
            pp_dim = pp_target + '.dim'

            # Pre-process graph
            if PP_ENV not in os.environ:
                sat = "s1" if self.sat_id == Platform.S1 else "sar"
                spt = "grd" if self.sar_prod_type == SarProductType.GDRG else "cplx"
                pp_graph = os.path.join(utils.get_gpt_graphs_dir(), f"{spt}_{sat}_preprocess_default.xml")
            else:
                pp_graph = os.environ[PP_ENV]
                if not os.path.isfile(pp_graph) or not pp_graph.endswith(".xml"):
                    FileNotFoundError(f"{pp_graph} cannot be found.")

            # Command line
            if not os.path.isfile(pp_dim):
                def_res = float(os.environ.get(SAR_DEF_RES, 0.0))
                res_m = resolution if resolution else def_res
                res_deg = res_m / 10. * 8.983152841195215E-5  # Approx
                cmd_list = utils.get_gpt_cli(pp_graph,
                                             [f'-Pfile={strings.to_cmd_string(self.snap_path)}',
                                              f'-Pout={pp_dim}',
                                              f'-Pcrs={self.utm_crs()}',
                                              f'-Pres_m={res_m}',
                                              f'-Pres_deg={res_deg}'],
                                             display_snap_opt=LOGGER.level == logging.DEBUG)

                # Pre-process SAR images according to the given graph
                LOGGER.debug("Pre-process SAR image")
                misc.run_cli(cmd_list)

            # Convert DIMAP images to GeoTiff
            for pol in self.pol_channels:
                # Speckle image
                out[sbn.from_value(pol)] = self._write_sar(pp_dim, pol.value)

        return out

    def _despeckle_sar(self, band: sbn) -> str:
        """
        Pre-process SAR data (orthorectify...)

        Args:
            band (sbn): Band to despeckle

        Returns:
            str: Despeckled path
        """
        # Create target dir (tmp dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Out files
            target_file = os.path.join(tmp_dir, f"{self.get_condensed_name()}_DESPK")
            dspk_dim = target_file + '.dim'

            # Despeckle graph
            if DSPK_ENV not in os.environ:
                dspk_graph = os.path.join(utils.get_gpt_graphs_dir(), f"sar_despeckle_default.xml")
            else:
                dspk_graph = os.environ[DSPK_ENV]
                if not os.path.isfile(dspk_graph) or not dspk_graph.endswith(".xml"):
                    FileNotFoundError(f"{dspk_graph} cannot be found.")

            # Create command line and run it
            if not os.path.isfile(dspk_dim):
                path = self.get_band_paths([band])[band]
                cmd_list = utils.get_gpt_cli(dspk_graph,
                                             [f'-Pfile={path}',
                                              f'-Pout={dspk_dim}'],
                                             display_snap_opt=False)

                # Pre-process SAR images according to the given graph
                LOGGER.debug("Despeckle SAR image")
                misc.run_cli(cmd_list)

            # Convert DIMAP images to GeoTiff
            out = self._write_sar(dspk_dim, band.value)

        return out

    def _write_sar(self, dim_path: str, pol_up: str):
        """
        Write SAR image on disk.

        Args:
            dim_path (str): DIMAP path
            pol_up (str): Polarization name
        """
        pol_up = pol_up.upper()  # To be sure

        # Get .img file path (readable by rasterio)
        try:
            img = rasters.get_dim_img_path(dim_path, pol_up)
        except FileNotFoundError:
            img = rasters.get_dim_img_path(dim_path)  # Maybe not the good name

        with rasterio.open(img, 'r') as dst:
            # Read array and set no data
            arr = dst.read(masked=True)
            arr[np.isnan(arr)] = self.nodata
            meta = dst.meta

            # Save the file as the terrain-corrected image
            file_path = os.path.join(self.output, f"{files.get_filename(dim_path)}_{pol_up}.tif")
            rasters.write(arr, file_path, meta, nodata=self.nodata)

        return file_path
