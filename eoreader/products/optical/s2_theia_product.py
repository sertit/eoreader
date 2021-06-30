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
"""
Sentinel-2 Theia products.
See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_ for more information.
"""

import datetime
import logging
from functools import reduce
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio.enums import Resampling

from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS, SHADOWS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.products.optical.s2_product import S2ProductType
from eoreader.utils import DATETIME_FMT, EOREADER_NAME
from sertit import files, rasters, rasters_rio, vectors
from sertit.rasters import XDS_TYPE

LOGGER = logging.getLogger(EOREADER_NAME)


class S2TheiaProduct(OpticalProduct):
    """
    Class of Sentinel-2 Theia Products.
    See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_
    for more information.
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
        return 20.0

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """

        return self.split_name[3]

    def _set_product_type(self) -> None:
        """Set products type"""
        self.product_type = S2ProductType.L2A
        self.band_names.map_bands(
            {
                obn.BLUE: "2",
                obn.GREEN: "3",
                obn.RED: "4",
                obn.VRE_1: "5",
                obn.VRE_2: "6",
                obn.VRE_3: "7",
                obn.NIR: "8",
                obn.NARROW_NIR: "8A",
                obn.SWIR_1: "11",
                obn.SWIR_2: "12",
            }
        )

        # TODO: bands 1 and 9 are in ATB_R1 (10m) and ATB_R2 (20m)
        # B1 to be divided by 20
        # B9 to be divided by 200

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. WARNING::
            As Landsat 7 is broken (with nodata stripes all over the bands),
            the footprint is not easily computed and may take some time to be delivered.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
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
        edg_path = self.get_mask_path("EDG", "R2")

        # Open SAT band
        mask = rasters.read(edg_path, masked=False)

        # Vectorize the nodata band
        footprint = rasters.vectorize(mask, values=0, default_nodata=-1)
        footprint = vectors.get_wider_exterior(footprint).convex_hull

        return footprint

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime.datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms
            >>> prod.get_datetime(as_datetime=False)
            '20190625T105728'

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

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <OpticalBandNames.GREEN: 'GREEN'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
                <OpticalBandNames.RED: 'RED'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:  # Get clean band path
            clean_band = self._get_clean_band_path(band, resolution=resolution)
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                try:
                    if self.is_archived:
                        band_paths[band] = files.get_archived_rio_path(
                            self.path, f".*FRE_B{self.band_names[band]}\.tif"
                        )
                    else:
                        band_paths[band] = files.get_file_in_dir(
                            self.path, f"FRE_B{self.band_names[band]}.tif"
                        )
                except (FileNotFoundError, IndexError) as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({self.band_names[band]}) band for {self.path}"
                    ) from ex

        return band_paths

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
        band_xda = rasters.read(
            path, resolution=resolution, size=size, resampling=Resampling.bilinear
        ).astype(np.float32)

        # Compute the correct radiometry of the band
        band_xda = band_xda / 10000.0

        return band_xda

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
        See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_ for more
        information.

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

        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        theia_nodata = -1.0
        no_data_mask = np.where(
            band_arr.data == theia_nodata, nodata_true, nodata_false
        ).astype(np.uint8)

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
        return self._set_nodata_mask(band_arr, mask)

    def get_mask_path(self, mask_id: str, res_id: str) -> str:
        """
        Get mask path from its id and file_id (`R1` for 10m resolution, `R2` for 20m resolution)

        Accepted mask IDs:

        - `DFP`: Defective pixels (do not always exist ! Will raise `InvalidProductError` if not)
        - `EDG`: Nodata pixels mask
        - `SAT`: Saturated pixels mask
        - `MG2`: Geophysical mask (classification)
        - `IAB`: Mask where water vapor and TOA pixels have been interpolated
        - `CLM`: Cloud mask

        Args:
            mask_id (str): Mask ID
            res_id (str): Resolution ID (`R1` or `R2`)

        Returns:
            str: Mask path
        """
        assert res_id in ["R1", "R2"]

        mask_regex = f"*{mask_id}_{res_id}.tif"
        try:
            if self.is_archived:
                mask_path = files.get_archived_rio_path(
                    self.path, mask_regex.replace("*", ".*")
                )
            else:
                mask_path = files.get_file_in_dir(
                    self.path.joinpath("MASKS"), mask_regex, exact_name=True
                )
        except (FileNotFoundError, IndexError) as ex:
            raise InvalidProductError(
                f"Non existing mask {mask_regex} in {self.name}"
            ) from ex

        return mask_path

    def open_mask(
        self,
        mask_id: str,
        band: Union[obn, str],
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> np.ndarray:
        """
        Open a Sentinel-2 THEIA mask as a numpy array.

        - Opens the saturation and defective mask to the correct bit ID corresponding to the given band.
        - Opens the nodata binary mask
        - Opens the other masks as is

        Do not open cloud mask with this function. Use `load` instead.

        See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_ for more
        information.

        Accepted mask IDs:

        - `DFP`: Defective pixels
        - `EDG`: Nodata pixels mask
        - `SAT`: Saturated pixels mask
        - `MG2`: Geophysical mask (classification)
        - `IAB`: Mask where water vapor and TOA pixels have been interpolated

        .. code-block:: python

            >>> from eoreader.bands.alias import *
            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
            >>> prod = Reader().open(path)
            >>> prod.open_mask("EDG", GREEN)
            array([[[0, ..., 0]]], dtype=uint8)

        Args:
            mask_id: Mask ID
            band (Union[obn, str]): Band name as an OpticalBandNames or resolution ID: [`R1`, `R2`]
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ndarray: Mask array

        """
        # https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/
        # For r_1, the band order is: B2, B3, B4, B8 and for r_2: B5, B6, B7, B8a, B11, B12
        res_10m = [obn.BLUE, obn.GREEN, obn.RED, obn.NIR, "R1"]
        res_20m = [
            obn.VRE_1,
            obn.VRE_2,
            obn.VRE_3,
            obn.NARROW_NIR,
            obn.SWIR_1,
            obn.SWIR_2,
            "R2",
        ]
        if band in res_10m:
            bit_id = res_10m.index(band)
            res_id = "R1"
        elif band in res_20m:
            res_id = "R2"
            bit_id = res_20m.index(band)
        else:
            raise InvalidProductError(f"Invalid band: {band.value}")

        mask_path = self.get_mask_path(mask_id, res_id)

        # Open SAT band
        mask, _ = rasters_rio.read(
            mask_path,
            resolution=resolution,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
        )

        if mask_id in ["SAT", "DFP"]:
            bit_mask = rasters_rio.read_bit_array(mask, bit_id)
        else:
            bit_mask = mask

        return bit_mask

    def _load_bands(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands list: List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        band_paths = self.get_band_paths(bands)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_S2THEIA_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return (
            f"{self.get_datetime()}_S2THEIA_{self.tile_name}_{self.product_type.value}"
        )

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (154.554755774838, 27.5941391571236)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        try:
            mean_sun_angles = root.find(".//Sun_Angles")
            zenith_angle = float(mean_sun_angles.findtext("ZENITH_ANGLE"))
            azimuth_angle = float(mean_sun_angles.findtext("AZIMUTH_ANGLE"))
        except TypeError:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        return azimuth_angle, zenith_angle

    def read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element Muscate_Metadata_Document at 0x252d2071e88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = "MTD_ALL.xml"
        mtd_archived = "MTD_ALL\.xml"

        return self._read_mtd(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        return True

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read S2 Theia cloud mask:
        https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/

        > A cloud mask for each resolution (CLM_R1.tif ou CLM_R2.tif):
            - bit 0 (1) : all clouds except the thinnest and all shadows
            - bit 1 (2) : all clouds (except the thinnest)
            - bit 2 (4) : clouds detected via mono-temporal thresholds
            - bit 3 (8) : clouds detected via multi-temporal thresholds
            - bit 4 (16) : thinnest clouds
            - bit 5 (32) : cloud shadows cast by a detected cloud
            - bit 6 (64) : cloud shadows cast by a cloud outside image
            - bit 7 (128) : high clouds detected by 1.38 µm

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            # Open 20m cloud file if resolution >= 20m
            res_id = "R2" if resolution >= 20 else "R1"

            cloud_path = self.get_mask_path("CLM", res_id)
            clouds_mask = rasters.read(
                cloud_path,
                resolution=resolution,
                size=size,
                resampling=Resampling.nearest,
            ).astype(np.float32)

            # Get nodata mask
            nodata = self.open_mask("EDG", res_id, resolution=resolution, size=size)

            # Bit ids
            clouds_shadows_id = 0
            clouds_id = 1
            cirrus_id = 4
            shadows_in_id = 5
            shadows_out_id = 6

            for res_id in bands:
                if res_id == ALL_CLOUDS:
                    band_dict[res_id] = self._create_mask(
                        clouds_mask, [clouds_shadows_id, cirrus_id], nodata
                    )
                elif res_id == SHADOWS:
                    band_dict[res_id] = self._create_mask(
                        clouds_mask, [shadows_in_id, shadows_out_id], nodata
                    )
                elif res_id == CLOUDS:
                    band_dict[res_id] = self._create_mask(
                        clouds_mask, clouds_id, nodata
                    )
                elif res_id == CIRRUS:
                    band_dict[res_id] = self._create_mask(
                        clouds_mask, cirrus_id, nodata
                    )
                elif res_id == RAW_CLOUDS:
                    band_dict[res_id] = clouds_mask
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-2 THEIA: {res_id}"
                    )

        return band_dict

    def _create_mask(
        self, bit_array: XDS_TYPE, bit_ids: Union[int, list], nodata: np.ndarray
    ) -> xr.DataArray:
        """
        Create a mask masked array (uint8) from a bit array, bit IDs and a nodata mask.

        Args:
            bit_array (XDS_TYPE): Conditional array
            bit_ids (Union[int, list]): Bit IDs
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Mask masked array

        """
        if not isinstance(bit_ids, list):
            bit_ids = [bit_ids]
        conds = rasters.read_bit_array(bit_array.astype(np.uint8), bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every conditions (bitwise or)

        return super()._create_mask(bit_array, cond, nodata)
