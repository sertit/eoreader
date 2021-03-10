""" Sentinel-3 products """

import logging
import os
import tempfile
from datetime import datetime
from enum import unique
from typing import Union

import netCDF4
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.enums import Resampling
from rasterio.windows import Window
from sertit import rasters, vectors, files, strings, misc, snap
from sertit.misc import ListEnum

from eoreader import utils
from eoreader.exceptions import InvalidTypeError, InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)
BT_BANDS = [obn.MIR, obn.TIR_1, obn.TIR_2]
S3_DEF_RES = "EOREADER_S3_DEFAULT_RES"


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
        self.instrument_name = None
        self.data_type = None
        super().__init__(product_path, archive_path, output_path)  # Order is important here
        self.snap_no_data = -1
        self.condensed_name = self._get_condensed_name()

    def _set_product_type(self) -> None:
        """ Get products type """
        # Product type
        if self.name[7] != "1":
            raise InvalidTypeError("Only L1 products are used for Sentinel-3 data.")

        if "OL" in self.name:
            # Instrument
            self.instrument_name = S3Instrument.OLCI

            # Data type
            if S3DataTypes.EFR.value in self.name:
                self.data_type = S3DataTypes.EFR
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
            self.instrument_name = S3Instrument.SLSTR

            # Data type
            if S3DataTypes.RBT.value in self.name:
                self.data_type = S3DataTypes.RBT
                self.product_type = S3ProductType.SLSTR_RBT
            else:
                raise InvalidTypeError("Only RBT data type is used for Sentinel-3 SLSTR data.")

            # Bands
            self.band_names.map_bands({
                obn.GREEN: '1',  # radiance, 500m
                obn.RED: '2',  # radiance, 500m
                obn.NIR: '3',  # radiance, 500m
                obn.NNIR: '3',  # radiance, 500m
                obn.CIRRUS: '4',  # radiance, 500m
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
            raise InvalidProductError(f"Non existing band ({band.name}) for S3-{self.data_type.name} products")

        # Get band name
        if self.data_type == S3DataTypes.EFR:
            snap_bn = f"Oa{band_nb}_reflectance"  # Converted into reflectance previously in the graph
        elif self.data_type == S3DataTypes.RBT:
            if band in BT_BANDS:
                snap_bn = f"S{band_nb}_BT_in"
            else:
                snap_bn = f"S{band_nb}_reflectance_an"  # Conv into reflectance previously in the graph
        else:
            raise InvalidTypeError(f"Unknown data type for Sentinel-3 data: {self.data_type}")

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
        if self.data_type == S3DataTypes.EFR:
            band_nb = band_filename[2:4]
        elif self.data_type == S3DataTypes.RBT:
            band_nb = band_filename[1]
        else:
            raise InvalidTypeError(f"Invalid Sentinel-3 datatype: {self.data_type}")

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
            raise InvalidProductError(f"Non existing band ({band.name}) for S3-{self.data_type.name} products")

        # Get quality flag name
        if self.data_type == S3DataTypes.RBT:
            snap_bn = f"S{band_nb}_exception_{'i' if band in BT_BANDS else 'a'}n"
        else:
            raise InvalidTypeError(f"This function only works for Sentinel-3 SLSTR data: {self.data_type}")

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
        if self.data_type == S3DataTypes.RBT:
            snap_name = snap_name[:-3]

        return snap_name

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        **WARNING**: If not existing, this function will orthorectify your bands !

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
    def _read_band(self, dataset, x_res: float = None, y_res: float = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset.

        **WARNING**: Invalid pixels are not managed here, please consider using `load` or use it at your own risk!

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
        >>> prod = Reader().open(path)
        >>> with rasterio.open(prod.get_default_band_path()) as dst:
        >>>     band, meta = prod.read_band(dst, x_res=500, y_res=500)  # You can create not square pixels here
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
            x_res (float): Resolution for X axis
            y_res (float): Resolution for Y axis
        Returns:
            np.ma.masked_array, dict: Radar band, saved as float 32 and its metadata

        """
        # Read band
        return rasters.read(dataset, [x_res, y_res], Resampling.bilinear)

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(self,
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
        if self.instrument_name == S3Instrument.OLCI:
            band_arr_mask, meta = self._manage_invalid_pixels_olci(band_arr, band, meta, res_x, res_y)
        else:
            band_arr_mask, meta = self._manage_invalid_pixels_slstr(band_arr, band, meta, res_x, res_y)

        return band_arr_mask, meta

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels_olci(self,
                                    band_arr: np.ma.masked_array,
                                    band: obn,
                                    meta: dict,
                                    res_x: float = None,
                                    res_y: float = None) -> (np.ma.masked_array, dict):
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
            res_x (float): Resolution for X axis
            res_y (float): Resolution for Y axis

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

        with rasterio.open(qual_flags_path) as qual_dst:
            # Nearest to keep the flags
            qual_arr, _ = rasters.read(qual_dst, [res_x, res_y], Resampling.nearest, masked=False)
            invalid, sat = rasters.read_bit_array(qual_arr, [invalid_id, sat_band_id])

        # Get nodata mask
        no_data = np.where(band_arr == self.snap_no_data, nodata_true, nodata_false)

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
                                     res_x: float = None,
                                     res_y: float = None) -> (np.ma.masked_array, dict):
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        ISP_absent pixel_absent not_decompressed no_signal saturation invalid_radiance no_parameters unfilled_pixel"

        Args:
            band_arr (np.ma.masked_array): Band array loaded
            band (obn): Band name as an OpticalBandNames
            meta (dict): Band metadata from rasterio
            res_x (float): Resolution for X axis
            res_y (float): Resolution for Y axis

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

        with rasterio.open(qual_flags_path) as qual_dst:
            # Nearest to keep the flags
            qual_arr, _ = rasters.read(qual_dst, [res_x, res_y], Resampling.nearest, masked=False)

            # Set no data for everything (except ISP) that caused an exception
            exception = np.where(qual_arr > 2, nodata_true, nodata_false)

        # Get nodata mask
        no_data = np.where(band_arr.data == self.snap_no_data, nodata_true, nodata_false)

        # Combine masks
        mask = no_data | exception

        # DO not set 0 to epsilons as they are a part of the
        return self._create_band_masked_array(band_arr, mask, meta)

    def _load_bands(self, band_list: [list, BandNames], resolution: float = 20) -> (dict, dict):
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
        band_arrays, meta = self._open_bands(band_paths, resolution)

        return band_arrays, meta

    def _preprocess_s3(self, resolution: float):
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
            # out_dim = os.path.join(self.output, self.condensed_name + ".dim")  DEBUG OPTION
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
                with rasterio.open(rasters.get_dim_img_path(out_dim, snap_band_name)) as dim_ds:
                    nodata = self.snap_no_data if dim_ds.meta["dtype"] == float else self.nodata
                    rasters.write(dim_ds.read(masked=True), out_tif, dim_ds.meta, nodata=nodata)

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

    def _run_s3_gpt_cli(self, out_dim: str, resolution: float) -> list:
        """
        Construct GPT command line to reproject S3 images and quality flags

        Args:
            out_dim (str): Out DIMAP name
            resolution (float): Resolution

        Returns:
            list: Processed band name
        """
        # Construct GPT graph
        graph_path = os.path.join(utils.get_data_dir(), "gpt_graphs", "preprocess_s3.xml")
        snap_bands = ",".join([self._get_snap_band_name(band)
                               for band, band_nb in self.band_names.items() if band_nb])
        if self.instrument_name == S3Instrument.OLCI:
            sensor = "OLCI"
            fmt = "Sen3"
            snap_bands += ",quality_flags"
            def_res = os.environ.get(S3_DEF_RES, 300)
        else:
            sensor = "SLSTR_500m"
            fmt = "Sen3_SLSTRL1B_500m"
            def_res = os.environ.get(S3_DEF_RES, 500)
            exception_bands = ",".join([self._get_slstr_quality_flags_name(band)
                                        for band, band_nb in self.band_names.items() if band_nb])
            snap_bands += f",{exception_bands}"

        # Run GPT graph
        cmd_list = snap.get_gpt_cli(graph_path, [f'-Pin={strings.to_cmd_string(self.path)}',
                                                 f'-Pbands={snap_bands}',
                                                 f'-Psensor={sensor}',
                                                 f'-Pformat={fmt}',
                                                 f'-Pno_data={self.snap_no_data}',
                                                 f'-Pres_m={resolution if resolution else def_res}',
                                                 f'-Pout={strings.to_cmd_string(out_dim)}'],
                                    display_snap_opt=LOGGER.level == logging.DEBUG)
        LOGGER.debug("Converting %s", self.name)
        misc.run_cli(cmd_list)

        return snap_bands.split(",")

    def utm_extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile, managing the case with not orthorectified bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.utm_extent()
                                                    geometry
        0  POLYGON ((1488846.028 6121896.451, 1488846.028...
        ```

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        try:
            extent = super().utm_extent()

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
        >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
        >>> prod = Reader().open(path)
        >>> prod.get_mean_sun_angles()
        (78.55043955912154, 31.172127033319388)
        ```

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        if self.data_type == S3DataTypes.EFR:
            geom_file = os.path.join(self.path, "tie_geometries.nc")
            sun_az = "SAA"
            sun_ze = "SZA"
        elif self.data_type == S3DataTypes.RBT:
            geom_file = os.path.join(self.path, "geometry_tn.nc")  # Only use nadir files
            sun_az = "solar_azimuth_tn"
            sun_ze = "solar_zenith_tn"
        else:
            raise InvalidTypeError(f"Unknown/Unsupported data type for Sentinel-3 data: {self.data_type}")

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
