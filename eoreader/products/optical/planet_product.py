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
Super-class of Planet products.
See
`Earth Online <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
for more information.
"""
import logging
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from rasterio.enums import Resampling
from sertit import files, rasters

from eoreader import cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    CIRRUS,
    CLOUDS,
    RAW_CLOUDS,
    SHADOWS,
    BandNames,
    to_str,
)
from eoreader.exceptions import InvalidTypeError
from eoreader.products import OpticalProduct
from eoreader.utils import EOREADER_NAME, simplify

LOGGER = logging.getLogger(EOREADER_NAME)


class PlanetProduct(OpticalProduct):
    """
    Super-class of Planet products.
    See
    `Earth Online <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Post init done by the super class
        super()._pre_init(**kwargs)

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

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
        nodata = self._load_nodata()

        # Vectorize the nodata band (rasters_rio is faster)
        footprint = rasters.vectorize(
            nodata, values=1, keep_values=False, dissolve=True
        ).convex_hull

        return gpd.GeoDataFrame(geometry=footprint.geometry, crs=footprint.crs)

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
        # Read band
        band_arr = utils.read(
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
            indexes=[self.bands[band].id],
            **kwargs,
        )

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See
        `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
        (unusable data mask) for more information.

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as a SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # Nodata
        no_data_mask = self._load_nodata(
            size=(band_arr.rio.width, band_arr.rio.height)
        ).values

        # Dubious pixels mapping
        dubious_bands = {
            key: val.id + 1 for key, val in self.bands.items() if val is not None
        }
        udm = self.open_mask("UNUSABLE", size=(band_arr.rio.width, band_arr.rio.height))
        # Workaround:
        # FutureWarning: The :code:`numpy.expand_dims` function is not implemented by Dask array.
        # You may want to use the da.map_blocks function or something similar to silence this warning.
        # Your code may stop working in a future release.
        dubious_mask = rasters.read_bit_array(udm.values, dubious_bands[band])

        # Combine masks
        mask = no_data_mask | dubious_mask

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
        # Nodata
        no_data_mask = self._load_nodata(
            size=(band_arr.rio.width, band_arr.rio.height)
        ).values

        # -- Merge masks
        return self._set_nodata_mask(band_arr, no_data_mask)

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
        band_paths = self.get_band_paths(bands, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, resolution=resolution, size=size, **kwargs
        )

        return band_arrays

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        # NOTE: CIRRUS == HEAVY HAZE

        # FROM DOCUMENTATION: https://developers.planet.com/docs/data/udm-2/
        # Percent of heavy haze values in dataset.
        # Heavy haze values represent scene content areas (non-blackfilled) that contain thin low altitude clouds,
        # higher altitude cirrus clouds, soot and dust which allow fair recognition of land cover features,
        # but not having reliable interpretation of the radiometry or surface reflectance.
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

        CIRRUS is HEAVY_HAZE

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        # Load default xarray as a template
        def_xarr = self._read_band(
            self.get_default_band_path(),
            band=self.get_default_band(),
            resolution=resolution,
            size=size,
        )

        # Load nodata
        nodata = self._load_nodata(resolution, size).data

        if bands:
            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(
                        def_xarr.rename(ALL_CLOUDS.name),
                        (
                            self.open_mask("CLOUD", resolution, size).data
                            & self.open_mask("SHADOW", resolution, size).data
                            & self.open_mask("HEAVY_HAZE", resolution, size).data
                        ),
                        nodata,
                    )
                elif band == SHADOWS:
                    cloud = self._create_mask(
                        def_xarr.rename(SHADOWS.name),
                        self.open_mask("SHADOW", resolution, size).data,
                        nodata,
                    )
                elif band == CLOUDS:
                    cloud = self._create_mask(
                        def_xarr.rename(CLOUDS.name),
                        self.open_mask("CLOUD", resolution, size).data,
                        nodata,
                    )
                elif band == CIRRUS:
                    cloud = self._create_mask(
                        def_xarr.rename(CIRRUS.name),
                        self.open_mask("HEAVY_HAZE", resolution, size).data,
                        nodata,
                    )
                elif band == RAW_CLOUDS:
                    cloud = utils.read(self._get_path("udm2", "tif"), resolution, size)
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Planet: {band}"
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def open_mask(
        self,
        mask_id: str,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> Union[xr.DataArray, None]:
        """
        Open a Planet UDM2 (Usable Data Mask) mask, band by band, as a xarray.
        Returns None if the mask is not available.

        Do not open cloud mask with this function. Use :code:`load` instead.

        See `here <https://developers.planet.com/docs/data/udm-2/>`_ for more
        information.

        Accepted mask IDs:

        - :code:`CLEAR`:      Band 1     Clear map        [0, 1]  0: not clear, 1: clear
        - :code:`SNOW`:       Band 2     Snow map         [0, 1]  0: no snow or ice, 1: snow or ice
        - :code:`SHADOW`:     Band 3     Shadow map       [0, 1]  0: no shadow, 1: shadow
        - :code:`LIGHT_HAZE`: Band 4     Light haze map   [0, 1]  0: no light haze, 1: light haze
        - :code:`HEAVY_HAZE`: Band 5     Heavy haze map   [0, 1]  0: no heavy haze, 1: heavy haze
        - :code:`CLOUD`:      Band 6     Cloud map        [0, 1]  0: no cloud, 1: cloud
        - :code:`CONFIDENCE`: Band 7     Confidence map   [0-100] %age value: per-pixel algorithmic confidence in classif
        - :code:`UNUSABLE`:   Band 8     Unusable pixels  --      Equivalent to the UDM asset

        .. code-block:: python

            >>> from eoreader.bands import *
            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
            >>> prod = Reader().open(path)
            >>> prod.open_mask("EDG", GREEN)
            array([[[0, ..., 0]]], dtype=uint8)

        Args:
            mask_id: Mask ID
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        band_mapping = {
            "CLEAR": 1,
            "SNOW": 2,
            "SHADOW": 3,
            "LIGHT_HAZE": 4,
            "HEAVY_HAZE": 5,
            "CLOUD": 6,
            "CONFIDENCE": 7,
            "UNUSABLE": 8,
        }

        assert mask_id in band_mapping
        mask_path = self._get_path("udm2", "tif")

        # Open mask band
        mask = utils.read(
            mask_path,
            resolution=resolution,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            indexes=[band_mapping[mask_id]],
        )

        return mask.astype(np.uint8)

    def _load_nodata(
        self,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> Union[xr.DataArray, None]:
        """
        Load nodata (unimaged pixels) as a numpy array.

        See
        `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
        (unusable data mask) for more information.

        Args:
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            Union[xarray.DataArray, None]: Nodata array

        """
        udm = self.open_mask("UNUSABLE", resolution, size)
        nodata = udm.copy(data=rasters.read_bit_array(udm.compute(), 0))
        return nodata.rename("NODATA")

    def _get_path(self, filename: str, extension: str, invalid_lookahead=None) -> str:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension

        Returns:
            str: Path

        """
        path = ""
        try:
            if self.is_archived:
                if invalid_lookahead:
                    regex = rf".*{filename}(?!{invalid_lookahead})\w*[_]*\.{extension}"
                else:
                    regex = rf".*{filename}\w*[_]*\.{extension}"

                path = files.get_archived_rio_path(self.path, regex)
            else:
                paths = list(self.path.glob(f"**/*{filename}*.{extension}"))
                if invalid_lookahead:
                    paths = [
                        path for path in paths if invalid_lookahead not in str(path)
                    ]
                path = str(paths[0])
        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return path
