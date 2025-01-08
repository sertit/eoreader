# Copyright 2025, SERTIT-ICube - France, https://sertit.unistra.fr/
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
VHR (very high resoplution) super class.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
for more information.
"""

import logging
import os
from abc import abstractmethod
from typing import Union

import affine
import numpy as np
import rasterio
import xarray as xr
from rasterio import rpc, warp
from rasterio import shutil as rio_shutil
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sertit import AnyPath, path, rasters
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, utils
from eoreader.bands import PAN, BandNames
from eoreader.env_vars import DEM_PATH, TILE_SIZE
from eoreader.exceptions import InvalidProductError
from eoreader.keywords import DEM_KW
from eoreader.products import OpticalProduct
from eoreader.utils import DEFAULT_TILE_SIZE

LOGGER = logging.getLogger(EOREADER_NAME)


class VhrProduct(OpticalProduct):
    """
    Super Class of VHR products.

    Implementing mechanisms for orthorectification, default transform...
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
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
        self._raw_nodata = 0

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # VHR products are stacked
        self.is_stacked = True

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Job ID
        self._job_id = self._get_job_id()

        # Post init done by the super class
        super()._post_init(**kwargs)

    def get_default_band_path(self, **kwargs) -> AnyPathType:
        """
        Get default band (:code:`GREEN` for optical data) path.

        .. WARNING:
            If you are using a non orthorectified product, this function will orthorectify the stack.
            To do so, you **MUST** provide a DEM through the EOREADER_DEM_PATH environment variable

        .. WARNING:
            If you are using a non-projected product, this function will reproject the stack.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_default_band_path()
            'IMG_PHR1A_PMS_001/DIM_PHR1A_PMS_202005110231585_ORT_5547047101.XML'

        Args:
            kwargs: Additional arguments
        Returns:
            AnyPathType: Default band path
        """
        return self._get_default_utm_band(self.pixel_size, **kwargs)

    @abstractmethod
    def _get_raw_crs(self) -> CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        raise NotImplementedError

    def _get_ortho_path(self, **kwargs) -> AnyPathType:
        """
        Get the orthorectified path of the bands.

        Returns:
            AnyPathType: Orthorectified path
        """
        if self.product_type in self._proj_prod_type:
            ortho_name = f"{self.condensed_name}_ortho.tif"

            ortho_path, ortho_exists = self._get_out_path(ortho_name)
            if not ortho_exists:
                LOGGER.info(
                    "Manually orthorectified stack not given by the user. "
                    "Reprojecting whole stack, this may take a while. "
                    "(Might be inaccurate on steep terrain, depending on the DEM pixel size)."
                )

                # Reproject and write on disk data
                dem_path = self._get_dem_path(**kwargs)

                with rasterio.open(self._get_tile_path()) as ds:
                    tags = ds.tags()

                    # TODO: change this when available in rioxarray
                    # See https://github.com/corteva/rioxarray/issues/837
                    rpcs = kwargs.pop("rpcs") if "rpcs" in kwargs else ds.rpcs

                if not rpcs:
                    raise InvalidProductError(
                        "Your projected VHR data doesn't have any RPC. "
                        "EOReader cannot orthorectify it!"
                    )

                tile = utils.read(self._get_tile_path())
                tile = self._reproject(tile, rpcs, dem_path, **kwargs)
                utils.write(
                    tile,
                    ortho_path,
                    dtype=np.float32,
                    nodata=self._raw_nodata,
                    tags=tags,
                )

        else:
            ortho_path = self._get_tile_path()

        return ortho_path

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
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
            pixel_size (float): Band pixel size
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
                band, pixel_size=pixel_size, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                # First look for reprojected bands
                reproj_path = self._get_utm_band_path(
                    band=band.name, pixel_size=pixel_size
                )
                if not reproj_path.is_file():
                    # Then for original data
                    band_path = self.ortho_path
                else:
                    band_path = reproj_path

                band_paths[band] = band_path

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
            if path.is_cloud_path(dem_path):
                raise ValueError(
                    "gdalwarp cannot process DEM stored on cloud with 'RPC_DEM' argument, "
                    "hence cloud-stored DEM cannot be used with non orthorectified DIMAP data."
                    f"(DEM: {dem_path}, DIMAP data: {self.name})"
                )

        return dem_path

    def _reproject(
        self, src_xda: xr.DataArray, rpcs: rpc.RPC, dem_path, **kwargs
    ) -> (np.ndarray, dict):
        """
        Reproject using RPCs (cannot use another pixel size than src to ensure RPCs are valid)

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
        kwargs.update(
            {
                "RPC_DEM": dem_path,
                "RPC_DEM_MISSING_VALUE": 0,
                "OSR_USE_ETMERC": "YES",
                "BIGTIFF": "IF_NEEDED",
            }
        )

        # Reproject with rioxarray
        # Seems to handle the resolution well on the contrary to rasterio's reproject...
        if src_xda.rio.crs is None:
            src_xda.rio.write_crs(self._get_raw_crs(), inplace=True)

        out_xda = src_xda.rio.reproject(
            dst_crs=self.crs(),
            resolution=self.pixel_size,
            resampling=Resampling.bilinear,
            nodata=self._raw_nodata,
            num_threads=utils.get_max_cores(),
            rpcs=rpcs,
            dtype=src_xda.dtype,
            **kwargs,
        )
        out_xda.rename(f"Reprojected stack of {self.name}")

        if kwargs.get("band") == PAN:
            out_xda.attrs["long_name"] = "PAN"
        else:
            out_xda.attrs["long_name"] = self.get_bands_names()

        # Daskified reproject doesn't seem to work with RPC
        # See https://github.com/opendatacube/odc-geo/issues/193
        # from odc.geo import xr # noqa
        # out_xda = src_xda.odc.reproject(
        #     how=self.crs(),
        #     resolution=self.pixel_size,
        #     resampling=Resampling.bilinear,
        #     dst_nodata=self._raw_nodata,
        #     num_threads=utils.get_max_cores(),
        #     rpcs=rpcs,
        #     dtype=src_xda.dtype,
        #     **kwargs
        # )

        # Legacy with rasterio directly
        # WARNING: may not give correct output pixel size
        # out_arr, dst_transform = warp.reproject(
        #     src_arr,
        #     rpcs=rpcs,
        #     src_crs=self._get_raw_crs(),
        #     src_nodata=self._raw_nodata,
        #     dst_crs=self.crs(),
        #     dst_resolution=self.pixel_size,
        #     dst_nodata=self._raw_nodata,  # input data should be in integer
        #     num_threads=utils.get_max_cores(),
        #     resampling=Resampling.bilinear,
        #     **kwargs,
        # )
        # # Get dims
        # count, height, width = out_arr.shape
        #
        # # Update metadata
        # meta = src_meta.copy()
        # meta["transform"] = dst_transform
        # meta["driver"] = "GTiff"
        # meta["compress"] = "lzw"
        # meta["nodata"] = self._raw_nodata
        # meta["crs"] = self.crs()
        # meta["width"] = width
        # meta["height"] = height
        # meta["count"] = count

        return out_xda

    def _read_band(
        self,
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            pixel_size (Union[tuple, list, float]): Size of the pixels of the wanted band, in dataset unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray
        """
        with rasterio.open(str(band_path)) as dst:
            dst_crs = dst.crs

            # Compute pixel_size from size (if needed)
            if pixel_size is None and size is not None:
                pixel_size = self._pixel_size_from_img_size(size)

            # Reproj path in case
            reproj_path = self._get_utm_band_path(band=band.name, pixel_size=pixel_size)

            # Manage the case if we got a LAT LON product
            if not dst_crs.is_projected:
                if not reproj_path.is_file():
                    reproj_path = self._get_utm_band_path(
                        band=band.name, pixel_size=pixel_size, writable=True
                    )
                    # Warp band if needed
                    self._warp_band(
                        band_path,
                        reproj_path=reproj_path,
                        pixel_size=pixel_size,
                    )

                # Read band
                LOGGER.debug(f"Reading warped {band.name}.")
                band_arr = utils.read(
                    reproj_path,
                    pixel_size=pixel_size,
                    size=size,
                    resampling=Resampling.bilinear,
                    indexes=[self.bands[band].id],
                    **kwargs,
                )

            # Manage the case if we open a simple band (EOReader processed bands)
            elif dst.count == 1:
                # Read band
                band_arr = utils.read(
                    band_path,
                    pixel_size=pixel_size,
                    size=size,
                    resampling=Resampling.bilinear,
                    **kwargs,
                )

            # Manage the case if we open a stack (native DIMAP bands)
            else:
                # Read band
                band_arr = utils.read(
                    band_path,
                    pixel_size=pixel_size,
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
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands list: List of the wanted bands
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Other arguments used to load bands
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if pixel_size is None and size is not None:
            pixel_size = self._pixel_size_from_img_size(size)
        band_paths = self.get_band_paths(bands, pixel_size=pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
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
            band_arr = rasters.set_nodata(band_arr, self._raw_nodata)

        return band_arr

    def _get_condensed_name(self) -> str:
        """
        Get PlanetScope products condensed name ({date}_PLD_{product_type}_{band_combi}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{self.band_combi.name}_{self._job_id}"

    def _get_path(self, filename: str = "", extension: str = "") -> AnyPathType:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension

        Returns:
            Union[list, AnyPathType]: Path or list of paths (needs this because of potential mosaic)

        """
        prod_path = []
        try:
            if filename and not filename.startswith("*"):
                filename = f"*{filename}"

            if self.is_archived:
                prod_path = self._get_archived_rio_path(
                    rf".{filename}.*\.{extension}",
                )
            else:
                prod_path = next(self.path.glob(f"{filename}*.{extension}"))

        except (FileNotFoundError, IndexError, StopIteration) as exc:
            raise InvalidProductError(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            ) from exc

        return prod_path

    def _get_utm_band_path(
        self,
        band: str,
        pixel_size: Union[float, tuple, list] = None,
        writable: bool = False,
    ) -> AnyPathType:
        """
        Create the UTM band path

        Args:
            band (str): Band in string as written on the filepath
            pixel_size (Union[float, tuple, list]): Pixel size of the wanted UTM band
            writable (bool): Do we need to write the UTM band ?

        Returns:
            AnyPathType: UTM band path
        """
        res_str = self._pixel_size_to_str(pixel_size)

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}_{band}_{res_str}.vrt"
        )

    def _warp_band(
        self,
        band_path: AnyPathStrType,
        reproj_path: AnyPathStrType,
        pixel_size: float = None,
    ) -> None:
        """
        Warp band to UTM

        Args:
            band_path (AnyPathStrType): Band path to warp
            reproj_path (AnyPathStrType): Path where to write the reprojected band
            pixel_size (int): Band pixel size in meters

        """
        # Do not warp if existing file
        if reproj_path.is_file():
            return

        if not pixel_size:
            pixel_size = self.pixel_size

        LOGGER.info(
            f"Warping {path.get_filename(band_path)} to UTM with a {pixel_size} m pixel size."
        )

        # Read band
        with rasterio.open(str(band_path)) as src:
            # Calculate transform
            utm_tr, utm_w, utm_h = warp.calculate_default_transform(
                src.crs,
                self.crs(),
                src.width,
                src.height,
                *src.bounds,
                resolution=pixel_size,
            )

            try:
                tile_size = int(os.getenv(TILE_SIZE, DEFAULT_TILE_SIZE))
            except ValueError:
                tile_size = int(DEFAULT_TILE_SIZE)

            vrt_options = {
                "crs": self.crs(),
                "transform": utm_tr,
                "height": utm_h,
                "width": utm_w,
                # TODO: go nearest to speed up results ?
                "resampling": Resampling.bilinear,
                "nodata": self._raw_nodata,
                # Float32 is the max possible
                "warp_mem_limit": 32 * tile_size**2 / 1e6,
                "dtype": src.meta["dtype"],
                "num_threads": utils.get_max_cores(),
            }
            with (
                rasterio.Env(
                    **{"GDAL_NUM_THREADS": "ALL_CPUS", "NUM_THREADS": "ALL_CPUS"}
                ),
                WarpedVRT(src, **vrt_options) as vrt,
            ):
                rio_shutil.copy(vrt, reproj_path, driver="vrt")

    def _get_default_utm_band(
        self, pixel_size: float = None, size: Union[list, tuple] = None
    ) -> AnyPathType:
        """
        Get the default UTM band:
        - If one already exists, get it
        - If not, create reproject (if needed) the GREEN band

        Args:
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            str: Default UTM path
        """
        # Manage pixel_size
        if pixel_size is None and size is not None:
            pixel_size = self._pixel_size_from_img_size(size)
        def_res = pixel_size if pixel_size else self.pixel_size

        # Get default band path
        default_band = self.get_default_band()
        def_path = self.get_band_paths([default_band], pixel_size=def_res)[default_band]

        # First look for reprojected bands
        res_str = self._pixel_size_to_str(pixel_size)
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
                    utm_path = self._get_utm_band_path(
                        band=def_band.name, pixel_size=pixel_size
                    )

                    # Warp band if needed
                    if not utm_path.is_file():
                        utm_path = self._get_utm_band_path(
                            band=def_band.name, pixel_size=pixel_size, writable=True
                        )
                        self._warp_band(
                            def_path,
                            reproj_path=utm_path,
                            pixel_size=pixel_size,
                        )
                else:
                    utm_path = def_path
            else:
                utm_path = AnyPath(reproj_bands[0])
        else:
            utm_path = AnyPath(reproj_bands[0])

        return utm_path

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
            Affine, int, int, CRS: transform, width, height, CRS

        """
        default_band = self.get_default_band()
        def_path = self.get_band_paths(
            [default_band], pixel_size=self.pixel_size, **kwargs
        )[default_band]
        with rasterio.open(str(def_path)) as dst:
            return dst.transform, dst.width, dst.height, dst.crs

    @abstractmethod
    def _get_tile_path(self) -> AnyPathType:
        """
        Get the VHR tile path

        Returns:
            AnyPathType: VHR filepath
        """
        raise NotImplementedError

    @abstractmethod
    def _get_job_id(self) -> AnyPathType:
        """
        Get VHR job ID

        Returns:
            AnyPathType: VHR product ID
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
