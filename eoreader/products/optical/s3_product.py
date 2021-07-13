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
""" Sentinel-3 products """
import logging
import os
import tempfile
from datetime import datetime
from enum import unique
from functools import reduce
from pathlib import Path
from typing import Union

import geopandas as gpd
import netCDF4
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import features
from rasterio.enums import Resampling
from rasterio.windows import Window

from eoreader import utils
from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.env_vars import S3_DEF_RES
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME
from sertit import files, misc, rasters, rasters_rio, snap, strings, vectors
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

LOGGER = logging.getLogger(EOREADER_NAME)
BT_BANDS = [obn.MIR, obn.TIR_1, obn.TIR_2]


@unique
class S3ProductType(ListEnum):
    """Sentinel-3 products types (not exhaustive, only L1)"""

    OLCI_EFR = "OL_1_EFR___"
    """OLCI EFR Product Type"""

    SLSTR_RBT = "SL_1_RBT___"
    """SLSTR RBT Product Type"""


@unique
class S3Instrument(ListEnum):
    """Sentinel-3 products types"""

    OLCI = "OLCI"
    """OLCI Instrument"""

    SLSTR = "SLSTR"
    """SLSTR Instrument"""


@unique
class S3DataTypes(ListEnum):
    """Sentinel-3 data types -> only considering useful ones"""

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

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        self._instrument_name = None
        self._data_type = None
        self._snap_no_data = -1
        super().__init__(
            product_path, archive_path, output_path, remove_tmp
        )  # Order is important here

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
            def_res = 300.0
        else:
            def_res = 500.0
        return def_res

    def _set_product_type(self) -> None:
        """Set products type"""
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
                raise InvalidTypeError(
                    "Only EFR data type is used for Sentinel-3 OLCI data."
                )

            # Bands
            self.band_names.map_bands(
                {
                    obn.CA: "02",
                    obn.BLUE: "03",
                    obn.GREEN: "06",
                    obn.RED: "08",
                    obn.VRE_1: "11",
                    obn.VRE_2: "12",
                    obn.VRE_3: "16",
                    obn.NIR: "17",
                    obn.NARROW_NIR: "17",
                    obn.WV: "20",
                    obn.FAR_NIR: "21",
                }
            )
        elif "SL" in self.name:
            # Instrument
            self._instrument_name = S3Instrument.SLSTR

            # Data type
            if S3DataTypes.RBT.value in self.name:
                self._data_type = S3DataTypes.RBT
                self.product_type = S3ProductType.SLSTR_RBT
            else:
                raise InvalidTypeError(
                    "Only RBT data type is used for Sentinel-3 SLSTR data."
                )

            # Bands
            self.band_names.map_bands(
                {
                    obn.GREEN: "1",  # radiance, 500m
                    obn.RED: "2",  # radiance, 500m
                    obn.NIR: "3",  # radiance, 500m
                    obn.NARROW_NIR: "3",  # radiance, 500m
                    obn.SWIR_CIRRUS: "4",  # radiance, 500m
                    obn.SWIR_1: "5",  # radiance, 500m
                    obn.SWIR_2: "6",  # radiance, 500m
                    obn.MIR: "7",  # brilliance temperature, 1km
                    obn.TIR_1: "8",  # brilliance temperature, 1km
                    obn.TIR_2: "9",  # brilliance temperature, 1km
                }
            )
        else:
            raise InvalidProductError(f"Invalid Sentinel-3 name: {self.name}")

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint in UTM of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return rasters.get_footprint(
            self.get_default_band_path()
        )  # Processed by SNAP: the nodata is set

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 11, 15, 23, 37, 22)
            >>> prod.get_datetime(as_datetime=False)
            '20191115T233722'

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
            raise InvalidProductError(
                f"Non existing band ({band.name}) for S3-{self._data_type.name} products"
            )

        # Get band name
        if self._data_type == S3DataTypes.EFR:
            snap_bn = f"Oa{band_nb}_reflectance"  # Converted into reflectance previously in the graph
        elif self._data_type == S3DataTypes.RBT:
            if band in BT_BANDS:
                snap_bn = f"S{band_nb}_BT_in"
            else:
                snap_bn = f"S{band_nb}_reflectance_an"  # Conv into reflectance previously in the graph
        else:
            raise InvalidTypeError(
                f"Unknown data type for Sentinel-3 data: {self._data_type}"
            )

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
        band = list(self.band_names.keys())[
            list(self.band_names.values()).index(band_nb)
        ]

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
            raise InvalidProductError(
                f"Non existing band ({band.name}) for S3-{self._data_type.name} products"
            )

        # Get quality flag name
        if self._data_type == S3DataTypes.RBT:
            snap_bn = f"S{band_nb}_exception_{'i' if band in BT_BANDS else 'a'}n"
        else:
            raise InvalidTypeError(
                f"This function only works for Sentinel-3 SLSTR data: {self._data_type}"
            )

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
            raise InvalidTypeError(
                "The given band should be an OpticalBandNames or directly the snap_name"
            )

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

        .. code-block:: python

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

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        use_snap = False
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(band, resolution=resolution)
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                # Get standard band names
                band_name = self._get_band_filename(band)

                try:
                    # Try to open converted images
                    band_paths[band] = files.get_file_in_dir(
                        self._get_band_folder(),
                        f"{self.condensed_name}_{band_name}.tif",
                    )
                except (FileNotFoundError, TypeError):
                    use_snap = True

            # If not existing (file or output), convert them
            if use_snap:
                all_band_paths = self._preprocess_s3(resolution)
                band_paths = {band: all_band_paths[band] for band in band_list}

        return band_paths

    # pylint: disable=W0613

    def _read_band(
        self,
        path: str,
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (str): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            XDS_TYPE: Band xarray

        """
        # Read band
        return rasters.read(
            path, resolution=resolution, size=size, resampling=Resampling.bilinear
        )

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(
        self,
        band_arr: XDS_TYPE,
        band: obn,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            XDS_TYPE: Cleaned band array
        """
        if self._instrument_name == S3Instrument.OLCI:
            band_arr_mask = self._manage_invalid_pixels_olci(
                band_arr, band, resolution=resolution, size=size
            )
        else:
            band_arr_mask = self._manage_invalid_pixels_slstr(
                band_arr, band, resolution=resolution, size=size
            )

        return band_arr_mask

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels_olci(
        self,
        band_arr: XDS_TYPE,
        band: obn,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
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
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            XDS_TYPE: Cleaned band array
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
            obn.NARROW_NIR: 4,  # Band 17
            obn.WV: 1,  # Band 20
            obn.FAR_NIR: 0,  # Band 21
        }
        invalid_id = 24
        sat_band_id = band_bit_id[band]

        # Open quality flags
        qual_flags_path = self._get_band_folder().joinpath(
            f"{self.condensed_name}_quality_flags.tif"
        )
        if not qual_flags_path.is_file():
            LOGGER.warning(
                "Impossible to open quality flags %s. Taking the band as is.",
                qual_flags_path,
            )
            return band_arr

        # Open flag file
        qual_arr, _ = rasters_rio.read(
            qual_flags_path,
            resolution=resolution,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
        )
        invalid, sat = rasters.read_bit_array(
            qual_arr.astype(np.uint32), [invalid_id, sat_band_id]
        )

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr), nodata_true, nodata_false)

        # Combine masks
        mask = no_data | invalid | sat

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels_slstr(
        self,
        band_arr: XDS_TYPE,
        band: obn,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        ISP_absent pixel_absent not_decompressed no_signal saturation invalid_radiance no_parameters unfilled_pixel"

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            XDS_TYPE: Cleaned band array
        """
        nodata_true = 1
        nodata_false = 0

        # Open quality flags (discard _an/_in)
        qual_flags_path = self._get_band_folder().joinpath(
            f"{self.condensed_name}_{self._get_slstr_quality_flags_name(band)[:-3]}.tif"
        )
        if not qual_flags_path.is_file():
            LOGGER.warning(
                "Impossible to open quality flags %s. Taking the band as is.",
                qual_flags_path,
            )
            return band_arr

        # Open flag file
        qual_arr, _ = rasters_rio.read(
            qual_flags_path,
            resolution=resolution,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
        )

        # Set no data for everything (except ISP) that caused an exception
        exception = np.where(qual_arr > 2, nodata_true, nodata_false)

        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), nodata_true, nodata_false)

        # Combine masks
        mask = no_data | exception

        # DO not set 0 to epsilons as they are a part of the
        return self._set_nodata_mask(band_arr, mask)

    def _load_bands(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if not isinstance(bands, list):
            bands = [bands]
        band_paths = self.get_band_paths(bands)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays

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
                out_tif = self._tmp_process.joinpath(
                    f"{self.condensed_name}_{band_name}.tif"
                )
                if out_tif.is_file():
                    files.remove(out_tif)

                # Convert to geotiffs and set no data with only keeping the first band
                with rioxarray.open_rasterio(
                    str(rasters.get_dim_img_path(out_dim, snap_band_name))
                ) as arr:
                    arr = arr.where(arr != self._snap_no_data)
                    rasters.write(arr, out_tif, dtype=np.float32)

        # Get the wanted bands (not the quality flags here !)
        for band in processed_bands:
            filename = self._get_band_filename(band)
            if "exception" not in filename:
                out_tif = self._tmp_process.joinpath(
                    f"{self.condensed_name}_{band_name}.tif"
                )
                if not out_tif.is_file():
                    raise FileNotFoundError(
                        f"Error when processing S3 bands with SNAP. Couldn't find {out_tif}"
                    )

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
        graph_path = utils.get_data_dir().joinpath("preprocess_s3.xml")
        snap_bands = ",".join(
            [
                self._get_snap_band_name(band)
                for band, band_nb in self.band_names.items()
                if band_nb
            ]
        )
        if self._instrument_name == S3Instrument.OLCI:
            sensor = "OLCI"
            fmt = "Sen3"
            snap_bands += ",quality_flags"
        else:
            sensor = "SLSTR_500m"
            fmt = "Sen3_SLSTRL1B_500m"
            exception_bands = ",".join(
                [
                    self._get_slstr_quality_flags_name(band)
                    for band, band_nb in self.band_names.items()
                    if band_nb
                ]
            )
            snap_bands += f",{exception_bands},cloud_an,cloud_in"

        # Download cloud path to cache
        if isinstance(self.path, CloudPath):
            if self.path.is_dir():
                LOGGER.debug(f"Caching {self.path}")
                prod_path = os.path.join(os.path.dirname(out_dim), self.path.name)
                self.path.download_to(prod_path)
            else:
                raise InvalidProductError(
                    "Sentinel-3 data must be extracted, as NetCDF data cannot be read through zip."
                )
        else:
            prod_path = self.path

        # Run GPT graph
        cmd_list = snap.get_gpt_cli(
            graph_path,
            [
                f"-Pin={strings.to_cmd_string(prod_path)}",
                f"-Pbands={snap_bands}",
                f"-Psensor={sensor}",
                f"-Pformat={fmt}",
                f"-Pno_data={self._snap_no_data}",
                f"-Pres_m={resolution if resolution else def_res}",
                f"-Pout={strings.to_cmd_string(out_dim)}",
            ],
            display_snap_opt=LOGGER.level == logging.DEBUG,
        )
        LOGGER.debug("Converting %s", self.name)
        try:
            misc.run_cli(cmd_list)
        except RuntimeError as ex:
            raise RuntimeError("Something went wrong with SNAP!") from ex

        return snap_bands.split(",")

    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile, managing the case with not orthorectified bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                                        geometry
            0  POLYGON ((1488846.028 6121896.451, 1488846.028...

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
                with rasterio.open(str(path), "r") as sub_ds:
                    # Open the 4 corners of the array
                    height = sub_ds.height
                    width = sub_ds.width
                    scales = sub_ds.scales
                    pt1 = sub_ds.read(1, window=Window(0, 0, 1, 1)) * scales
                    pt2 = sub_ds.read(1, window=Window(width - 1, 0, width, 1)) * scales
                    pt3 = (
                        sub_ds.read(1, window=Window(0, height - 1, 1, height)) * scales
                    )
                    pt4 = (
                        sub_ds.read(
                            1, window=Window(width - 1, height - 1, width, height)
                        )
                        * scales
                    )
                    pt_list = [pt1, pt2, pt3, pt4]

                    # Return min and max
                    return np.min(pt_list), np.max(pt_list)

            if self.product_type == S3ProductType.OLCI_EFR:
                # Open geodetic_an.nc
                geom_file = self.path.joinpath(
                    "geo_coordinates.nc"
                )  # Only use nadir files

                with rasterio.open(str(geom_file), "r") as geom_ds:
                    lat_min, lat_max = get_min_max("latitude", geom_ds.subdatasets)
                    lon_min, lon_max = get_min_max("longitude", geom_ds.subdatasets)

            elif self.product_type == S3ProductType.SLSTR_RBT:
                # Open geodetic_an.nc
                geom_file = self.path.joinpath("geodetic_an.nc")  # Only use nadir files

                with rasterio.open(str(geom_file), "r") as geom_ds:
                    lat_min, lat_max = get_min_max("latitude_an", geom_ds.subdatasets)
                    lon_min, lon_max = get_min_max("longitude_an", geom_ds.subdatasets)
            else:
                raise InvalidTypeError(
                    f"Invalid products type {self.product_type}"
                ) from ex

            # Create wgs84 extent (left, bottom, right, top)
            extent_wgs84 = gpd.GeoDataFrame(
                geometry=[
                    vectors.from_bounds_to_polygon(lon_min, lat_min, lon_max, lat_max)
                ],
                crs=vectors.WGS84,
            )

            # Get upper-left corner and deduce UTM proj from it
            utm = vectors.corresponding_utm_projection(
                extent_wgs84.bounds.minx, extent_wgs84.bounds.maxy
            )
            extent = extent_wgs84.to_crs(utm)

        return extent

    def _get_condensed_name(self) -> str:
        """
        Get S3 products condensed name ({date}_S3_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.product_type.name}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (78.55043955912154, 31.172127033319388)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        if self._data_type == S3DataTypes.EFR:
            geom_file = self.path.joinpath("tie_geometries.nc")
            sun_az = "SAA"
            sun_ze = "SZA"
        elif self._data_type == S3DataTypes.RBT:
            geom_file = self.path.joinpath("geometry_tn.nc")  # Only use nadir files
            sun_az = "solar_azimuth_tn"
            sun_ze = "solar_zenith_tn"
        else:
            raise InvalidTypeError(
                f"Unknown/Unsupported data type for Sentinel-3 data: {self._data_type}"
            )

        # Open file
        if geom_file.is_file():
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
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element level1Product at 0x1b845b7ab88>, '')

        Returns:
            (etree._Element, str): Metadata XML root and its namespace
        """
        raise NotImplementedError(
            "Sentinel-3 products don't have XML metadata. "
            "Please check directly into NetCDF files"
        )

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?

        - SLSTR does
        - OLCI does not provide any cloud mask
        """
        if self._instrument_name == S3Instrument.SLSTR and band in [
            RAW_CLOUDS,
            ALL_CLOUDS,
            CLOUDS,
            CIRRUS,
        ]:
            has_band = True
        else:
            has_band = False

        return has_band

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

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
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            if self._instrument_name == S3Instrument.OLCI:
                raise InvalidTypeError(
                    "Sentinel-3 OLCI sensor does not provide any cloud file."
                )

            all_ids = list(np.arange(0, 14))
            cir_id = 8
            cloud_ids = [id for id in all_ids if id != cir_id]

            try:
                cloud_path = files.get_file_in_dir(
                    self._get_band_folder(), "cloud_RAD.tif"
                )
            except FileNotFoundError:
                self._preprocess_s3(resolution)
                cloud_path = files.get_file_in_dir(self._tmp_process, "cloud_RAD.tif")

            if not cloud_path:
                raise FileNotFoundError(
                    f"Unable to find the cloud mask for {self.path}"
                )

            # Open cloud file
            clouds_array = rasters.read(
                cloud_path,
                resolution=resolution,
                size=size,
                resampling=Resampling.nearest,
                masked=False,
            ).astype(np.uint16)

            # Get nodata mask
            # nodata = np.where(np.isnan(clouds_array), 1, 0)
            nodata = np.where(clouds_array == 65535, 1, 0)

            for band in bands:
                if band == ALL_CLOUDS:
                    band_dict[band] = self._create_mask(clouds_array, all_ids, nodata)
                elif band == CLOUDS:
                    band_dict[band] = self._create_mask(clouds_array, cloud_ids, nodata)
                elif band == CIRRUS:
                    band_dict[band] = self._create_mask(clouds_array, cir_id, nodata)
                elif band == RAW_CLOUDS:
                    band_dict[band] = clouds_array
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-3 SLSTR: {band}"
                    )

        return band_dict

    def _create_mask(
        self,
        bit_array: xr.DataArray,
        bit_ids: Union[int, list],
        nodata: np.ndarray,
    ) -> xr.DataArray:
        """
        Create a mask masked array (uint8) from a bit array, bit IDs and a nodata mask.

        Args:
            bit_array (xr.DataArray): Conditional array
            bit_ids (Union[int, list]): Bit IDs
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Mask masked array

        """
        if not isinstance(bit_ids, list):
            bit_ids = [bit_ids]
        conds = rasters.read_bit_array(bit_array, bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every conditions (bitwise or)

        cond_arr = np.where(cond, self._mask_true, self._mask_false).astype(np.uint8)
        cond_arr = np.squeeze(cond_arr)
        cond_arr = features.sieve(cond_arr, size=10, connectivity=4)
        cond_arr = np.expand_dims(cond_arr, axis=0)

        return super()._create_mask(bit_array, cond_arr, nodata)
