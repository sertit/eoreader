""" Super class for SAR products """
import logging
import os
import re
import tempfile
import zipfile
from abc import abstractmethod
from enum import unique
from string import Formatter
from typing import Union, Callable

import rasterio
from rasterio import crs
import geopandas as gpd
import numpy as np
from rasterio.enums import Resampling
from sertit import files, strings, misc, snap
from sertit.misc import ListEnum
from sertit import rasters, vectors

from eoreader import utils
from eoreader.exceptions import InvalidBandError, InvalidProductError, InvalidTypeError
from eoreader.bands.bands import SarBands, SarBandNames as sbn, BandNames
from eoreader.bands.alias import is_index, is_sar_band, is_optical_band, is_dem
from eoreader.products.product import Product, SensorType
from eoreader.reader import Platform
from eoreader.utils import EOREADER_NAME
from eoreader.env_vars import PP_GRAPH, DSPK_GRAPH, SAR_DEF_RES

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class SarProductType(ListEnum):
    """
    Generic products types, used to chose a SNAP graph.
    """
    CPLX = "COMPLEX"
    """Single Look Complex"""

    GDRG = "GROUND"
    """Ground Range"""

    OTHER = "OTHER"
    """Other products types, no used in EOReader"""
    # Add ortho products ?


class _ExtendedFormatter(Formatter):
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
        self.sar_prod_type = None
        """SAR product type, either Single Look Complex or Ground Range"""

        self.sensor_mode = None
        """Sensor Mode of the current product"""

        self.pol_channels = None
        """Polarization Channels stored in the current product"""

        # Private attributes
        self._band_folder = None
        self._snap_path = None
        self._raw_band_regex = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path)

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting product-type, band names and so on)
        """
        self.tile_name = None
        self.sensor_type = SensorType.SAR
        self.band_names = SarBands()
        self._set_sensor_mode()
        self.pol_channels = self._get_raw_bands()

    def get_default_band(self) -> BandNames:
        """
        Get default band:
        The first existing one between `VV` and `HH` for SAR data.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_default_band()
        <SarBandNames.VV: 'VV'>
        ```

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
        Get default band path (the first existing one between `VV` and `HH` for SAR data), ready to use (orthorectified)

        **WARNING** This functions orthorectifies SAR bands if not existing !

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_default_band_path()
        Executing processing graph
        ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
        '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'
        ```

        Returns:
            str: Default band path
        """
        default_band = self.get_default_band()
        band_path = self.get_band_paths([default_band])

        return band_path[default_band]

    @abstractmethod
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.wgs84_extent()
                               Name  ...                                           geometry
        0  Sentinel-1 Image Overlay  ...  POLYGON ((0.85336 42.24660, -2.32032 42.65493,...
        [1 rows x 12 columns]
        ```

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        raise NotImplementedError("This method should be implemented by a child class")

    def utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.utm_extent()
                               Name  ...                                           geometry
        0  Sentinel-1 Image Overlay  ...  POLYGON ((817914.501 4684349.823, 555708.624 4...
        [1 rows x 12 columns]
        ```

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        utm = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx,
                                                   extent_wgs84.bounds.maxy)
        extent = extent_wgs84.to_crs(utm)

        return extent

    def utm_crs(self) -> crs.CRS:
        """
        Get UTM projection

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.utm_crs()
        CRS.from_epsg(32630)
        ```

        Returns:
            crs.CRS: CRS object
        """
        # Get WGS84 extent
        extent_wgs84 = self.wgs84_extent()

        # Get upper-left corner and deduce UTM proj from it
        crs_str = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx,
                                                       extent_wgs84.bounds.maxy)

        return crs.CRS.from_string(crs_str)

    def _get_sar_product_type(self,
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
        if self.sar_prod_type == SarProductType.OTHER:
            raise NotImplementedError(f"{self.product_type.value} product type is not available ({self.name})")

    @abstractmethod
    def _set_sensor_mode(self) -> None:
        """
        Set SAR sensor mode
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        **WARNING** This functions orthorectifies SAR bands if not existing !

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_band_paths([VV, HH])
        {
            <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  # HH doesn't exist
        }
        ```

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
                speckle_band = sbn.corresponding_speckle(band)
                if speckle_band in self.pol_channels:
                    if sbn.is_despeckle(band):
                        # Despeckle the noisy band
                        band_paths[band] = self._despeckle_sar(speckle_band)
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
        extended_fmt = _ExtendedFormatter()
        band_paths = {}
        for band, band_name in self.band_names.items():
            band_regex = extended_fmt.format(self._raw_band_regex, band_name)

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
                    raise InvalidProductError(f"Only zipped products can be processed without extraction: {self.path}")
            else:
                try:
                    band_paths[band] = files.get_file_in_dir(self._band_folder,
                                                             band_regex,
                                                             exact_name=True,
                                                             get_list=True)
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

        **WARNING** This functions orthorectifies SAR bands if not existing !

        **WARNING** This functions despeckles SAR bands if not existing !

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_existing_band_paths()
        Executing processing graph
        ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
        Executing processing graph
        ....10%....20%....30%....40%....50%....60%....70%....80%....90% done.
        {
            <SarBandNames.VV: 'VV'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',
            <SarBandNames.VH: 'VH'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',
            <SarBandNames.VV_DSPK: 'DESPK_VV'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_DESPK_VV.tif',
            <SarBandNames.VH_DSPK: 'DESPK_VH'>: '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_DESPK_VH.tif'
        }
        ```

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

        **WARNING** This functions orthorectifies SAR bands if not existing !

        **WARNING** This functions despeckles SAR bands if not existing !

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> prod.get_existing_bands()
        [<SarBandNames.VV: 'VV'>,
        <SarBandNames.VH: 'VH'>,
        <SarBandNames.VV_DSPK: 'DESPK_VV'>,
        <SarBandNames.VH_DSPK: 'DESPK_VH'>]
        ```

        Returns:
            list: List of existing bands in the products
        """
        band_paths = self.get_existing_band_paths()
        return list(band_paths.keys())

    # unused band_name (compatibility reasons)
    # pylint: disable=W0613
    def _read_band(self, dataset, x_res: float = None, y_res: float = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"
        >>> prod = Reader().open(path)
        >>> with rasterio.open(prod.get_default_band_path()) as dst:
        >>>     band, meta = prod.read_band(dst, x_res=20, y_res=20)  # You can create not square pixels here
        >>> band
        masked_array(
          data=[[[--, ..., --]]],
          mask=[[[True, ..., True]]],
          fill_value=0.0,
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
        meta = {}
        for band_name, band_path in band_paths.items():
            with rasterio.open(band_path) as band_ds:
                # Read CSK band
                band_arrays[band_name], ds_meta = self._read_band(band_ds, resolution, resolution)

                # Meta
                if not meta:
                    meta = ds_meta.copy()

        return band_arrays, meta

    def load(self,
             band_and_idx_list: Union[list, BandNames, Callable],
             resolution: float = None) -> (dict, dict):
        """
        Load SAR bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> bands, meta = prod.load([GREEN, NDVI], resolution=20)  # Always square pixels here
        >>> bands
        {<function NDVI at 0x00000227FBB929D8>: masked_array(
          data=[[[--, ..., --]]],
          mask=[[[True, ..., True]]],
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
            'dtype': dtype('float32'),
            'nodata': 0.0,
            'width': 14900,
            'height': 11014,
            'count': 1,
            'crs': CRS.from_epsg(32630),
            'transform': Affine(20.000671140939595, 0.0, 554358.8404375388, 0.0, -19.999092064644998, 4897675.306485827)
        }
        ```

        Args:
            band_and_idx_list (list, index): Index list
            resolution (float): Resolution of the band, in meters

        Returns:
            dict, dict: Index and band dict, metadata
        """
        # Check if all bands are valid
        if not isinstance(band_and_idx_list, list):
            band_and_idx_list = [band_and_idx_list]

        if len(band_and_idx_list) == 0:
            return {}, {}

        band_list = []
        dem_list = []
        for band in band_and_idx_list:
            if is_index(band):
                raise NotImplementedError("For now, no index is implemented for SAR data.")
            elif is_optical_band(band):
                raise TypeError(f"You should ask for SAR bands as {self.name} is a SAR product.")
            elif is_sar_band(band):
                if not self.has_band(band):
                    raise InvalidBandError(f"{band} cannot be retrieved from {self.condensed_name}")
                else:
                    band_list.append(band)
            elif is_dem(band):
                dem_list.append(band)
            else:
                raise InvalidTypeError(f"{band} is neither a band nor an index !")

        # Load bands
        bands, meta = self._load_bands(band_list, resolution=resolution)

        # Add DEM
        dem_bands, dem_meta = self._load_dem(dem_list, resolution=resolution)
        bands.update(dem_bands)
        if not meta:
            meta = dem_meta

        # Manage the case of arrays of different size -> collocate arrays if needed
        bands = self._collocate_bands(bands, meta)

        return bands, meta

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
            target_file = os.path.join(tmp_dir, f"{self._set_condensed_name()}")

            # Use dimap for speed and security (ie. GeoTiff's broken georef)
            pp_target = f"{target_file}"
            pp_dim = pp_target + '.dim'

            # Pre-process graph
            if PP_GRAPH not in os.environ:
                sat = "s1" if self.sat_id == Platform.S1.name else "sar"
                spt = "grd" if self.sar_prod_type == SarProductType.GDRG else "cplx"
                pp_graph = os.path.join(utils.get_data_dir(), f"{spt}_{sat}_preprocess_default.xml")
            else:
                pp_graph = os.environ[PP_GRAPH]
                if not os.path.isfile(pp_graph) or not pp_graph.endswith(".xml"):
                    FileNotFoundError(f"{pp_graph} cannot be found.")

            # Command line
            if not os.path.isfile(pp_dim):
                def_res = float(os.environ.get(SAR_DEF_RES, self.resolution))
                res_m = resolution if resolution else def_res
                res_deg = res_m / 10. * 8.983152841195215E-5  # Approx
                cmd_list = snap.get_gpt_cli(pp_graph,
                                            [f'-Pfile={strings.to_cmd_string(self._snap_path)}',
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
            target_file = os.path.join(tmp_dir, f"{self._set_condensed_name()}_DESPK")
            dspk_dim = target_file + '.dim'

            # Despeckle graph
            if DSPK_GRAPH not in os.environ:
                dspk_graph = os.path.join(utils.get_data_dir(), f"sar_despeckle_default.xml")
            else:
                dspk_graph = os.environ[DSPK_GRAPH]
                if not os.path.isfile(dspk_graph) or not dspk_graph.endswith(".xml"):
                    FileNotFoundError(f"{dspk_graph} cannot be found.")

            # Create command line and run it
            if not os.path.isfile(dspk_dim):
                path = self.get_band_paths([band])[band]
                cmd_list = snap.get_gpt_cli(dspk_graph,
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

    def _compute_hillshade(self,
                           dem_path: str = "",
                           resolution: Union[float, tuple] = None,
                           resampling: Resampling = Resampling.bilinear) -> str:
        """
        Compute Hillshade mask

        Args:
            dem_path (str): DEM path, using EUDEM/MERIT DEM if none
            resolution (Union[float, tuple]): Resolution in meters. If not specified, use the product resolution.
            resampling (Resampling): Resampling method
        Returns:
            str: Hillshade mask path
        """
        raise InvalidProductError("Impossible to compute hillshade mask for SAR data.")
