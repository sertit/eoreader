"""
Sentinel-2 Theia products
See [here](https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more information.
"""

import glob
import logging
import os
import datetime
import re
import zipfile
from typing import Union

from lxml import etree
import numpy as np
from rasterio.enums import Resampling
from sertit import files, rasters

from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.s2_product import S2ProductType
from eoreader.bands.bands import OpticalBandNames as obn, BandNames
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.products.product import path_or_dst
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)


class S2TheiaProduct(OpticalProduct):
    """
    Class of Sentinel-2 Theia Products.
    See [here](https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more information.
    """

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()
        self.needs_extraction = False

        # Post init done by the super class
        super()._post_init()

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # S2: use 20m resolution, even if we have 60m and 10m resolution
        # In the future maybe set one resolution per band ?
        return 20.

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """

        return self.split_name[3]

    def _set_product_type(self) -> None:
        """ Get products type """
        self.product_type = S2ProductType.L2A
        self.band_names.map_bands({
            obn.BLUE: '2',
            obn.GREEN: '3',
            obn.RED: '4',
            obn.VRE_1: '5',
            obn.VRE_2: '6',
            obn.VRE_3: '7',
            obn.NIR: '8',
            obn.NNIR: '8A',
            obn.SWIR_1: '11',
            obn.SWIR_2: '12'
        })

        # TODO: bands 1 and 9 are in ATB_R1 (10m) and ATB_R2 (20m)
        # B1 to be divided by 20
        # B9 to be divided by 200

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime.datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
        >>> prod = Reader().open(path)
        >>> prod.get_datetime(as_datetime=True)
        datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms
        >>> prod.get_datetime(as_datetime=False)
        '20190625T105728'
        ```

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        # 20200624-105726-971
        date = datetime.datetime.strptime(self.split_name[1], "%Y%m%d-%H%M%S-%f")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
        >>> prod = Reader().open(path)
        >>> prod.get_band_paths([GREEN, RED])
        {
            <OpticalBandNames.GREEN: 'GREEN'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
            <OpticalBandNames.RED: 'RED'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
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
            try:
                if self.is_archived:
                    # Open the zip file
                    with zipfile.ZipFile(self.path, "r") as zip_ds:
                        # Get the correct band path
                        regex = re.compile(f".*FRE_B{self.band_names[band]}.tif")
                        filenames = [f.filename for f in zip_ds.filelist]
                        band_path = list(filter(regex.match, filenames))[0]

                    # Create the zip band path (readable from rasterio)
                    band_paths[band] = f"zip+file://{self.path}!/{band_path}"
                else:
                    band_paths[band] = files.get_file_in_dir(self.path, f"FRE_B{self.band_names[band]}.tif")
            except (FileNotFoundError, IndexError) as ex:
                raise InvalidProductError(f"Non existing {band} ({self.band_names[band]}) band for {self.path}") from ex

        return band_paths

    @path_or_dst
    def _read_band(self,
                   dataset,
                   resolution: Union[tuple, list, float] = None,
                   size: Union[list, tuple] = None) -> (np.ma.masked_array, dict):
        """
        Read band from a dataset

        **WARNING**: Invalid pixels are not managed here, please consider using `load` or use it at your own risk!

        ```python
        >>> import rasterio
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
        >>> prod = Reader().open(path)
        >>> band, meta = prod._read_band(prod.get_default_band_path(), resolution=20)
        >>> band
        masked_array(
          data=[[[0.05339999869465828, ..., 0.05790000036358833]]],
          mask=[[[False, ..., False],
          fill_value=1e+20,
          dtype=float32)
        >>> meta
        {
            'driver': 'GTiff',
            'dtype': <class 'numpy.float32'>,
            'nodata': 0,
            'width': 5490,
            'height': 5490,
            'count': 1,
            'crs': CRS.from_epsg(32631),
            'transform': Affine(20.0, 0.0, 499980.0, 0.0, -20.0, 5500020.0)
        }
        ```

        Args:
            dataset (Dataset): Band dataset
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            np.ma.masked_array, dict: Radiometrically coherent band, saved as float 32 and its metadata
        """
        # Read band
        band, dst_meta = rasters.read(dataset,
                                      resolution=resolution,
                                      size=size,
                                      resampling=Resampling.bilinear)

        # Compute the correct radiometry of the band
        band = band.astype(np.float32) / 10000.
        dst_meta["dtype"] = np.float32
        dst_meta["nodata"] = 0

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
        See there:
        https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf

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

        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        theia_nodata = -1.
        no_data_mask = np.where(band == theia_nodata, nodata_true, nodata_false).astype(np.uint8)

        # Open NODATA pixels mask
        edg_mask = self.open_mask("EDG", band, resolution=resolution, size=size)

        # Open saturated pixels
        sat_mask = self.open_mask("SAT", band, resolution=resolution, size=size)

        # Combine masks
        mask = no_data_mask | edg_mask | sat_mask

        # Open defective pixels (optional mask)
        try:
            def_mask = self.open_mask("DFP", band, resolution=resolution, size=size)
            mask = mask | def_mask
        except InvalidProductError:
            pass

        # -- Merge masks
        return self._create_band_masked_array(band_arr, mask, meta)

    def open_mask(self,
                  mask_id: str,
                  band: obn,
                  resolution: float = None,
                  size: Union[list, tuple] = None) -> np.ndarray:
        """
        Get a Sentinel-2 THEIA mask path.
        See [here](https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more
        information.

        Accepted mask IDs:

        - `DFP`: Defective pixels
        - `EDG`: Nodata pixels mask
        - `SAT`: Saturated pixels mask
        - `MG2`: Geophysical mask (classification)
        - `IAB`: Mask where water vapor and TOA pixels have been interpolated
        - `CLM`: Cloud mask


        ```python
        >>> from eoreader.bands.alias import *
        >>> from eoreader.reader import Reader
        >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
        >>> prod = Reader().open(path)
        >>> prod.open_mask("CLM", GREEN)
        array([[[0, ..., 0]]], dtype=uint8)
        ```

        Args:
            mask_id: Mask ID
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ndarray: Mask array

        """
        # https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/
        # For r_1, the band order is: B2, B3, B4, B8 and for r_2: B5, B6, B7, B8a, B11, B12
        r_1 = [obn.BLUE, obn.GREEN, obn.RED, obn.NIR]
        r_2 = [obn.VRE_1, obn.VRE_2, obn.VRE_3, obn.NNIR, obn.SWIR_1, obn.SWIR_2]
        if band in r_1:
            r_x = "R1"
            bit_id = r_1.index(band)
        elif band in r_2:
            r_x = "R2"
            bit_id = r_2.index(band)
        else:
            raise InvalidProductError(f"Invalid band: {band.value}")

        mask_regex = f"*{mask_id}_{r_x}.tif"
        try:
            if self.is_archived:
                # Open the zip file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    # Get the correct band path
                    regex = re.compile(f"{mask_regex.replace('*', '.*')}")
                    filenames = [f.filename for f in zip_ds.filelist]
                    band_path = list(filter(regex.match, filenames))[0]

                # Create the zip band path (readable from rasterio)
                mask_path = f"zip+file://{self.path}!/{band_path}"
            else:
                mask_path = files.get_file_in_dir(os.path.join(self.path, "MASKS"),
                                                  mask_regex,
                                                  exact_name=True)
        except (FileNotFoundError, IndexError) as ex:
            raise InvalidProductError(f"Non existing mask {mask_regex} in {self.name}") from ex

        # Open SAT band
        sat_arr, _ = rasters.read(mask_path,
                                  resolution=resolution,
                                  size=size,
                                  resampling=Resampling.nearest,  # Nearest to keep the flags
                                  masked=False)
        sat_mask = rasters.read_bit_array(sat_arr, bit_id)

        return sat_mask

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

    def _get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile]_{product_type}).

        Returns:
            str: Condensed S2 name
        """
        return f"{self.get_datetime()}_S2THEIA_{self.tile_name}_{self.product_type.value}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
        >>> prod = Reader().open(path)
        >>> prod.get_mean_sun_angles()
        (154.554755774838, 27.5941391571236)
        ```

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Init angles
        zenith_angle = None
        azimuth_angle = None

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        for element in root:
            if element.tag == 'Geometric_Informations':
                for node in element:
                    if node.tag == 'Mean_Value_List':
                        mean_sun_angles = node.find('Sun_Angles')
                        zenith_angle = float(mean_sun_angles.findtext('ZENITH_ANGLE'))
                        azimuth_angle = float(mean_sun_angles.findtext('AZIMUTH_ANGLE'))
                        break  # Only one Mean_Sun_Angle
                break  # Only one Geometric_Info

        if not zenith_angle or not azimuth_angle:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        return azimuth_angle, zenith_angle

    def read_mtd(self) -> (etree._Element, str):
        """
        Read metadata and outputs the metadata XML root and its namespace

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
        >>> prod = Reader().open(path)
        >>> prod.read_mtd()
        (<Element Muscate_Metadata_Document at 0x252d2071e88>, '')
        ```

        Returns:
            (etree._Element, str): Metadata XML root and its namespace
        """
        # Get MTD XML file
        if self.is_archived:
            # Open the zip file
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                # Get the correct band path
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*.MTD_ALL.xml")
                xml_zip = zip_ds.read(list(filter(regex.match, filenames))[0])
                root = etree.fromstring(xml_zip)
        else:
            # Open metadata file
            try:
                mtd_xml = glob.glob(os.path.join(self.path, '*MTD_ALL.xml'))[0]

                # pylint: disable=I1101:
                # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                xml_tree = etree.parse(mtd_xml)
                root = xml_tree.getroot()
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file not found in {self.path}") from ex

        # Get namespace
        namespace = ""

        return root, namespace
