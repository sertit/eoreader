# -*- coding: utf-8 -*-
# Copyright 2021, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Landsat products """
import logging
import tarfile
from abc import abstractmethod
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from cloudpathlib import CloudPath
from lxml import etree
from lxml.builder import E
from rasterio.enums import Resampling
from sertit import files, rasters, rasters_rio
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

from eoreader import cache, cached_property, utils
from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS, SHADOWS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class LandsatProductType(ListEnum):
    """Landsat products types"""

    L1_OLCI = "OLCI"
    """OLCI Product Type, for Landsat-8 platform"""

    L1_ETM = "ETM"
    """ETM Product Type, for Landsat-7 platform"""

    L1_TM = "TM"
    """TM Product Type, for Landsat-5 and 4 platforms"""

    L1_MSS = "MSS"
    """MSS Product Type, for Landsat-5, 4, 3, 2, 1 platforms"""


@unique
class LandsatCollection(ListEnum):
    """
    Landsat collection number.
    See `here <https://www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary>`_ for more information
    """

    COL_1 = "01"
    """Collection 1"""

    COL_2 = "02"
    """Collection 2"""


class LandsatProduct(OpticalProduct):
    """
    Super Class of Landsat Products

    You can use directly the .tar file in case of collection 2 products.
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        # Private
        self._collection = None
        self._pixel_quality_id = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp)

    def _set_collection(self):
        """Set Landsat collection"""
        mtd, _ = self.read_mtd()

        # Open identifier
        try:
            col_nb = mtd.findtext(".//COLLECTION_NUMBER")
        except TypeError:
            raise InvalidProductError("COLLECTION_NUMBER not found in metadata!")

        return LandsatCollection.from_value(col_nb)

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        mtd, _ = self.read_mtd()

        # Open identifier
        try:
            name = mtd.findtext(".//LANDSAT_PRODUCT_ID")
        except TypeError:
            raise InvalidProductError("LANDSAT_PRODUCT_ID not found in metadata !")

        # Collections are not set yet
        # Collection 2 do not need to be extracted. Set True by default
        if utils.get_split_name(name)[-2] == "02":
            self.needs_extraction = False  # Fine to read .tar files
        else:
            self.needs_extraction = True  # Too slow to read directly tar.gz files

        # Post init done by the super class
        super()._pre_init()

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()
        self._collection = self._set_collection()
        if self._collection == LandsatCollection.COL_1:
            self._pixel_quality_id = "_BQA"
            self._radsat_id = "_BQA"
        else:
            self._pixel_quality_id = "_QA_PIXEL"
            self._radsat_id = "_QA_RADSAT"

        # Warning if GS or GT
        if "GS" in self.name:
            LOGGER.warning(
                "This Landsat product %s could be badly georeferenced "
                "as only systematic geometric corrections have been applied "
                "(using the spacecraft ephemeris data).",
                self.name,
            )

        # Post init done by the super class
        super()._post_init()

    def _get_path(self, band_id: str) -> Union[CloudPath, Path]:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            Union[CloudPath, Path]: band path

        """
        if self.is_archived:
            # Because of gap_mask files that have the same name structure and exists only for L7
            if self.product_type == LandsatProductType.L1_ETM:
                regex = f".*RT{band_id}.*"
            else:
                regex = f".*{band_id}.*"
            path = files.get_archived_rio_path(self.path, regex)
        else:
            path = files.get_file_in_dir(self.path, band_id, extension="TIF")

        return path

    @cached_property
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint
               index                                           geometry
            0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        Indeed, nodata pixels vary according to the band sensor footprint,
        whereas QA nodata is where at least one band has nodata.

        We chose to keep QA nodata values for the footprint in order to show where all bands are valid.

        **TL;DR: We use the QA nodata value to determine the product's footprint**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        nodata_band = self._get_path(self._pixel_quality_id)

        # Vectorize the nodata band (rasters_rio is faster)
        footprint = rasters_rio.vectorize(
            nodata_band, values=1, keep_values=False, dissolve=True
        )

        # Keep only the convex hull
        footprint.geometry = footprint.geometry.convex_hull

        return footprint

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.get_tile_name()
            '023030'

        Returns:
            str: Tile name
        """
        return self.split_name[2]

    @abstractmethod
    def _set_product_type(self) -> None:
        """Set products type"""
        raise NotImplementedError("This method should be implemented by a child class")

    def _set_mss_product_type(self, version: int) -> None:
        """Set MSS product type and map corresponding bands"""
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_MSS
            self.band_names.map_bands(
                {
                    obn.GREEN: "4" if version < 4 else "1",
                    obn.RED: "5" if version < 4 else "2",
                    obn.VRE_1: "6" if version < 4 else "3",
                    obn.VRE_2: "6" if version < 4 else "3",
                    obn.VRE_3: "6" if version < 4 else "3",
                    obn.NIR: "7" if version < 4 else "4",
                    obn.NARROW_NIR: "7" if version < 4 else "4",
                }
            )
        else:
            raise InvalidProductError("Only Landsat level 1 are managed in EOReader")

    def _set_tm_product_type(self) -> None:
        """Set TM product type and map corresponding bands"""
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_TM
            self.band_names.map_bands(
                {
                    obn.BLUE: "1",
                    obn.GREEN: "2",
                    obn.RED: "3",
                    obn.NIR: "4",
                    obn.NARROW_NIR: "4",
                    obn.SWIR_1: "5",
                    obn.SWIR_2: "7",
                    obn.TIR_1: "6",
                    obn.TIR_2: "6",
                }
            )
        else:
            raise InvalidProductError("Only Landsat level 1 are managed in EOReader")

    def _set_etm_product_type(self) -> None:
        """Set ETM product type and map corresponding bands"""
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_ETM
            self.band_names.map_bands(
                {
                    obn.BLUE: "1",
                    obn.GREEN: "2",
                    obn.RED: "3",
                    obn.NIR: "4",
                    obn.NARROW_NIR: "4",
                    obn.SWIR_1: "5",
                    obn.SWIR_2: "7",
                    obn.PAN: "8",
                    obn.TIR_1: "6_VCID_1",
                    obn.TIR_2: "6_VCID_2",
                }
            )
        else:
            raise InvalidProductError("Only Landsat level 1 are managed in EOReader")

    def _set_olci_product_type(self) -> None:
        """Set OLCI product type and map corresponding bands"""
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_OLCI
            self.band_names.map_bands(
                {
                    obn.CA: "1",
                    obn.BLUE: "2",
                    obn.GREEN: "3",
                    obn.RED: "4",
                    obn.NIR: "5",
                    obn.NARROW_NIR: "5",
                    obn.SWIR_1: "6",
                    obn.SWIR_2: "7",
                    obn.PAN: "8",
                    obn.SWIR_CIRRUS: "9",
                    obn.TIR_1: "10",
                    obn.TIR_2: "11",
                }
            )
        else:
            raise InvalidProductError("Only Landsat level 1 are managed in EOReader")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 5, 18, 16, 34, 7)
            >>> prod.get_datetime(as_datetime=False)
            '20200518T163407'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            mtd_data, _ = self._read_mtd()

            try:
                date = mtd_data.findtext(".//DATE_ACQUIRED")
                hours = mtd_data.findtext(".//SCENE_CENTER_TIME").replace('"', "")[:-3]
            except TypeError:
                raise InvalidProductError("ACQUISITION_DATE not found in metadata!")

            date = (
                f"{datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')}"
                f"T{datetime.strptime(hours, '%H:%M:%S.%f').strftime('%H%M%S')}"
            )

            if as_datetime:
                date = datetime.strptime(date, DATETIME_FMT)

        else:
            date = self.datetime
            if not as_datetime:
                date = date.strftime(DATETIME_FMT)

        return date

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        if self.name is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            try:
                name = root.findtext(".//LANDSAT_PRODUCT_ID").replace(
                    '"', ""
                )  # For txt files
            except TypeError:
                raise InvalidProductError("LANDSAT_PRODUCT_ID not found in metadata!")
        else:
            name = self.name

        return name

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <OpticalBandNames.GREEN: 'GREEN'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',
                <OpticalBandNames.RED: 'RED'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            if not self.has_band(band):
                raise InvalidProductError(
                    f"Non existing band ({band.name}) "
                    f"for Landsat-{self.product_type.name} products"
                )
            band_nb = self.band_names[band]

            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, resolution=resolution, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                try:
                    band_paths[band] = self._get_path(f"_B{band_nb}")
                except FileNotFoundError as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({band_nb}) band for {self.path}"
                    ) from ex

        return band_paths

    def _read_mtd(
        self, force_pd=False
    ) -> Tuple[Union[pd.DataFrame, etree._Element], dict]:
        """
        Read Landsat metadata as:

         - a `pandas.DataFrame` whatever its collection is (by default for collection 1)
         - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)

        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace
        Returns:
            Tuple[Union[pd.DataFrame, etree._Element], dict]:
                Metadata as a Pandas.DataFrame or as (etree._Element, dict): Metadata XML root and its namespaces
        """
        # Try with XML (we don't know what collection it is)
        try:
            # Open XML metadata
            mtd_from_path = "_MTL.xml"
            mtd_archived = "_MTL\.xml"
            mtd_data = self._read_mtd_xml(mtd_from_path, mtd_archived)
        except (InvalidProductError, FileNotFoundError):
            mtd_name = "_MTL.txt"
            if self.is_archived:
                # We need to extract the file in memory to be used with pandas
                tar_ds = tarfile.open(self.path, "r")
                info = [f.name for f in tar_ds.getmembers() if mtd_name in f.name][0]
                mtd_path = tar_ds.extractfile(info)
            else:
                # FOR COLLECTION 1 AND 2
                tar_ds = None
                try:
                    mtd_path = next(self.path.glob(f"**/*{mtd_name}"))
                except ValueError:
                    mtd_path = next(self.path.glob(f"*{mtd_name}"))

                if not mtd_path.is_file():
                    raise InvalidProductError(
                        f"No metadata file found in {self.name} !"
                    )

            # Parse
            mtd_data = pd.read_table(
                mtd_path,
                sep="\s=\s",
                names=["NAME", "value"],
                skipinitialspace=True,
                engine="python",
            )

            # Workaround an unexpected behaviour in pandas !
            if any(mtd_data.NAME == "="):
                mtd_data = pd.read_table(
                    mtd_path,
                    sep="=",
                    names=["NAME", "=", "value"],
                    usecols=[0, 2],
                    skipinitialspace=True,
                )

            # Remove useless rows
            mtd_data = mtd_data[~mtd_data["NAME"].isin(["GROUP", "END_GROUP", "END"])]

            # Set index
            mtd_data = mtd_data.set_index("NAME").T

            # Create XML
            attr_names = mtd_data.columns.to_list()
            global_attr = [
                E(str(attr), str(mtd_data[attr].iat[0])) for attr in attr_names
            ]
            mtd = E.s3_global_attributes(*global_attr)
            mtd_el = etree.fromstring(
                etree.tostring(
                    mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
                )
            )
            mtd_data = (mtd_el, {})

            # Close if needed
            if tar_ds:
                tar_ds.close()

        return mtd_data

    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            XDS_TYPE: Band xarray

        """
        # Get band name: the last number of the filename:
        # ie: 'LC08_L1TP_200030_20191218_20191226_01_T1_B1'
        if self.is_archived:
            filename = files.get_filename(str(path).split("!")[-1])
        else:
            filename = files.get_filename(path)

        if self._pixel_quality_id in filename or self._radsat_id in filename:
            band_xda = utils.read(
                path,
                resolution=resolution,
                size=size,
                resampling=Resampling.nearest,  # NEAREST TO KEEP THE FLAGS
                masked=False,
                **kwargs,
            ).astype(np.uint16)
        else:
            # Read band (call superclass generic method)
            band_xda = utils.read(
                path,
                resolution=resolution,
                size=size,
                resampling=Resampling.bilinear,
                **kwargs,
            ).astype(np.float32)

            # Convert raw bands from DN to correct reflectance
            if not filename.startswith(self.condensed_name):
                # Original band name
                band_name = filename[-1]

                # Open mtd
                mtd_data, _ = self._read_mtd()

                # Get band nb and corresponding coeff
                c_mul_str = "REFLECTANCE_MULT_BAND_" + band_name
                c_add_str = "REFLECTANCE_ADD_BAND_" + band_name

                # Get coeffs to convert DN to reflectance
                try:
                    c_mul = float(mtd_data.findtext(f".//{c_mul_str}"))
                    c_add = float(mtd_data.findtext(f".//{c_add_str}"))
                except TypeError:
                    raise InvalidProductError("ACQUISITION_DATE not found in metadata!")

                # Manage NULL values
                try:
                    c_mul = float(c_mul)
                except ValueError:
                    c_mul = 1
                try:
                    c_add = float(c_add)
                except ValueError:
                    c_add = 0

                # Compute the correct reflectance of the band and set no data to 0
                band_xda = c_mul * band_xda + c_add  # Already in float

        return band_xda

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(
        self, band_arr: XDS_TYPE, band: obn, **kwargs
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            kwargs: Other arguments used to load bands

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Open QA band
        landsat_qa_path = self._get_path(self._radsat_id)
        qa_arr = self._read_band(
            landsat_qa_path,
            size=(band_arr.rio.width, band_arr.rio.height),
        ).data  # To np array

        if self._collection == LandsatCollection.COL_1:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band
            # Bit ids
            nodata_id = 0  # Fill value
            dropped_id = 1  # Dropped pixel or terrain occlusion
            # Set nodata to every saturated pixel, even if only 1-2 bands are touched by it
            # -> 01 or 10 or 11
            # -> bit 2 or bit 3
            sat_id_1 = 2
            sat_id_2 = 3
            nodata, dropped, sat_1, sat_2 = rasters.read_bit_array(
                qa_arr, [nodata_id, dropped_id, sat_id_1, sat_id_2]
            )
            mask = nodata | dropped | sat_1 | sat_2
        else:
            # https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands
            # SATURATED & OTHER PIXELS
            band_nb = int(self.band_names[band])

            # Bit ids
            sat_id = band_nb - 1  # Saturated pixel
            if self.product_type != LandsatProductType.L1_OLCI:
                other_id = 11  # Terrain occlusion
            else:
                other_id = 9  # Dropped pixels

            sat, other = rasters.read_bit_array(qa_arr, [sat_id, other_id])

            # If collection 2, nodata has to be found in pixel QA file
            landsat_stat_path = self._get_path(self._pixel_quality_id)
            pixel_arr = self._read_band(
                landsat_stat_path, size=(band_arr.rio.width, band_arr.rio.height)
            ).data
            nodata = np.where(pixel_arr == 1, 1, 0)

            mask = sat | other | nodata

        return self._set_nodata_mask(band_arr, mask)

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if not isinstance(bands, list):
            bands = [bands]

        if resolution is None and size is not None:
            resolution = self._resolution_from_size(size)
        band_paths = self.get_band_paths(bands, resolution=resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, resolution=resolution, size=size, **kwargs
        )

        return band_arrays

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (140.80752656, 61.93065805)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Retrieve angles
        mtd_data, _ = self._read_mtd()
        try:
            azimuth_angle = float(mtd_data.findtext(".//SUN_AZIMUTH"))
            zenith_angle = 90.0 - float(mtd_data.findtext(".//SUN_ELEVATION"))
        except TypeError:
            raise InvalidProductError("ACQUISITION_DATE not found in metadata!")

        return azimuth_angle, zenith_angle

    @abstractmethod
    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_Lx_{tile}_{product_type}).

        Returns:
            str: Condensed Landsat name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.tile_name}_{self.product_type.value}"

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands]
        """
        if self.product_type == LandsatProductType.L1_OLCI:
            has_band = True
        elif self.product_type in [LandsatProductType.L1_ETM, LandsatProductType.L1_TM]:
            has_band = self._e_tm_has_cloud_band(band)
        elif self.product_type == LandsatProductType.L1_MSS:
            has_band = self._mss_has_cloud_band(band)
        else:
            raise InvalidProductError(f"Invalid product type: {self.product_type}")

        return has_band

    @staticmethod
    def _mss_has_cloud_band(band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        if band in [RAW_CLOUDS, CLOUDS, ALL_CLOUDS]:
            has_band = True
        else:
            has_band = False
        return has_band

    @staticmethod
    def _e_tm_has_cloud_band(band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        if band in [RAW_CLOUDS, CLOUDS, ALL_CLOUDS, SHADOWS]:
            has_band = True
        else:
            has_band = False
        return has_band

    def _load_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands]


        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            # Open QA band
            landsat_qa_path = self._get_path(self._pixel_quality_id)
            qa_arr = self._read_band(landsat_qa_path, resolution=resolution, size=size)

            if self.product_type == LandsatProductType.L1_OLCI:
                band_dict = self._load_olci_clouds(qa_arr, bands)
            elif self.product_type in [
                LandsatProductType.L1_ETM,
                LandsatProductType.L1_TM,
            ]:
                band_dict = self._load_e_tm_clouds(qa_arr, bands)
            elif self.product_type == LandsatProductType.L1_MSS:
                band_dict = self._load_mss_clouds(qa_arr, bands)
            else:
                raise InvalidProductError(f"Invalid product type: {self.product_type}")

        return band_dict

    def _load_mss_clouds(self, qa_arr: XDS_TYPE, band_list: list) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-MSS clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/media/files/landsat-1-5-mss-collection-2-level-1-data-format-control-book]


        Args:
            qa_arr (XDS_TYPE): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        bands = {}

        # Get clouds and nodata
        nodata_id = 0
        cloud_id = (
            4 if self._collection == LandsatCollection.COL_1 else 3
        )  # Clouds with high confidence

        clouds = None
        if ALL_CLOUDS in band_list or CLOUDS in band_list:
            nodata, cld = rasters.read_bit_array(qa_arr, [nodata_id, cloud_id])
            clouds = self._create_mask(qa_arr, cld, nodata)

        for band in band_list:
            if band == ALL_CLOUDS:
                bands[band] = clouds
            elif band == CLOUDS:
                bands[band] = clouds
            elif band == RAW_CLOUDS:
                bands[band] = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for Landsat-MSS sensor: {band}"
                )

        return bands

    def _load_e_tm_clouds(
        self, qa_arr: XDS_TYPE, band_list: Union[list, BandNames]
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-(E)TM clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2 TM)[https://www.usgs.gov/media/files/landsat-4-5-tm-collection-2-level-1-data-format-control-book]
        - (COL 2 ETM)[https://www.usgs.gov/media/files/landsat-7-etm-collection-2-level-1-data-format-control-book]


        Args:
            qa_arr (XDS_TYPE): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        bands = {}

        # Get clouds and nodata
        nodata = None
        cld = None
        shd = None
        if any(band in [ALL_CLOUDS, CLOUDS, SHADOWS] for band in band_list):
            if self._collection == LandsatCollection.COL_1:
                # Bit id
                nodata_id = 0
                cloud_id = 4  # Clouds with high confidence
                shd_conf_1_id = 7
                shd_conf_2_id = 8
                nodata, cld, shd_conf_1, shd_conf_2 = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_conf_1_id, shd_conf_2_id]
                )
                shd = shd_conf_1 & shd_conf_2
            else:
                # Bit ids
                nodata_id = 0
                cloud_id = 3  # Clouds with high confidence
                shd_id = 4  # Shadows with high confidence
                nodata, cld, shd = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_id]
                )

        for band in band_list:
            if band == ALL_CLOUDS:
                bands[band] = self._create_mask(qa_arr, cld | shd, nodata)
            elif band == SHADOWS:
                bands[band] = self._create_mask(qa_arr, shd, nodata)
            elif band == CLOUDS:
                bands[band] = self._create_mask(qa_arr, cld, nodata)
            elif band == RAW_CLOUDS:
                bands[band] = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for Landsat-(E)TM sensor: {band}"
                )

        return bands

    def _load_olci_clouds(
        self, qa_arr: XDS_TYPE, band_list: Union[list, BandNames]
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat-OLCI clouds from QA mask.
        See here for clouds_values:

        - (COL 1)[https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band]
        - (COL 2)[https://www.usgs.gov/media/files/landsat-8-level-1-data-format-control-book]


        Args:
            qa_arr (XDS_TYPE): Quality array
            band_list (list): List of the wanted bands
        Returns:
            dict, dict: Dictionary {band_name, band_array}
        """
        bands = {}

        # Get clouds and nodata
        nodata = None
        cld = None
        shd = None
        cir = None
        if any(band in [ALL_CLOUDS, CLOUDS, SHADOWS] for band in band_list):
            if self._collection == LandsatCollection.COL_1:
                # Bit ids
                nodata_id = 0
                cloud_id = 4  # Clouds with high confidence
                shd_conf_1_id = 7
                shd_conf_2_id = 8
                cir_conf_1_id = 11
                cir_conf_2_id = 12

                # Read binary mask
                (
                    nodata,
                    cld,
                    shd_conf_1,
                    shd_conf_2,
                    cir_conf_1,
                    cir_conf_2,
                ) = rasters.read_bit_array(
                    qa_arr,
                    [
                        nodata_id,
                        cloud_id,
                        shd_conf_1_id,
                        shd_conf_2_id,
                        cir_conf_1_id,
                        cir_conf_2_id,
                    ],
                )

                shd = shd_conf_1 & shd_conf_2
                cir = cir_conf_1 & cir_conf_2
            else:
                # Bit ids
                nodata_id = 0
                cloud_id = 3  # Clouds with high confidence
                shd_id = 4  # Shadows with high confidence
                cir_id = 2  # Cirrus with high confidence
                nodata, cld, shd, cir = rasters.read_bit_array(
                    qa_arr, [nodata_id, cloud_id, shd_id, cir_id]
                )

        for band in band_list:
            if band == ALL_CLOUDS:
                bands[band] = self._create_mask(qa_arr, cld | shd | cir, nodata)
            elif band == SHADOWS:
                bands[band] = self._create_mask(qa_arr, shd, nodata)
            elif band == CLOUDS:
                bands[band] = self._create_mask(qa_arr, cld, nodata)
            elif band == CIRRUS:
                bands[band] = self._create_mask(qa_arr, cir, nodata)
            elif band == RAW_CLOUDS:
                bands[band] = qa_arr
            else:
                raise InvalidTypeError(
                    f"Non existing cloud band for Landsat-OLCI sensor: {band}"
                )

        return bands
