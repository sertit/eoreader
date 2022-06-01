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
import numpy as np
import rasterio
import xarray as xr
from cloudpathlib import AnyPath, CloudPath
from rasterio import rpc, warp
from rasterio.crs import CRS
from rasterio.enums import Resampling
from sertit import files, rasters, rasters_rio
from sertit.snap import MAX_CORES

from eoreader import utils
from eoreader.bands.bands import BandNames
from eoreader.env_vars import DEM_PATH
from eoreader.exceptions import InvalidProductError
from eoreader.keywords import DEM_KW
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
        **kwargs,
    ) -> None:
        self.ortho_path = None
        """
        Orthorectified path.
        Can be set to use manually orthorectified or pansharpened data, especially useful for VHR data on steep terrain.
        """

        self._proj_prod_type = []

        self.band_combi = None
        """
        Band combination, i.e. PAN, PMS, MS...
        """

        # Order id (product name more or less)
        self._order_id = None

        # Resolutions
        self._pan_res = None
        self._ms_res = None

        self._job_id = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Job ID
        self._job_id = self._get_job_id()

        # Post init done by the super class
        super()._post_init(**kwargs)

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

    @abstractmethod
    def _get_raw_crs(self) -> CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        raise NotImplementedError

    def _get_ortho_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """
        if self.product_type in self._proj_prod_type:
            ortho_name = f"{self.condensed_name}_ortho.tif"
            ortho_path = self._get_band_folder().joinpath(ortho_name)
            if not ortho_path.is_file():
                ortho_path = self._get_band_folder(writable=True).joinpath(ortho_name)
                LOGGER.info(
                    "Manually orthorectified stack not given by the user. "
                    "Reprojecting whole stack, this may take a while. "
                    "(May be inaccurate on steep terrain, depending on the DEM resolution)"
                )

                # Reproject and write on disk data
                dem_path = self._get_dem_path(**kwargs)
                with rasterio.open(str(self._get_tile_path())) as src:
                    if "rpcs" in kwargs:
                        rpcs = kwargs.pop("rpcs")
                    else:
                        rpcs = src.rpcs

                    if not rpcs:
                        raise InvalidProductError(
                            "Your projected VHR data doesn't have any RPC. "
                            "EOReader cannot orthorectify it!"
                        )

                    out_arr, meta = self._reproject(
                        src.read(), src.meta, rpcs, dem_path, **kwargs
                    )
                    rasters_rio.write(out_arr, meta, ortho_path)

        else:
            ortho_path = self._get_tile_path()

        return ortho_path

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
                <SpectralBandNames.GREEN: 'GREEN'>:
                'IMG_PHR1A_PMS_001/DIM_PHR1A_PMS_202005110231585_ORT_5547047101.XML',
                <SpectralBandNames.RED: 'RED'>:
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
            self.ortho_path = self._get_ortho_path(**kwargs)

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
                reproj_path = self._get_utm_band_path(
                    band=band.name, resolution=resolution
                )
                if not reproj_path.is_file():
                    # Then for original data
                    path = self.ortho_path
                else:
                    path = reproj_path

                band_paths[band] = path

        return band_paths

    def _get_dem_path(self, **kwargs) -> str:
        """
        Get DEM path

        Returns:
            str: DEM path

        """
        # Get DEM path
        dem_path = os.environ.get(DEM_PATH, kwargs.get(DEM_KW))
        if not dem_path:
            raise ValueError(
                f"As you are using a non orthorectified VHR product ({self.path}), "
                f"you must provide a valid DEM through the {DEM_PATH} environment variable"
            )
        else:
            if isinstance(AnyPath(dem_path), CloudPath):
                raise ValueError(
                    "gdalwarp cannot process DEM stored on cloud with 'RPC_DEM' argument, "
                    "hence cloud-stored DEM cannot be used with non orthorectified DIMAP data."
                    f"(DEM: {dem_path}, DIMAP data: {self.name})"
                )

        return dem_path

    def _reproject(
        self, src_arr: np.ndarray, src_meta: dict, rpcs: rpc.RPC, dem_path, **kwargs
    ) -> (np.ndarray, dict):
        """
        Reproject using RPCs (cannot use another resolution than src to ensure RPCs are valid)

        Args:
            src_arr (np.ndarray): Array to reproject
            src_meta (dict): Metadata
            rpcs (rpc.RPC): RPCs
            dem_path (str): DEM path

        Returns:
            (np.ndarray, dict): Reprojected array and its metadata
        """

        # Set RPC keywords
        LOGGER.debug(f"Orthorectifying data with {dem_path}")
        kwargs = {
            "RPC_DEM": dem_path,
            "RPC_DEM_MISSING_VALUE": 0,
            "OSR_USE_ETMERC": "YES",
        }

        # Reproject
        # WARNING: may not give correct output resolution
        out_arr, dst_transform = warp.reproject(
            src_arr,
            rpcs=rpcs,
            src_crs=self._get_raw_crs(),
            dst_crs=self.crs(),
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
        meta["crs"] = self.crs()
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
        with rasterio.open(str(path)) as dst:
            dst_crs = dst.crs

            # Compute resolution from size (if needed)
            if resolution is None and size is not None:
                resolution = self._resolution_from_size(size)

            # Reproj path in case
            reproj_path = self._get_utm_band_path(band=band.name, resolution=resolution)

            # Manage the case if we got a LAT LON product
            if not dst_crs.is_projected:
                if not reproj_path.is_file():
                    reproj_path = self._get_utm_band_path(
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
                band_arr = utils.read(
                    reproj_path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    **kwargs,
                )

            # Manage the case if we open a simple band (EOReader processed bands)
            elif dst.count == 1:
                # Read band
                band_arr = utils.read(
                    path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    **kwargs,
                )

            # Manage the case if we open a stack (native DIMAP bands)
            else:
                # Read band
                band_arr = utils.read(
                    path,
                    resolution=resolution,
                    size=size,
                    resampling=Resampling.bilinear,
                    indexes=[self.bands[band].id],
                    **kwargs,
                )

        # Pop useless long name
        if "long_name" in band_arr.attrs:
            band_arr.attrs.pop("long_name")

        return band_arr

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

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        return self._manage_nodata(band_arr, band, **kwargs)

    def _manage_nodata(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage only nodata pixels

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # If nodata not set, set it here
        if not band_arr.rio.encoded_nodata:
            band_arr = rasters.set_nodata(band_arr, 0)

        return band_arr

    def _get_condensed_name(self) -> str:
        """
        Get PlanetScope products condensed name ({date}_PLD_{product_type}_{band_combi}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{self.band_combi.name}_{self._job_id}"

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
                    rf".{filename}.*\.{extension}",
                )
            else:
                path = next(self.path.glob(f"{filename}*.{extension}"))

        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return path

    def _get_utm_band_path(
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
            band_id = self.bands[band].id
            meta = src.meta.copy()

            utm_tr, utm_w, utm_h = warp.calculate_default_transform(
                src.crs,
                self.crs(),
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
                source=src.read(band_id),
                destination=out_arr,
                src_crs=src.crs,
                dst_crs=self.crs(),
                src_transform=src.transform,
                dst_transform=utm_tr,
                src_nodata=0,
                dst_nodata=0,  # input data should be in integer
                num_threads=MAX_CORES,
            )
            meta["transform"] = utm_tr
            meta["crs"] = self.crs()
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
                    path = self._get_utm_band_path(
                        band=def_band.name, resolution=resolution
                    )

                    # Warp band if needed
                    if not path.is_file():
                        path = self._get_utm_band_path(
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

    @abstractmethod
    def _get_tile_path(self) -> Union[CloudPath, Path]:
        """
        Get the VHR tile path

        Returns:
            Union[CloudPath, Path]: VHR filepath
        """
        raise NotImplementedError

    @abstractmethod
    def _get_job_id(self) -> Union[CloudPath, Path]:
        """
        Get VHR job ID

        Returns:
            Union[CloudPath, Path]: VHR product ID
        """
        raise NotImplementedError

    def get_raw_band_paths(self, **kwargs) -> dict:
        """
        Return the raw band paths.

        Args:
            kwargs: Additional arguments

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        raw_band_paths = {}
        for band in self.get_existing_bands():
            raw_band_paths[band] = self._get_tile_path()
        return raw_band_paths
