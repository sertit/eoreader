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
Maxar super class.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
for more information.
"""
import logging
import math
import os
from abc import abstractmethod
from pathlib import Path
from typing import Union

import affine
import geopandas as gpd
import numpy as np
import rasterio
from cloudpathlib import AnyPath, CloudPath
from rasterio import rpc, transform, warp
from rasterio.crs import CRS
from rasterio.enums import Resampling
from sertit import files, rasters, rasters_rio
from sertit.rasters import XDS_TYPE
from sertit.snap import MAX_CORES
from sertit.vectors import WGS84
from shapely.geometry import box

from eoreader import cached_property, utils
from eoreader.bands.bands import BandNames
from eoreader.env_vars import DEM_PATH
from eoreader.products import OpticalProduct
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


class VhrProduct(OpticalProduct):
    """
    Super Class of VHR products.

    Implementing mechanisms for orthorectification, default transform...
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        self.ortho_path = None
        """
        Orthorectified path.
        Can be set to use manually orthorectified or pansharpened data, especially useful for VHR data on steep terrain.
        """

        # Order id (product name more or less)
        self._order_id = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp)

    @abstractmethod
    def _get_raw_crs(self) -> CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def get_default_band_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get default band (:code:`GREEN` for optical data) path.

        .. WARNING:
            If you are using a non orthorectified product, this function will orthorectify the stack.
            To do so, you **MUST** provide a DEM trough the EOREADER_DEM_PATH environment variable

        .. WARNING:
            If you are using a non projected product, this function will reproject the stack.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band_path()
            'IMG_PHR1A_PMS_001/DIM_PHR1A_PMS_202005110231585_ORT_5547047101.XML'

        Args:
            kwargs: Additional arguments
        Returns:
            Union[CloudPath, Path]: Default band path
        """
        return self._get_default_utm_band(self.resolution, **kwargs)

    @cached_property
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                                        geometry
            0  POLYGON ((309780.000 4390200.000, 309780.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        def_tr, def_w, def_h, def_crs = self.default_transform()
        bounds = transform.array_bounds(def_h, def_w, def_tr)
        return gpd.GeoDataFrame(geometry=[box(*bounds)], crs=def_crs).to_crs(self.crs)

    @abstractmethod
    def _get_ortho_path(self) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """

        raise NotImplementedError("This method should be implemented by a child class")

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <OpticalBandNames.GREEN: 'GREEN'>:
                'IMG_PHR1A_PMS_001/DIM_PHR1A_PMS_202005110231585_ORT_5547047101.XML',
                <OpticalBandNames.RED: 'RED'>:
                'IMG_PHR1A_PMS_001/DIM_PHR1A_PMS_202005110231585_ORT_5547047101.XML'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        if not self.ortho_path:
            self.ortho_path = self._get_ortho_path()

        # Processed path names
        band_paths = {}
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, resolution=resolution, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                # First look for reprojected bands
                reproj_path = self._create_utm_band_path(
                    band=band.name, resolution=resolution
                )
                if not reproj_path.is_file():
                    # Then for original data
                    path = self.ortho_path
                else:
                    path = reproj_path

                band_paths[band] = path

        return band_paths

    def _reproject(
        self, src_arr: np.ndarray, src_meta: dict, rpcs: rpc.RPC
    ) -> (np.ndarray, dict):
        """
        Reproject using RPCs

        Args:
            src_arr (np.ndarray): Array to reproject
            src_meta (dict): Metadata
            rpcs (rpc.RPC): RPCs

        Returns:
            (np.ndarray, dict): Reprojected array and its metadata
        """
        # Get DEM path
        dem_path = os.environ.get(DEM_PATH)
        if not dem_path:
            raise ValueError(
                f"You are using a non orthorectified Pleiades product {self.path}, "
                f"you must provide a valid DEM through the {DEM_PATH} environment variable"
            )
        else:
            dem_path = AnyPath(dem_path)
            if isinstance(dem_path, CloudPath):
                raise TypeError(
                    "gdalwarp cannot process DEM stored on cloud with 'RPC_DEM' argument, "
                    "hence cloud-stored DEM cannot be used with non orthorectified DIMAP data."
                    f"(DEM: {dem_path}, DIMAP data: {self.name})"
                )

        # Set RPC keywords
        kwargs = {"RPC_DEM": dem_path, "RPC_DEM_MISSING_VALUE": 0}
        # TODO:  add "refine_gcps" ? With which tolerance ? (ie. '-refine_gcps 500 1.9')
        #  (https://gdal.org/programs/gdalwarp.html#cmdoption-gdalwarp-refine_gcps)

        # Reproject
        # WARNING: may not give correct output resolution
        out_arr, dst_transform = warp.reproject(
            src_arr,
            rpcs=rpcs,
            src_crs=WGS84,
            dst_crs=self.crs,
            resolution=self.resolution,
            src_nodata=0,
            dst_nodata=0,  # input data should be in integer
            num_threads=MAX_CORES,
            resampling=Resampling.bilinear,
            **kwargs,
        )
        # Get dims
        count, height, width = out_arr.shape

        # Update metadata
        meta = src_meta.copy()
        meta["transform"] = dst_transform
        meta["driver"] = "GTiff"
        meta["compress"] = "lzw"
        meta["nodata"] = 0
        meta["crs"] = self.crs
        meta["width"] = width
        meta["height"] = height
        meta["count"] = count

        # Just in case, read the array with the most appropriate resolution
        # as the warping sometimes gives not the closest resolution possible to the wanted one
        if not math.isclose(dst_transform.a, self.resolution, rel_tol=1e-4):
            out_arr, meta = rasters_rio.read(
                (out_arr, meta), resolution=self.resolution
            )

        return out_arr, meta

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
        with rasterio.open(str(path)) as dst:
            dst_crs = dst.crs

            # Compute resolution from size (if needed)
            if resolution is None and size is not None:
                resolution = self._resolution_from_size(size)

            # Reproj path in case
            reproj_path = self._create_utm_band_path(
                band=band.name, resolution=resolution
            )

            # Manage the case if we got a LAT LON product
            if not dst_crs.is_projected:
                if not reproj_path.is_file():
                    reproj_path = self._create_utm_band_path(
                        band=band.name, resolution=resolution, writable=True
                    )
                    # Warp band if needed
                    self._warp_band(
                        path,
                        band,
                        reproj_path=reproj_path,
                        resolution=resolution,
                    )

                # Read band
                band_xda = utils.read(
                    reproj_path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    **kwargs,
                )

            # Manage the case if we open a simple band (EOReader processed bands)
            elif dst.count == 1:
                # Read band
                band_xda = utils.read(
                    path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    **kwargs,
                )

            # Manage the case if we open a stack (native DIMAP bands)
            else:
                # Read band
                band_xda = utils.read(
                    path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    indexes=[self.band_names[band]],
                    **kwargs,
                )

            # If nodata not set, set it here
            if not band_xda.rio.encoded_nodata:
                band_xda = rasters.set_nodata(band_xda, 0)

            # Compute the correct radiometry of the band
            if dst.meta["dtype"] == "uint16":
                band_xda /= 10000.0

            # Pop useless long name
            if "long_name" in band_xda.attrs:
                band_xda.attrs.pop("long_name")

            # To float32
            if band_xda.dtype != np.float32:
                band_xda = band_xda.astype(np.float32)

        return band_xda

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
        band_paths = self.get_band_paths(bands, resolution=resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, resolution=resolution, size=size, **kwargs
        )

        return band_arrays

    def _get_path(
        self, filename: str = "", extension: str = ""
    ) -> Union[CloudPath, Path]:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension

        Returns:
            Union[list, CloudPath, Path]: Path or list of paths (needs this because of potential mosaic)

        """
        path = []
        try:
            if filename and not filename.startswith("*"):
                filename = f"*{filename}"

            if self.is_archived:
                path = files.get_archived_rio_path(
                    self.path,
                    f".{filename}.*\.{extension}",
                )
            else:
                path = next(self.path.glob(f"{filename}*.{extension}"))

        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return path

    def _create_utm_band_path(
        self,
        band: str,
        resolution: Union[float, tuple, list] = None,
        writable: bool = False,
    ) -> Union[CloudPath, Path]:
        """
        Create the UTM band path

        Args:
            band (str): Band in string as written on the filepath
            resolution (Union[float, tuple, list]): Resolution of the wanted UTM band
            writable (bool): Do we need to write the UTM band ?

        Returns:
            Union[CloudPath, Path]: UTM band path
        """
        res_str = self._resolution_to_str(resolution)

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band}_{res_str}.tif"
        )

    def _warp_band(
        self,
        path: Union[str, CloudPath, Path],
        band: BandNames,
        reproj_path: Union[str, CloudPath, Path],
        resolution: float = None,
    ) -> None:
        """
        Warp band to UTM

        Args:
            path (Union[str, CloudPath, Path]): Band path to warp
            band (band): Band to warp
            reproj_path (Union[str, CloudPath, Path]): Path where to write the reprojected band
            resolution (int): Band resolution in meters

        """
        # Do not warp if existing file
        if reproj_path.is_file():
            return

        if not resolution:
            resolution = self.resolution

        LOGGER.info(
            f"Reprojecting band {band.name} to UTM with a {resolution} m resolution."
        )

        # Read band
        with rasterio.open(str(path)) as src:
            band_nb = self.band_names[band]
            meta = src.meta.copy()

            utm_tr, utm_w, utm_h = warp.calculate_default_transform(
                src.crs,
                self.crs,
                src.width,
                src.height,
                *src.bounds,
                resolution=resolution,
            )

            # If nodata not set, set it here
            meta["nodata"] = 0

            # If the CRS is not in UTM, reproject it
            out_arr = np.empty((1, utm_h, utm_w), dtype=meta["dtype"])
            warp.reproject(
                source=src.read(band_nb),
                destination=out_arr,
                src_crs=src.crs,
                dst_crs=self.crs,
                src_transform=src.transform,
                dst_transform=utm_tr,
                src_nodata=0,
                dst_nodata=0,  # input data should be in integer
                num_threads=MAX_CORES,
            )
            meta["transform"] = utm_tr
            meta["crs"] = self.crs
            meta["driver"] = "GTiff"

            rasters_rio.write(out_arr, meta, reproj_path)

    def _get_default_utm_band(
        self, resolution: float = None, size: Union[list, tuple] = None
    ) -> Union[CloudPath, Path]:
        """
        Get the default UTM band:
        - If one already exists, get it
        - If not, create reproject (if needed) the GREEN band

        Args:
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            str: Default UTM path
        """
        # Manage resolution
        if resolution is None and size is not None:
            resolution = self._resolution_from_size(size)
        def_res = resolution if resolution else self.resolution

        # Get default band path
        default_band = self.get_default_band()
        def_path = self.get_band_paths([default_band], resolution=def_res)[default_band]

        # First look for reprojected bands
        res_str = self._resolution_to_str(resolution)
        warped_regex = f"*{self.condensed_name}_*_{res_str}.tif"
        reproj_bands = list(self._get_band_folder().glob(warped_regex))

        if len(reproj_bands) == 0:

            # Check in the writeable band folder
            reproj_bands = list(self._get_band_folder(writable=True).glob(warped_regex))

            if len(reproj_bands) == 0:
                # Manage the case if we got a LAT LON product
                with rasterio.open(str(def_path)) as dst:
                    dst_crs = dst.crs

                if not dst_crs.is_projected:
                    def_band = self.get_default_band()
                    path = self._create_utm_band_path(
                        band=def_band.name, resolution=resolution
                    )

                    # Warp band if needed
                    if not path.is_file():
                        path = self._create_utm_band_path(
                            band=def_band.name, resolution=resolution, writable=True
                        )
                        self._warp_band(
                            def_path,
                            def_band,
                            reproj_path=path,
                            resolution=resolution,
                        )
                else:
                    path = def_path
            else:
                path = AnyPath(reproj_bands[0])
        else:
            path = AnyPath(reproj_bands[0])

        return path

    def default_transform(self, **kwargs) -> (affine.Affine, int, int, CRS):
        """
        Returns default transform data of the default band (UTM),
        as the :code:`rasterio.warp.calculate_default_transform` does:
        - transform
        - width
        - height
        - CRS

        Overload in order not to reproject WGS84 data

        Args:
            kwargs: Additional arguments

        Returns:
            Affine, int, int: transform, width, height

        """
        default_band = self.get_default_band()
        def_path = self.get_band_paths(
            [default_band], resolution=self.resolution, **kwargs
        )[default_band]
        with rasterio.open(str(def_path)) as dst:
            return dst.transform, dst.width, dst.height, dst.crs
