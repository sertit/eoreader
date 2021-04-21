""" Sentinel-2 products """

import glob
import logging
import os
import zipfile
import re
from datetime import datetime
from enum import unique
from typing import Union

from lxml import etree
import numpy as np
import geopandas as gpd
from rasterio import features, MemoryFile
from rasterio.enums import Resampling
from sertit import files
from sertit import rasters
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.bands.bands import OpticalBandNames as obn, BandNames
from eoreader.bands.alias import ALL_CLOUDS, RAW_CLOUDS, CLOUDS, SHADOWS, CIRRUS
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.products.product import path_or_dst
from eoreader.utils import EOREADER_NAME, DATETIME_FMT

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S2ProductType(ListEnum):
    """ Sentinel-2 products types (L1C or L2A) """
    L1C = "L1C"
    L2A = "L2A"


BAND_DIR_NAMES = {S2ProductType.L1C: 'IMG_DATA',
                  S2ProductType.L2A: {'01': ['R60m'],
                                      '02': ['R10m', 'R20m', 'R60m'],
                                      '03': ['R10m', 'R20m', 'R60m'],
                                      '04': ['R10m', 'R20m', 'R60m'],
                                      '05': ['R20m', 'R60m'],
                                      '06': ['R20m', 'R60m'],
                                      '07': ['R20m', 'R60m'],
                                      '08': ['R10m'],
                                      '8A': ['R20m', 'R60m'],
                                      '09': ['R60m'],
                                      '11': ['R20m', 'R60m'],
                                      '12': ['R20m', 'R60m']}}


class S2Product(OpticalProduct):
    """
    Class of Sentinel-2 Products

    You can use directly the .zip file
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
        return self.split_name[-2]

    def _set_product_type(self) -> None:
        """ Get products type """
        if "MSIL2A" in self.name:
            self.product_type = S2ProductType.L2A
            self.band_names.map_bands({
                obn.CA: '01',
                obn.BLUE: '02',
                obn.GREEN: '03',
                obn.RED: '04',
                obn.VRE_1: '05',
                obn.VRE_2: '06',
                obn.VRE_3: '07',
                obn.NIR: '08',
                obn.NARROW_NIR: '8A',
                obn.WV: '09',
                obn.SWIR_1: '11',
                obn.SWIR_2: '12'
            })
        elif "MSIL1C" in self.name:
            self.product_type = S2ProductType.L1C
            self.band_names.map_bands({
                obn.CA: '01',
                obn.BLUE: '02',
                obn.GREEN: '03',
                obn.RED: '04',
                obn.VRE_1: '05',
                obn.VRE_2: '06',
                obn.VRE_3: '07',
                obn.NIR: '08',
                obn.NARROW_NIR: '8A',
                obn.WV: '09',
                obn.SWIR_CIRRUS: '10',
                obn.SWIR_1: '11',
                obn.SWIR_2: '12'
            })
        else:
            raise InvalidProductError(f"Invalid Sentinel-2 name: {self.name}")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
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

        date = self.split_name[2]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def _get_res_band_folder(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.
        (IMG_DATA for L1C, IMG_DATA/Rx0m for L2A)

        Args:
            band_list (list): Wanted bands (listed as 01, 02...)
            resolution (float): Band resolution for Sentinel-2 products {R10m, R20m, R60m}.
                                The wanted bands will be chosen in this proper folder.

        Returns:
            dict: Dictionary containing the folder path for each queried band
        """
        # Open the band directory names
        s2_bands_folder = {}

        # Manage L2A
        band_dir = BAND_DIR_NAMES[self.product_type]
        for band in band_list:
            assert band in obn
            band_nb = self.band_names[band]
            if band_nb is None:
                raise InvalidProductError(f"Non existing band ({band.name}) for S2-{self.product_type.name} products")

            # If L2A products, we care about the resolution
            if self.product_type == S2ProductType.L2A:
                # If we got a true S2 resolution, open the corresponding band
                if resolution and f"R{resolution}m" in band_dir[band_nb]:
                    dir_name = f"R{resolution}m"

                # Else open the first one, it will be resampled when the ban will be read
                else:
                    dir_name = band_dir[band_nb][0]
            # If L1C, we do not
            else:
                dir_name = band_dir

            if self.is_archived:
                # Open the zip file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    # Get the band folder (use dirname is the first of the list is a band)
                    s2_bands_folder[band] = [os.path.dirname(f.filename) for f in zip_ds.filelist
                                             if dir_name in f.filename][0]
            else:
                # Search for the name of the folder into the S2 products
                for root, folders, _ in os.walk(os.path.abspath(self.path)):
                    for folder in folders:
                        if folder == dir_name:
                            s2_bands_folder[band] = os.path.join(root, folder)

        for band in band_list:
            if band not in s2_bands_folder:
                raise InvalidProductError(f"Band folder for band {band.value} not found in {self.path}")

        return s2_bands_folder

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
        band_folders = self._get_res_band_folder(band_list, resolution)
        band_paths = {}
        for band in band_list:
            try:
                if self.is_archived:
                    band_paths[band] = files.get_archived_rio_path(self.path, f".*_B{self.band_names[band]}.*.jp2")
                else:
                    band_paths[band] = files.get_file_in_dir(band_folders[band],
                                                             "_B" + self.band_names[band],
                                                             extension="jp2")
            except (FileNotFoundError, IndexError) as ex:
                raise InvalidProductError(f"Non existing {band} ({self.band_names[band]}) band for {self.path}") from ex

        return band_paths

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
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> band, meta = prod._read_band(prod.get_default_band_path(), resolution=20)
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

        # Get resolution
        coeff = 1 / 10000. if dataset.meta['dtype'] == 'uint16' else 1

        # Compute the correct radiometry of the band
        band = band.astype(np.float32) * coeff
        dst_meta["dtype"] = np.float32

        return band, dst_meta

    def open_mask(self, mask_str: str, band: Union[obn, str]) -> gpd.GeoDataFrame:
        """
        Open S2 mask (GML files stored in QI_DATA) as `gpd.GeoDataFrame`.

        Masks than can be called that way are:

        - `TECQUA`: Technical quality mask
        - `SATURA`: Saturated Pixels
        - `NODATA`: Pixel nodata (inside the detectors)
        - `DETFOO`: Detectors footprint -> used to process nodata outside the detectors
        - `DEFECT`: Defective pixels
        - `CLOUDS`, **only with `00` as a band !**

        ```python
        >>> from eoreader.reader import Reader
        >>> from eoreader.bands.alias import *
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod.open_mask("NODATA", GREEN)
        Empty GeoDataFrame
        Columns: [geometry]
        Index: []
        >>> prod.open_mask("SATURA", GREEN)
        Empty GeoDataFrame
        Columns: [geometry]
        Index: []
        >>> prod.open_mask("DETFOO", GREEN)
                                gml_id  ...                                           geometry
        0  detector_footprint-B03-02-0  ...  POLYGON Z ((199980.000 4500000.000 0.000, 1999...
        1  detector_footprint-B03-03-1  ...  POLYGON Z ((222570.000 4500000.000 0.000, 2225...
        2  detector_footprint-B03-05-2  ...  POLYGON Z ((273050.000 4500000.000 0.000, 2730...
        3  detector_footprint-B03-07-3  ...  POLYGON Z ((309770.000 4453710.000 0.000, 3097...
        4  detector_footprint-B03-04-4  ...  POLYGON Z ((248080.000 4500000.000 0.000, 2480...
        5  detector_footprint-B03-06-5  ...  POLYGON Z ((297980.000 4500000.000 0.000, 2979...
        [6 rows x 3 columns]
        ```

        Args:
            mask_str (str): Mask name, such as DEFECT, NODATA, SATURA...
            band (Union[obn, str]): Band number as an OpticalBandNames or str (for clouds: 00)

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        # Check inputs
        assert mask_str in ['DEFECT', 'DETFOO', 'NODATA', 'SATURA', 'TECQUA', 'CLOUDS']
        if mask_str == "CLOUDS":
            band = "00"

        def _open_mask(fct, *args, **kwargs):
            # Read the GML file
            try:
                # Discard some weird error concerning a NULL pointer that outputs a ValueError (as we already except it)
                fiona_logger = logging.getLogger("fiona._env")
                fiona_logger.setLevel(logging.CRITICAL)

                # Read mask
                mask = fct(*args, **kwargs)

                # Set fiona logger back to what it was
                fiona_logger.setLevel(logging.INFO)
            except ValueError:
                mask = gpd.GeoDataFrame(geometry=[], crs=self.crs())

            return mask

        # Get QI_DATA path
        if isinstance(band, obn):
            band_name = self.band_names[band]
        else:
            band_name = band

        if self.is_archived:
            # Open the zip file
            # WE DON'T KNOW WHY BUT DO NOT USE files.read_archived_vector HERE !!!
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*GRANULE.*QI_DATA.*MSK_{mask_str}_B{band_name}.gml")
                with zip_ds.open(list(filter(regex.match, filenames))[0]) as mask_path:
                    mask = _open_mask(gpd.read_file,
                                      mask_path)

            # mask = _open_mask(files.read_archived_vector,
            #                   self.path,
            #                   f".*GRANULE.*QI_DATA.*MSK_{mask_str}_B{band_name}\.gml")
        else:
            qi_data_path = os.path.join(self.path, 'GRANULE', '*', 'QI_DATA')

            # Get mask path
            mask_path = files.get_file_in_dir(qi_data_path,
                                              f"MSK_{mask_str}_B{band_name}.gml",
                                              exact_name=True)

            mask = _open_mask(gpd.read_file,
                              mask_path)

        return mask

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
        See there: https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf

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

        # Get detector footprint to deduce the outside nodata
        nodata_det = self.open_mask("DETFOO", band)  # Detector nodata, -> pixels that are outside of the detectors

        # Rasterize nodata
        mask = features.rasterize(nodata_det.geometry,
                                  out_shape=(meta["width"], meta["height"]),
                                  fill=nodata_true,  # Outside detector = nodata
                                  default_value=nodata_false,  # Inside detector = acceptable value
                                  transform=meta["transform"],
                                  dtype=np.uint8)

        #  Load masks and merge them into the nodata
        nodata_pix = self.open_mask("NODATA", band)  # Pixel nodata, not pixels that are outside of the detectors !!!
        if len(nodata_pix) > 0:
            # Discard pixels corrected during crosstalk
            nodata_pix = nodata_pix[nodata_pix.gml_id == "QT_NODATA_PIXELS"]
        nodata_pix.append(self.open_mask("DEFECT", band))
        nodata_pix.append(self.open_mask("SATURA", band))

        # Technical quality mask
        tecqua = self.open_mask("TECQUA", band)
        if len(tecqua) > 0:
            # Do not take into account ancillary data
            tecqua = tecqua[tecqua.gml_id.isin(["MSI_LOST", "MSI_DEG"])]
        nodata_pix.append(tecqua)

        if len(nodata_pix) > 0:
            # Rasterize mask
            mask_pix = features.rasterize(nodata_pix.geometry,
                                          out_shape=(meta["width"], meta["height"]),
                                          fill=nodata_false,  # OK pixels = OK value
                                          default_value=nodata_true,  # Discarded pixels = nodata
                                          transform=meta["transform"],
                                          dtype=np.uint8)

            mask[mask_pix] = nodata_true

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

        band_paths = self.get_band_paths(band_list, resolution)

        # Open bands and get array (resampled if needed)
        band_arrays, meta = self._open_bands(band_paths, resolution=resolution, size=size)
        meta["driver"] = "GTiff"

        return band_arrays, meta

    def _get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile}_{product_type}_{processed_hours}).

        Returns:
            str: Condensed S2 name
        """
        # Used to make the difference between 2 products acquired on the same tile at the same date but cut differently
        proc_time = self.split_name[-1].split("T")[-1]
        return f"{self.get_datetime()}_S2_{self.tile_name}_{self.product_type.value}_{proc_time}"

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
        # Init angles
        zenith_angle = None
        azimuth_angle = None

        # Read metadata
        root, namespace = self.read_mtd()

        # Open zenith and azimuth angle
        for element in root:
            if element.tag == namespace + 'Geometric_Info':
                for node in element:
                    if node.tag == 'Tile_Angles':
                        mean_sun_angles = node.find('Mean_Sun_Angle')
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
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> prod = Reader().open(path)
        >>> prod.read_mtd()
        (<Element {https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd}Level-2A_Tile_ID at ...>,
        '{https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd}')

        ```

        Returns:
            (etree._Element, str): Metadata XML root and its namespace
        """
        # Get MTD XML file
        if self.is_archived:
            root = files.read_archived_xml(self.path, ".*GRANULE.*\.xml")
        else:
            # Open metadata file
            try:
                mtd_file = glob.glob(os.path.join(self.path, "GRANULE", "*", "*.xml"))[0]

                # pylint: disable=I1101:
                # Module 'lxml.etree' has no 'parse' member, but source is unavailable.
                xml_tree = etree.parse(mtd_file)
                root = xml_tree.getroot()
            except IndexError as ex:
                raise InvalidProductError(f"Metadata file not found in {self.path}") from ex

        # Get namespace
        idx = root.tag.rindex("}")
        namespace = root.tag[:idx + 1]

        return root, namespace

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks
        """
        if band == SHADOWS:
            has_band = False
        else:
            has_band = True
        return has_band

    def _load_clouds(self,
                     band_list: Union[list, BandNames],
                     resolution: float = None,
                     size: Union[list, tuple] = None) -> (dict, dict):
        """
        Load cloud files as numpy arrays with the same resolution (and same metadata).

        Read S2 cloud mask .GML files (both valid for L2A and L1C products).
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks

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
            def_band = self.get_default_band()
            cloud_vec = self.open_mask('CLOUDS', "00")

            # Open a bands to mask it
            band, meta = self.load(def_band, resolution=resolution)
            nodata = np.where(band == meta["nodata"], 1, 0)

            with MemoryFile().open(**meta) as mem_ds:
                # Write band into dst
                mem_ds.write(band[def_band])

                for band in band_list:
                    if band == ALL_CLOUDS:
                        bands[band] = self._rasterize(mem_ds, cloud_vec, nodata)
                    elif band == CIRRUS:
                        try:
                            cirrus = cloud_vec[cloud_vec.maskType == "CIRRUS"]
                        except AttributeError:
                            # No masktype -> empty
                            cirrus = gpd.GeoDataFrame(geometry=[], crs=cloud_vec.crs)
                        bands[band] = self._rasterize(mem_ds, cirrus, nodata)
                    elif band == CLOUDS:
                        try:
                            clouds = cloud_vec[cloud_vec.maskType == "OPAQUE"]
                        except AttributeError:
                            # No masktype -> empty
                            clouds = gpd.GeoDataFrame(geometry=[], crs=cloud_vec.crs)
                        bands[band] = self._rasterize(mem_ds, clouds, nodata)
                    elif band == RAW_CLOUDS:
                        bands[band] = self._rasterize(mem_ds, cloud_vec, nodata)
                    else:
                        raise InvalidTypeError(f"Non existing cloud band for Sentinel-2: {band}")

        return bands, meta

    def _rasterize(self, mem_ds, geometry: gpd.GeoDataFrame, nodata: np.ndarray) -> np.ma.masked_array:
        """
        Rasterize a vector on a memory dataset

        Args:
            mem_ds: Memory file
            geometry (gpd.GeoDataFrame): Geometry to rasterize
            nodata (np.ndarray): Nodata mask

        Returns:

        """
        if not geometry.empty:
            # Just in case
            if geometry.crs != mem_ds.crs:
                geometry = geometry.to_crs(mem_ds.crs)

            # Mask the file -> do not use rasterize to get a correct nodata mask !
            rstrzd, _ = rasters.mask(mem_ds, geometry.geometry, nodata=mem_ds.nodata)

            # Get cloud raster
            mask = np.ma.masked_array(np.where(rstrzd > 0, self._mask_true, self._mask_false),
                                      mask=nodata,
                                      fill_value=self._mask_nodata,
                                      dtype=np.uint8)
        else:
            # If empty geometry, just
            mask = np.ma.masked_array(np.full(shape=(mem_ds.count, mem_ds.height, mem_ds.width),
                                              dtype=np.uint8,
                                              fill_value=self._mask_false),
                                      mask=nodata,
                                      fill_value=self._mask_nodata,
                                      dtype=np.uint8)
        return mask
