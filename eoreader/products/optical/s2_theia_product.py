# -*- coding: utf-8 -*-
# Copyright 2022, SERTIT-ICube - France, https://sertit.unistra.fr/
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

import logging
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from rasterio.enums import Resampling
from sertit import files, rasters, rasters_rio, vectors

from eoreader import cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    RAW_CLOUDS,
    SHADOWS,
    BandNames,
    SpectralBand,
)
from eoreader.bands import spectral_bands as spb
from eoreader.bands import to_str
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import OpticalProduct, S2ProductType
from eoreader.stac import CENTER_WV, FWHM, GSD, ID, NAME
from eoreader.utils import DATETIME_FMT, EOREADER_NAME, simplify

LOGGER = logging.getLogger(EOREADER_NAME)


class S2TheiaProduct(OpticalProduct):
    """
    Class of Sentinel-2 Theia Products.
    See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._has_cloud_cover = True
        self.needs_extraction = False
        self._use_filename = True

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        # S2: use 10m resolution, even if we have 60m and 20m resolution
        # In the future maybe set one resolution per band ?
        return 10.0

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        tile = root.findtext(".//GEOGRAPHICAL_ZONE")
        if not tile:
            raise InvalidProductError("GEOGRAPHICAL_ZONE not found in metadata!")

        return tile

    def _set_product_type(self) -> None:
        """Set products type"""
        self.product_type = S2ProductType.L2A

    def _set_instrument(self) -> None:
        """
        Set instrument

        Sentinel-2: https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2/instrument-payload/
        """
        self.instrument = "MSI"

    def _map_bands(self) -> None:
        """
        Map bands
        """
        l2a_bands = {
            spb.BLUE: SpectralBand(
                eoreader_name=spb.BLUE,
                **{NAME: "B2", ID: "2", GSD: 10, CENTER_WV: 492, FWHM: 66},
            ),
            spb.GREEN: SpectralBand(
                eoreader_name=spb.GREEN,
                **{NAME: "B3", ID: "3", GSD: 10, CENTER_WV: 560, FWHM: 36},
            ),
            spb.RED: SpectralBand(
                eoreader_name=spb.RED,
                **{NAME: "B4", ID: "4", GSD: 10, CENTER_WV: 665, FWHM: 31},
            ),
            spb.VRE_1: SpectralBand(
                eoreader_name=spb.VRE_1,
                **{NAME: "B5", ID: "5", GSD: 20, CENTER_WV: 704, FWHM: 15},
            ),
            spb.VRE_2: SpectralBand(
                eoreader_name=spb.VRE_2,
                **{NAME: "B6", ID: "6", GSD: 20, CENTER_WV: 740, FWHM: 15},
            ),
            spb.VRE_3: SpectralBand(
                eoreader_name=spb.VRE_3,
                **{NAME: "B7", ID: "7", GSD: 20, CENTER_WV: 781, FWHM: 20},
            ),
            spb.NIR: SpectralBand(
                eoreader_name=spb.NIR,
                **{NAME: "B8A", ID: "8A", GSD: 10, CENTER_WV: 833, FWHM: 106},
            ),
            spb.NARROW_NIR: SpectralBand(
                eoreader_name=spb.NARROW_NIR,
                **{NAME: "B8", ID: "8", GSD: 20, CENTER_WV: 864, FWHM: 21},
            ),
            spb.SWIR_1: SpectralBand(
                eoreader_name=spb.SWIR_1,
                **{NAME: "B11", ID: "11", GSD: 20, CENTER_WV: 1612, FWHM: 92},
            ),
            spb.SWIR_2: SpectralBand(
                eoreader_name=spb.SWIR_2,
                **{NAME: "B12", ID: "12", GSD: 20, CENTER_WV: 2190, FWHM: 180},
            ),
        }
        self.bands.map_bands(l2a_bands)

        # TODO: bands 1 and 9 are in ATB_R1 (10m) and ATB_R2 (20m)
        # B1 to be divided by 20
        # B9 to be divided by 200

    @cache
    @simplify
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
        mask = utils.read(edg_path, masked=False)

        # Vectorize the nodata band
        footprint = rasters.vectorize(mask, values=0, default_nodata=-1)
        footprint = vectors.get_wider_exterior(footprint)
        footprint.geometry = footprint.geometry.convex_hull

        return footprint

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//ACQUISITION_DATE")
            if not acq_date:
                raise InvalidProductError("ACQUISITION_DATE not found in metadata!")

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        name = files.get_filename(root.findtext(".//IDENTIFIER"))
        if not name:
            raise InvalidProductError("IDENTIFIER not found in metadata!")

        return name

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        For Theia products, FRE bands are given because, it is written in the <documentation `https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/`>_
        that "After having compiled the user feedback, it is likely that we will only distribute « FRE » files to reduce the data volume."

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
                <SpectralBandNames.RED: 'RED'>: 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:  # Get clean band path
            clean_band = self._get_clean_band_path(
                band, resolution=resolution, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                band_id = self.bands[band].id
                try:
                    if self.is_archived:
                        band_paths[band] = files.get_archived_rio_path(
                            self.path, rf".*FRE_B{band_id}\.tif"
                        )
                    else:
                        band_paths[band] = files.get_file_in_dir(
                            self.path, f"FRE_B{band_id}.tif"
                        )
                except (FileNotFoundError, IndexError) as ex:
                    raise InvalidProductError(
                        f"Non existing {band.name} ({band_id}) band for {self.path}"
                    ) from ex

        return band_paths

    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
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
            xr.DataArray: Band xarray
        """
        band_arr = utils.read(
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
            **kwargs,
        )

        # Convert type if needed
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        path: Union[Path, CloudPath],
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # Compute the correct radiometry of the band for raw band
        if files.get_filename(path).startswith("SENTINEL"):
            band_arr /= 10000.0

        # Convert type if needed
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_ for more
        information.

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        theia_nodata = -1.0
        no_data_mask = np.where(
            band_arr.data == theia_nodata, self._mask_true, self._mask_false
        ).astype(np.uint8)

        # Open NODATA pixels mask
        edg_mask = self.open_mask(
            "EDG", band, size=(band_arr.rio.width, band_arr.rio.height)
        )

        # Open saturated pixels
        sat_mask = self.open_mask(
            "SAT", band, size=(band_arr.rio.width, band_arr.rio.height)
        )

        # Combine masks
        mask = no_data_mask | edg_mask | sat_mask

        # Open defective pixels (optional mask)
        try:
            def_mask = self.open_mask(
                "DFP", band, size=(band_arr.rio.width, band_arr.rio.height)
            )
            mask = mask | def_mask
        except InvalidProductError:
            pass

        # -- Merge masks
        return self._set_nodata_mask(band_arr, mask)

    def _manage_nodata(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage only nodata pixels

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as a SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        theia_nodata = -1.0
        no_data_mask = np.where(
            band_arr.data == theia_nodata, self._mask_true, self._mask_false
        ).astype(np.uint8)

        # -- Merge masks
        return self._set_nodata_mask(band_arr, no_data_mask)

    def get_mask_path(self, mask_id: str, res_id: str) -> Union[CloudPath, Path]:
        """
        Get mask path from its id and file_id (:code:`R1` for 10m resolution, :code:`R2` for 20m resolution)

        Accepted mask IDs:

        - :code:`DFP`: Defective pixels (do not always exist ! Will raise :code:`InvalidProductError` if not)
        - :code:`EDG`: Nodata pixels mask
        - :code:`SAT`: Saturated pixels mask
        - :code:`MG2`: Geophysical mask (classification)
        - :code:`IAB`: Mask where water vapor and TOA pixels have been interpolated
        - :code:`CLM`: Cloud mask

        Args:
            mask_id (str): Mask ID
            res_id (str): Resolution ID (:code:`R1` or :code:`R2`)

        Returns:
            Union[CloudPath, Path]: Mask path
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
        band: Union[BandNames, str],
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> np.ndarray:
        """
        Open a Sentinel-2 THEIA mask as a numpy array.

        - Opens the saturation and defective mask to the correct bit ID corresponding to the given band.
        - Opens the nodata binary mask
        - Opens the other masks as is

        Do not open cloud mask with this function. Use :code:`load` instead.

        See `here <https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/>`_ for more
        information.

        Accepted mask IDs:

        - :code:`DFP`: Defective pixels
        - :code:`EDG`: Nodata pixels mask
        - :code:`SAT`: Saturated pixels mask
        - :code:`MG2`: Geophysical mask (classification)
        - :code:`IAB`: Mask where water vapor and TOA pixels have been interpolated

        .. code-block:: python

            >>> from eoreader.bands import *
            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
            >>> prod = Reader().open(path)
            >>> prod.open_mask("EDG", GREEN)
            array([[[0, ..., 0]]], dtype=uint8)

        Args:
            mask_id: Mask ID
            band (Union[BandNames, str]): Band name as an SpectralBandNames or resolution ID: ['R1', 'R2']
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            np.ndarray: Mask array

        """
        # https://labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/
        # For r_1, the band order is: B2, B3, B4, B8 and for r_2: B5, B6, B7, B8a, B11, B12
        res_10m = [spb.BLUE, spb.GREEN, spb.RED, spb.NIR, "R1"]
        res_20m = [
            spb.VRE_1,
            spb.VRE_2,
            spb.VRE_3,
            spb.NARROW_NIR,
            spb.SWIR_1,
            spb.SWIR_2,
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
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands list: List of the wanted bands
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
        if resolution is None and size is not None:
            resolution = self._resolution_from_size(size)
        band_paths = self.get_band_paths(bands, resolution=resolution, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, resolution=resolution, size=size, **kwargs
        )

        return band_arrays

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_S2THEIA_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return (
            f"{self.get_datetime()}_S2THEIA_{self.tile_name}_{self.product_type.name}"
        )

    @cache
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
            raise InvalidProductError("Azimuth or Zenith angles not found in metadata!")

        return azimuth_angle, zenith_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
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
        mtd_archived = r"MTD_ALL\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        return True

    def _open_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
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
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if resolution:
            res_file = resolution
        else:
            if size:
                res_file = self._resolution_from_size(size)[0]
            else:
                res_file = self.resolution

        if bands:
            # Open 20m cloud file if resolution >= 20m
            res_id = "R2" if res_file >= 20 else "R1"

            cloud_path = self.get_mask_path("CLM", res_id)
            clouds_mask = utils.read(
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

            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(
                        clouds_mask, [clouds_shadows_id, cirrus_id], nodata
                    )
                elif band == SHADOWS:
                    cloud = self._create_mask(
                        clouds_mask, [shadows_in_id, shadows_out_id], nodata
                    )
                elif band == CLOUDS:
                    cloud = self._create_mask(clouds_mask, clouds_id, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(clouds_mask, cirrus_id, nodata)
                elif band == RAW_CLOUDS:
                    cloud = clouds_mask
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-2 THEIA: {res_id}"
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _create_mask(
        self, bit_array: xr.DataArray, bit_ids: Union[int, list], nodata: np.ndarray
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
        conds = rasters.read_bit_array(bit_array.astype(np.uint8), bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every conditions (bitwise or)

        return super()._create_mask(bit_array, cond, nodata)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing (some providers are providing one quicklook, such as creodias)

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = files.get_archived_rio_path(
                    self.path, file_regex=r".*QKL_ALL\.jpg"
                )
            else:
                quicklook_path = str(next(self.path.glob("**/*QKL_ALL.jpg")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    @cache
    def get_cloud_cover(self) -> float:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_cloud_cover()
            55.5

        Returns:
            float: Cloud cover as given in the metadata
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(".//QUALITY_INDEX[@name='CloudPercent']"))

        except TypeError:
            raise InvalidProductError(
                "QUALITY_INDEXQUALITY_INDEX name='CloudPercent' not found in metadata!"
            )

        return cc
