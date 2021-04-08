""" Sentinel-3 products """
import logging
import os
import tempfile
from datetime import datetime
from enum import unique
from functools import reduce
from typing import Union

import netCDF4
import numpy as np
import rasterio
import geopandas as gpd
from lxml import etree
from rasterio.enums import Resampling
from rasterio.windows import Window
from sertit import rasters, vectors, files, strings, misc, snap
from sertit.misc import ListEnum

from eoreader import utils
from eoreader.bands.alias import ALL_CLOUDS, RAW_CLOUDS, CLOUDS, CIRRUS
from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.products.product import path_or_dst
from eoreader.utils import EOREADER_NAME, DATETIME_FMT
from eoreader.env_vars import S3_DEF_RES

LOGGER = logging.getLogger(EOREADER_NAME)
BT_BANDS = [obn.MIR, obn.TIR_1, obn.TIR_2]


@unique
class S3ProductType(ListEnum):
    """ Sentinel-3 products types (not exhaustive, only L1)"""
    OLCI_EFR = "OL_1_EFR___"
    """OLCI EFR Product Type"""

    SLSTR_RBT = "SL_1_RBT___"
    """SLSTR RBT Product Type"""


@unique
class S3Instrument(ListEnum):
    """ Sentinel-3 products types """
    OLCI = "OLCI"
    """OLCI Instrument"""

    SLSTR = "SLSTR"
    """SLSTR Instrument"""


@unique
class S3DataTypes(ListEnum):
    """ Sentinel-3 data types -> only considering useful ones """
    EFR = "EFR___"
    """EFR Data Type, for OLCI instrument"""

    RBT = "RBT__"
    """RBT Data Type, for SLSTR instrument"""


class S3Product(OpticalProduct):
    """
    Class of Sentinel-3 Products

    **Note**: All S3-OLCI bands won't be used in EOReader !

    **Note**: We only use NADIR rasters for S3-SLSTR bands
    """

    def __init__(self, product_path: str, archive_path: str = None, output_path=None) -> None:
        self._instrument_name = None
        self._data_type = None
        self._snap_no_data = -1
        super().__init__(product_path, archive_path, output_path)  # Order is important here

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Post init done by the super class
        super()._post_init()

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        if self._instrument_name == S3Instrument.OLCI:
            def_res = 300.
        else:
            def_res = 500.
        return def_res

    def _set_product_type(self) -> None:
        """ Get products type """
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        if "OL" in self.name:
            # Instrument
            self._instrument_name = S3Instrument.OLCI

            # Data type
            if S3DataTypes.EFR.value in self.name:
                self._data_type = S3DataTypes.EFR
                self.product_type = S3ProductType.OLCI_EFR
            else:
                raise InvalidTypeError("Only EFR data type is used for Sentinel-3 OLCI data.")

            # Bands
            self.band_names.map_bands({
                obn.CA: '02',
                obn.BLUE: '03',
                obn.GREEN: '06',
                obn.RED: '08',
                obn.VRE_1: '11',
                obn.VRE_2: '12',
                obn.VRE_3: '16',
                obn.NIR: '17',
                obn.NNIR: '17',
                obn.WV: '20',
                obn.FNIR: '21'
            })
        elif "SL" in self.name:
            # Instrument
            self._instrument_name = S3Instrument.SLSTR

            # Data type
            if S3DataTypes.RBT.value in self.name:
                self._data_type = S3DataTypes.RBT
                self.product_type = S3ProductType.SLSTR_RBT
            else:
                raise InvalidTypeError("Only RBT data type is used for Sentinel-3 SLSTR data.")

            # Bands
            self.band_names.map_bands({
                obn.GREEN: '1',  # radiance, 500m
                obn.RED: '2',  # radiance, 500m
                obn.NIR: '3',  # radiance, 500m
                obn.NNIR: '3',  # radiance, 500m
                obn.SWIR_CIRRUS: '4',  # radiance, 500m
                obn.SWIR_1: '5',  # radiance, 500m
                obn.SWIR_2: '6',  # radiance, 500m
                obn.MIR: '7',  # brilliance temperature, 1km
                obn.TIR_1: '8',  # brilliance temperature, 1km
                obn.TIR_2: '9'  # brilliance temperature, 1km
            })
        else:
            raise InvalidProductError(f"Invalid Sentinel-3 name: {self.name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2019, 11, 15, 23, 37, 22)
        >>> prod.get_datetime(as_datetime=False)
        '20191115T233722'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """

        date = self.split_name[4]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def _get_snap_band_name(self, band: obn) -> str:
        """
        Get SNAP band name.
        Args:
            band (obn): Band as an OpticalBandNames

        Returns:
            str: Band name with SNAP format
        """
        # Get band number
        band_nb = self.band_names[band]
        if band_nb is None:
            raise InvalidProductError(f"Non existing band ({band.name}) for S3-{self._data_type.name} products")

        # Get band name
        if self._data_type == S3DataTypes.EFR:
            snap_bn = f"Oa{band_nb}_reflectance"  # Converted into reflectance previously in the graph
        elif self._data_type == S3DataTypes.RBT:
            if band in BT_BANDS:
                snap_bn = f"S{band_nb}_BT_in"
            else:
                snap_bn = f"S{band_nb}_reflectance_an"  # Conv into reflectance previously in the graph
        else:
            raise InvalidTypeError(f"Unknown data type for Sentinel-3 data: {self._data_type}")

        return snap_bn

    def _get_band_from_filename(self, band_filename: str) -> obn:
        """
        Get band from filename
        Args:
            band_filename (str): Band filename

        Returns:
            obn: Band name with SNAP format
        """
        # Get band name
        if self._data_type == S3DataTypes.EFR:
            band_nb = band_filename[2:4]
        elif self._data_type == S3DataTypes.RBT:
            band_nb = band_filename[1]
        else:
            raise InvalidTypeError(f"Invalid Sentinel-3 datatype: {self._data_type}")

        # Get band
        band = list(self.band_names.keys())[list(self.band_names.values()).index(band_nb)]

        return band

    def _get_slstr_quality_flags_name(self, band: obn) -> str:
        """
        Get SNAP band name.
        Args:
            band (obn): Band as an OpticalBandNames

        Returns:
            str: Quality flag name with SNAP format
        """
        # Get band number
        band_nb = self.band_names[band]
        if band_nb is None:
            raise InvalidProductError(f"Non existing band ({band.name}) for S3-{self._data_type.name} products")

        # Get quality flag name
        if self._data_type == S3DataTypes.RBT:
            snap_bn = f"S{band_nb}_exception_{'i' if band in BT_BANDS else 'a'}n"
        else:
            raise InvalidTypeError(f"This function only works for Sentinel-3 SLSTR data: {self._data_type}")

        return snap_bn

    def _get_band_filename(self, band: Union[obn, str]) -> str:
        """
        Get band filename from its band type

        Args:
            band ( Union[obn, str]): Band as an OpticalBandNames or directly the snap_name

        Returns:
            str: Band name
        """
        if isinstance(band, obn):
            snap_name = self._get_snap_band_name(band)
        elif isinstance(band, str):
            snap_name = band
        else:
            raise InvalidTypeError("The given band should be an OpticalBandNames or directly the snap_name")

        # Remove _an/_in for SLSTR products
        if self._data_type == S3DataTypes.RBT:
            if "cloud" not in snap_name:
                snap_name = snap_name[:-3]
            elif "an" in snap_name:
                snap_name = snap_name[:-3] + "_RAD"
            else:
                # in
                snap_name = snap_name[:-3] + "_BT"

        return snap_name

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: If not existing, this function will orthorectify your bands !

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> prod.get_band_paths([GREEN, RED])
        Executing processing graph
        ...11%...21%...31%...42%...52%...62%...73%...83%... done.
        {
            <OpticalBandNames.GREEN: 'GREEN'>: '20191115T233722_S3_SLSTR_RBT\\S1_reflectance.tif',
            <OpticalBandNames.RED: 'RED'>: '20191115T233722_S3_SLSTR_RBT\\S2_reflectance.tif',
        }
        ```

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        use_snap = False
        for band in band_list:
            # Get standard band names
            band_name = self._get_band_filename(band)

            try:
                # Try to open converted images
                band_paths[band] = files.get_file_in_dir(self.output, band_name + ".tif")
            except (FileNotFoundError, TypeError):
                use_snap = True

        # If not existing (file or output), convert them
        if use_snap:
            all_band_paths = self._preprocess_s3(resolution)
            band_paths = {band: all_band_paths[band] for band in band_list}

        return band_paths

    # pylint: disable=W0613
    @path_or_dst
    def _read_band(self,
                   dataset,
                   resolution: Union[tuple, list, float] = None,
                   size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset.

        .. WARNING:: Invalid pixels are not managed here, please consider using `load` or use it at your own risk!

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> band, meta = prod._read_band(prod.get_default_band_path(), resolution=500)
        >>> band
        masked_array(
          data=[[[-1.0, ..., -1.0]]],
          mask=[[[False, ..., False],
          fill_value=1e+20,
          dtype=float32)
        >>> meta
        {
            'driver': 'GTiff',
            'dtype': dtype('float32'),
            'nodata': 0.0,
            'width': 3530,
            'height': 3099,
            'count': 1,
            'crs': CRS.from_epsg(32755),
            'transform': Affine(500.0, 0.0, -276153.9721025338, 0.0, -500.0, 7671396.450676169)
        }

        Args:
            dataset (Dataset): Band dataset
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            np.ma.masked_array, dict: Radar band, saved as float 32 and its metadata

        """
        # Read band
        return rasters.read(dataset,
                            resolution=resolution,
                            size=size,
                            resampling=Resampling.bilinear)

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
        if self._instrument_name == S3Instrument.OLCI:
            band_arr_mask, meta = self._manage_invalid_pixels_olci(band_arr, band, meta,
                                                                   resolution=resolution,
                                                                   size=size)
        else:
            band_arr_mask, meta = self._manage_invalid_pixels_slstr(band_arr, band, meta,
                                                                    resolution=resolution,
                                                                    size=size)

        return band_arr_mask, meta

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels_olci(self,
                                    band_arr: np.ma.masked_array,
                                    band: obn,
                                    meta: dict,
                                    resolution: float = None,
                                    size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...) for OLCI data.
        See there:
        https://sentinel.esa.int/documents/247904/1872756/Sentinel-3-OLCI-Product-Data-Format-Specification-OLCI-Level-1

        QUALITY FLAGS (From end to start of the 32 bits):
        | Bit |  Flag               |
        |----|----------------------|
        | 0  |   saturated21        |
        | 1  |   saturated20        |
        | 2  |   saturated19        |
        | 3  |   saturated18        |
        | 4  |   saturated17        |
        | 5  |   saturated16        |
        | 6  |   saturated15        |
        | 7  |   saturated14        |
        | 8  |   saturated13        |
        | 9  |   saturated12        |
        | 10 |   saturated11        |
        | 11 |   saturated10        |
        | 11 |   saturated09        |
        | 12 |   saturated08        |
        | 13 |   saturated07        |
        | 14 |   saturated06        |
        | 15 |   saturated05        |
        | 16 |   saturated04        |
        | 17 |   saturated03        |
        | 18 |   saturated02        |
        | 19 |   saturated01        |
        | 20 |   dubious            |
        | 21 |   sun-glint_risk     |
        | 22 |   duplicated         |
        | 23 |   cosmetic           |
        | 24 |   invalid            |
        | 25 |   straylight_risk    |
        | 26 |   bright             |
        | 27 |   tidal_region       |
        | 28 |   fresh_inland_water |
        | 19 |   coastline          |
        | 30 |   land               |

        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ma.masked_array, dict: Cleaned band array and its metadata
        """
        nodata_true = 1
        nodata_false = 0

        # Bit ids
        band_bit_id = {
            obn.CA: 18,  # Band 2
            obn.BLUE: 17,  # Band 3
            obn.GREEN: 14,  # Band 6
            obn.RED: 12,  # Band 8
            obn.VRE_1: 10,  # Band 11
            obn.VRE_2: 9,  # Band 12
            obn.VRE_3: 5,  # Band 16
            obn.NIR: 4,  # Band 17
            obn.NNIR: 4,  # Band 17
            obn.WV: 1,  # Band 20
            obn.FNIR: 0  # Band 21
        }
        invalid_id = 24
        sat_band_id = band_bit_id[band]

        # Open quality flags
        qual_flags_path = os.path.join(self.output, "quality_flags.tif")
        if not os.path.isfile(qual_flags_path):
            LOGGER.warning("Impossible to open quality flags %s. Taking the band as is.", qual_flags_path)
            return band_arr, meta

        # Open flag file
        qual_arr, _ = rasters.read(qual_flags_path,
                                   resolution=resolution,
                                   size=size,
                                   resampling=Resampling.nearest,  # Nearest to keep the flags
                                   masked=False)
        invalid, sat = rasters.read_bit_array(qual_arr, [invalid_id, sat_band_id])

        # Get nodata mask
        no_data = np.where(band_arr == self._snap_no_data, nodata_true, nodata_false)

        # Combine masks
        mask = no_data | invalid | sat

        # DO not set 0 to epsilons as they are a part of the
        return self._create_band_masked_array(band_arr, mask, meta)

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels_slstr(self,
                                     band_arr: np.ma.masked_array,
                                     band: obn,
                                     meta: dict,
                                     resolution: float = None,
                                     size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        ISP_absent pixel_absent not_decompressed no_signal saturation invalid_radiance no_parameters unfilled_pixel"

        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ma.masked_array, dict: Cleaned band array and its metadata
        """
        nodata_true = 1
        nodata_false = 0

        # Open quality flags (discard _an/_in)
        qual_flags_path = os.path.join(self.output, self._get_slstr_quality_flags_name(band)[:-3] + ".tif")
        if not os.path.isfile(qual_flags_path):
            LOGGER.warning("Impossible to open quality flags %s. Taking the band as is.", qual_flags_path)
            return band_arr, meta

        # Open flag file
        qual_arr, _ = rasters.read(qual_flags_path,
                                   resolution=resolution,
                                   size=size,
                                   resampling=Resampling.nearest,  # Nearest to keep the flags
                                   masked=False)

        # Set no data for everything (except ISP) that caused an exception
        exception = np.where(qual_arr > 2, nodata_true, nodata_false)

        # Get nodata mask
        no_data = np.where(band_arr.data == self._snap_no_data, nodata_true, nodata_false)

        # Combine masks
        mask = no_data | exception

        # DO not set 0 to epsilons as they are a part of the
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
        # Return empty if no band are specified
        if not band_list:
            return {}, {}

        # Get band paths
        if not isinstance(band_list, list):
            band_list = [band_list]
        band_paths = self.get_band_paths(band_list)

        # Open bands and get array (resampled if needed)
        band_arrays, meta = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays, meta

    def _preprocess_s3(self, resolution: float = None):
        """
        pre-process S3 bands (orthorectify...)

        Args:
            resolution (float): Resolution

        Returns:
            dict: Dictionary containing {band: path}
        """

        band_paths = {}

        # DIM in tmp files
        with tempfile.TemporaryDirectory() as tmp_dir:
            # out_dim = os.path.join(self.output, self.condensed_name + ".dim")  # DEBUG OPTION
            out_dim = os.path.join(tmp_dir, self.condensed_name + ".dim")

            # Run GPT graph
            processed_bands = self._run_s3_gpt_cli(out_dim, resolution)

            # Save all processed bands and quality flags into GeoTIFFs
            for snap_band_name in processed_bands:
                # Get standard band names
                band_name = self._get_band_filename(snap_band_name)

                # Remove tif if already existing
                # (if we are here, sth has failed when creating them, so delete them all)
                out_tif = os.path.join(self.output, band_name + ".tif")
                if os.path.isfile(out_tif):
                    files.remove(out_tif)

                # Convert to geotiffs and set no data with only keeping the first band
                arr, meta = rasters.read(rasters.get_dim_img_path(out_dim, snap_band_name))
                nodata = self._snap_no_data if meta["dtype"] == float else self.nodata
                rasters.write(arr, out_tif, meta, nodata=nodata)

        # Get the wanted bands (not the quality flags here !)
        for band in processed_bands:
            filename = self._get_band_filename(band)
            if "exception" not in filename:
                out_tif = os.path.join(self.output, filename + ".tif")
                if not os.path.isfile(out_tif):
                    raise FileNotFoundError(f"Error when processing S3 bands with SNAP. Couldn't find {out_tif}")

                # Quality flags will crash here
                try:
                    band_paths[self._get_band_from_filename(filename)] = out_tif
                except ValueError:
                    pass

        return band_paths

    def _run_s3_gpt_cli(self, out_dim: str, resolution: float = None) -> list:
        """
        Construct GPT command line to reproject S3 images and quality flags

        Args:
            out_dim (str): Out DIMAP name
            resolution (float): Resolution

        Returns:
            list: Processed band name
        """
        # Default resolution
        def_res = os.environ.get(S3_DEF_RES, self.resolution)

        # Construct GPT graph
        graph_path = os.path.join(utils.get_data_dir(), "preprocess_s3.xml")
        snap_bands = ",".join([self._get_snap_band_name(band)
                               for band, band_nb in self.band_names.items() if band_nb])
        if self._instrument_name == S3Instrument.OLCI:
            sensor = "OLCI"
            fmt = "Sen3"
            snap_bands += ",quality_flags"
        else:
            sensor = "SLSTR_500m"
            fmt = "Sen3_SLSTRL1B_500m"
            exception_bands = ",".join([self._get_slstr_quality_flags_name(band)
                                        for band, band_nb in self.band_names.items() if band_nb])
            snap_bands += f",{exception_bands},cloud_an,cloud_in"

        # Run GPT graph
        cmd_list = snap.get_gpt_cli(graph_path, [f'-Pin={strings.to_cmd_string(self.path)}',
                                                 f'-Pbands={snap_bands}',
                                                 f'-Psensor={sensor}',
                                                 f'-Pformat={fmt}',
                                                 f'-Pno_data={self._snap_no_data}',
                                                 f'-Pres_m={resolution if resolution else def_res}',
                                                 f'-Pout={strings.to_cmd_string(out_dim)}'],
                                    display_snap_opt=LOGGER.level == logging.DEBUG)
        LOGGER.debug("Converting %s", self.name)
        misc.run_cli(cmd_list)

        return snap_bands.split(",")

    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile, managing the case with not orthorectified bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> prod.utm_extent()
                                                    geometry
        0  POLYGON ((1488846.028 6121896.451, 1488846.028...
        ```

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        try:
            extent = super().extent()

        except (FileNotFoundError, TypeError) as ex:
            def get_min_max(substr: str, subdatasets: list) -> (float, float):
                """
                Get min/max of a subdataset array
                Args:
                    substr: Substring to identfy the subdataset
                    subdatasets: List of subdatasets

                Returns:
                    float, float: min/max of the subdataset
                """
                path = [path for path in subdatasets if substr in path][0]
                with rasterio.open(path, "r") as sub_ds:
                    # Open the 4 corners of the array
                    height = sub_ds.height
                    width = sub_ds.width
                    scales = sub_ds.scales
                    pt1 = sub_ds.read(1, window=Window(0, 0, 1, 1)) * scales
                    pt2 = sub_ds.read(1, window=Window(width - 1, 0, width, 1)) * scales
                    pt3 = sub_ds.read(1, window=Window(0, height - 1, 1, height)) * scales
                    pt4 = sub_ds.read(1, window=Window(width - 1, height - 1, width, height)) * scales
                    pt_list = [pt1, pt2, pt3, pt4]

                    # Return min and max
                    return np.min(pt_list), np.max(pt_list)

            if self.product_type == S3ProductType.OLCI_EFR:
                # Open geodetic_an.nc
                geom_file = os.path.join(self.path, "geo_coordinates.nc")  # Only use nadir files

                with rasterio.open(geom_file, "r") as geom_ds:
                    lat_min, lat_max = get_min_max("latitude", geom_ds.subdatasets)
                    lon_min, lon_max = get_min_max("longitude", geom_ds.subdatasets)

            elif self.product_type == S3ProductType.SLSTR_RBT:
                # Open geodetic_an.nc
                geom_file = os.path.join(self.path, "geodetic_an.nc")  # Only use nadir files

                with rasterio.open(geom_file, "r") as geom_ds:
                    lat_min, lat_max = get_min_max("latitude_an", geom_ds.subdatasets)
                    lon_min, lon_max = get_min_max("longitude_an", geom_ds.subdatasets)
            else:
                raise InvalidTypeError(f"Invalid products type {self.product_type}") from ex

            # Create wgs84 extent (left, bottom, right, top)
            extent_wgs84 = gpd.GeoDataFrame(geometry=[vectors.from_bounds_to_polygon(lon_min,
                                                                                     lat_min,
                                                                                     lon_max,
                                                                                     lat_max)],
                                            crs=vectors.WGS84)

            # Get upper-left corner and deduce UTM proj from it
            utm = vectors.corresponding_utm_projection(extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy)
            extent = extent_wgs84.to_crs(utm)

        return extent

    def _get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile]_{product_type}).

        Returns:
            str: Condensed S2 name
        """
        return f"{self.get_datetime()}_S3_{self.product_type.name}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> prod.get_mean_sun_angles()
        (78.55043955912154, 31.172127033319388)
        ```

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        if self._data_type == S3DataTypes.EFR:
            geom_file = os.path.join(self.path, "tie_geometries.nc")
            sun_az = "SAA"
            sun_ze = "SZA"
        elif self._data_type == S3DataTypes.RBT:
            geom_file = os.path.join(self.path, "geometry_tn.nc")  # Only use nadir files
            sun_az = "solar_azimuth_tn"
            sun_ze = "solar_zenith_tn"
        else:
            raise InvalidTypeError(f"Unknown/Unsupported data type for Sentinel-3 data: {self._data_type}")

        # Open file
        if os.path.isfile(geom_file):
            # Bug pylint with netCDF4
            # pylint: disable=E1101
            netcdf_ds = netCDF4.Dataset(geom_file)

            # Get variables
            sun_az_var = netcdf_ds.variables[sun_az]
            sun_ze_var = netcdf_ds.variables[sun_ze]

            # Get sun angles as the mean of whole arrays
            azimuth_angle = float(np.mean(sun_az_var[:]))
            zenith_angle = float(np.mean(sun_ze_var[:]))

            # Close dataset
            netcdf_ds.close()
        else:
            raise InvalidProductError(f"Geometry file {geom_file} not found")

        return azimuth_angle, zenith_angle

    def read_mtd(self) -> (etree._Element, str):
        """
        Read metadata and outputs the metadata XML root and its namespace

        ```python
        >>> from eoreader.reader import Reader
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> prod.read_mtd()
        (<Element level1Product at 0x1b845b7ab88>, '')
        ```

        Returns:
            (etree._Element, str): Metadata XML root and its namespace
        """
        raise NotImplementedError("Sentinel-3 products don't have XML metadata. "
                                  "Please check directly into NetCDF files")

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        - SLSTR does
        - OLCI does not provide any cloud mask
        ```
        """
        if self._instrument_name == S3Instrument.SLSTR and band in [RAW_CLOUDS, ALL_CLOUDS, CLOUDS, CIRRUS]:
            has_band = True
        else:
            has_band = False

        return has_band

    def _load_clouds(self,
                     band_list: Union[list, BandNames],
                     resolution: float = None,
                     size: Union[list, tuple] = None) -> (dict, dict):
        """
        Load cloud files as numpy arrays with the same resolution (and same metadata).

        Read S3 SLSTR clouds from the flags file:cloud netcdf file.
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/cloud-identification

        bit_id  flag_masks (ushort)     flag_meanings
        ===     ===                     ===
        0       1US                     visible
        1       2US                     1.37_threshold
        2       4US                     1.6_small_histogram
        3       8US                     1.6_large_histogram
        4       16US                    2.25_small_histogram
        5       32US                    2.25_large_histogram
        6       64US                    11_spatial_coherence
        7       128US                   gross_cloud
        8       256US                   thin_cirrus
        9       512US                   medium_high
        10      1024US                  fog_low_stratus
        11      2048US                  11_12_view_difference
        12      4096US                  3.7_11_view_difference
        13      8192US                  thermal_histogram
        14      16384US                 spare
        15      32768US                 spare

        Args:
            band_list (Union[list, BandNames]): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict, dict: Dictionary {band_name, band_array} and the products metadata
                        (supposed to be the same for all bands)
        """
        bands = {}
        meta = {}

        if band_list:
            if self._instrument_name == S3Instrument.OLCI:
                raise InvalidTypeError("Sentinel-3 OLCI sensor does not provide any cloud file.")

            all_ids = list(np.arange(0, 14))
            cir_id = 8
            cloud_ids = [id for id in all_ids if id != cir_id]

            try:
                cloud_path = files.get_file_in_dir(self.output, "cloud_RAD.tif")
            except FileNotFoundError:
                self._preprocess_s3(resolution)
                cloud_path = files.get_file_in_dir(self.output, "cloud_RAD.tif")

            if not cloud_path:
                raise FileNotFoundError(f'Unable to find the cloud mask for {self.path}')

            # Open cloud file
            clouds_array, meta = rasters.read(cloud_path,
                                              resolution=resolution,
                                              size=size,
                                              resampling=Resampling.nearest)

            # Get nodata mask
            nodata = np.where(clouds_array == 65535, 1, 0)

            for band in band_list:
                if band == ALL_CLOUDS:
                    bands[band] = self._create_mask(clouds_array, all_ids, nodata)
                elif band == CLOUDS:
                    bands[band] = self._create_mask(clouds_array, cloud_ids, nodata)
                elif band == CIRRUS:
                    bands[band] = self._create_mask(clouds_array, cir_id, nodata)
                elif band == RAW_CLOUDS:
                    bands[band] = clouds_array
                else:
                    raise InvalidTypeError(f"Non existing cloud band for Sentinel-3 SLSTR: {band}")

        return bands, meta

    def _create_mask(self,
                     bit_array: np.ma.masked_array,
                     bit_ids: Union[int, list],
                     nodata: np.ndarray) -> np.ma.masked_array:
        """
        Create a mask masked array (uint8) from a bit array, bit IDs and a nodata mask.

        Args:
            bit_array (np.ma.masked_array): Conditional array
            bit_ids (Union[int, list]): Bit IDs
            nodata (np.ndarray): Nodata mask

        Returns:
            np.ma.masked_array: Mask masked array

        """
        if not isinstance(bit_ids, list):
            bit_ids = [bit_ids]
        conds = rasters.read_bit_array(bit_array, bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every conditions (bitwise or)

        cond_arr = np.where(cond, self._mask_true, self._mask_false)
        cond_arr, _ = rasters.sieve(cond_arr, {"dtype": cond_arr.dtype}, 10)

        mask = np.ma.masked_array(cond_arr,
                                  mask=nodata,
                                  fill_value=self._mask_nodata,
                                  dtype=np.uint8)

        # Fill nodata pixels
        mask[nodata == 1] = self._mask_nodata

        return mask
