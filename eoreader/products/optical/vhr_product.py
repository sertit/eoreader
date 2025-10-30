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
from abc import abstractmethod
from typing import Union

import affine
import rasterio
import xarray as xr
from rasterio.crs import CRS
from sertit import AnyPath, rasters
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, utils
from eoreader.bands import BandNames
from eoreader.exceptions import InvalidProductError
from eoreader.products import OpticalProduct

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

                with rasterio.open(str(self._get_tile_path())) as ds:
                    tags = ds.tags()

                    # TODO: change this when available in rioxarray
                    # See https://github.com/corteva/rioxarray/issues/837
                    rpcs = kwargs.pop("rpcs") if "rpcs" in kwargs else ds.rpcs

                    # Only look for GCPs if RPCs are absent
                    if not rpcs:
                        gcps = kwargs.pop("gcps") if "gcps" in kwargs else ds.gcps[0]
                    else:
                        gcps = None

                if not rpcs and not gcps:
                    raise InvalidProductError(
                        "Your projected VHR data doesn't have any RPCs or GCPs. "
                        "EOReader cannot orthorectify it!"
                    )
                else:
                    tile = utils.read(self._get_tile_path())
                    self._orthorectify(
                        tile,
                        rpcs=rpcs,
                        gcps=gcps,
                        dem_path=dem_path,
                        ortho_path=ortho_path,
                        tags=tags,
                        **kwargs,
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
            clean_band = self.get_band_path(band, pixel_size=pixel_size, **kwargs)
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
        resampling = kwargs.pop("resampling", self.band_resampling)

        with rasterio.open(str(band_path)) as dst:
            dst_crs = dst.crs

            # Reproj path in case
            reproj_path = self._get_utm_band_path(band=band.name, pixel_size=pixel_size)

            # Manage the case if we got a LAT LON product
            if not dst_crs.is_projected:
                if not reproj_path.is_file():
                    # Here we are warping the whole stack, not only one band
                    reproj_path = self._get_utm_band_path(
                        pixel_size=pixel_size, writable=True
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
                    resampling=resampling,
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
                    resampling=resampling,
                    **kwargs,
                )

            # Manage the case if we open a stack (native DIMAP bands)
            else:
                # Read band
                band_arr = utils.read(
                    band_path,
                    pixel_size=pixel_size,
                    size=size,
                    resampling=resampling,
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
        band_paths = self.get_band_paths(bands, pixel_size=pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
        )

        return band_arrays

    def _manage_nodata(
        self,
        band_arr: xr.DataArray,
        band: BandNames,
        pixel_size: float = None,
        **kwargs,
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
        band: str = None,
        pixel_size: Union[float, tuple, list] = None,
        writable: bool = False,
    ) -> AnyPathType:
        """
        Create the UTM band path

        Args:
            band (str): Band in string as written on the filepath
            pixel_size (Union[float, tuple, list]): Pixel size of the wanted UTM band
            writable (bool): Do we need to write the UTM band?

        Returns:
            AnyPathType: UTM band path
        """
        res_str = self._pixel_size_to_str(pixel_size)

        band_str = f"_{band}" if band is not None else ""

        return self._get_band_folder(writable).joinpath(
            f"{self.condensed_name}{band_str}_{res_str}.vrt"
        )

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
                        # Here we will warp the whole stack
                        utm_path = self._get_utm_band_path(
                            pixel_size=pixel_size, writable=True
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
