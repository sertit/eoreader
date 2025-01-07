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
Super-class of Planet products.
See
`Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
for more information.
"""

import logging
from abc import abstractmethod
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from rasterio.enums import Resampling
from sertit import path, rasters, strings, types
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    BLUE,
    CA,
    CIRRUS,
    CLOUDS,
    GREEN,
    GREEN_1,
    NARROW_NIR,
    NIR,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    VRE_1,
    YELLOW,
    BandNames,
    to_str,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import OpticalProduct, OrbitDirection
from eoreader.products.optical.optical_product import RawUnits
from eoreader.reader import Constellation
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class PlanetMaskType(ListEnum):
    """
    Planet Mask Type
    UDM2 > UDM > NONE
    """

    UDM2 = "Usable Data Mask"
    """
    The usable data mask file provides information on areas of usable data within an image (e.g. clear, snow, shadow, light haze, heavy haze and cloud).
    The pixel size after orthorectification will be 3.125 m for PlanetScope OrthoTiles and 3.0m for PlanetScope Scenes.
    The usable data mask is a raster image having the same dimensions as the image product, comprised of 8 bands, where each band represents a specific usability class mask.
    The usability masks are mutually exclusive, and a value of one indicates that the pixel is assigned to that usability class.
    - Band 1: clear mask (a value of “1” indicates the pixel is clear, a value of “0” indicates that the pixel is not clear and is one of the 5 remaining classes below)
    - Band 2: snow mask
    - Band 3: shadow mask
    - Band 4: light haze mask
    - Band 5: heavy haze mask
    - Band 6: cloud mask
    - Band 7: confidence map (a value of “0” indicates a low confidence in the assigned classification, a value of “100” indicates a high confidence in the assigned classification)
    - Band 8: unusable data mask
    """

    UDM = "Unusable Data Mask"
    """
    The unusable data mask file provides information on areas of unusable data within an image (e.g. cloud and non-imaged areas).
    The pixel size after orthorectification will be 3.125 m for PlanetScope OrthoTiles, 3.0m for PlanetScope Scenes, 50m for RapidEye, and 0.8 m for SkySat.
    It is suggested that when using the file to check for usable data, a buffer of at least 1 pixel should be considered.
    Each bit in the 8-bit pixel identifies whether the corresponding part of the product contains useful imagery:
    - Bit 0: Identifies whether the area contains blackfill in all bands (this area was not imaged). A value of “1” indicates blackfill.
    - Bit 1: Identifies whether the area is cloud covered. A value of “1” indicates cloud coverage.
    Cloud detection is performed on a decimated version of the image (i.e. the browse image) and hence small clouds may be missed.
    Cloud areas are those that have pixel values in the assessed band (Red, NIR or Green) that are above a configurable threshold.
    This algorithm will:
    - Assess snow as cloud
    - Assess cloud shadow as cloud free
    - Assess haze as cloud free
    - Bit 2: Identifies whether the area contains missing (lost during downlink) or suspect (contains down-link errors) data in band 1.
    A value of “1” indicates missing/suspect data. If the product does not include this band, the value is set to “0”.
    - Bit 3: Identifies whether the area contains missing (lost during downlink and hence blackfilled) or suspect (contains downlink errors) data in the band 2.
    A value of “1” indicates missing/suspect data. If the product does not include this band, the value is set to “0”.
    - Bit 4: Identifies whether the area contains missing (lost during downlink) or suspect (contains downlink errors) data in the band 3.
    A value of “1” indicates missing/suspect data. If the product does not include this band, the value is set to “0”.
    - Bit 5: Identifies whether the area contains missing (lost during downlink) or suspect (contains downlink errors) data in band 4.
    A value of “1” indicates missing/suspect data. If the product does not include this band, the value is set to “0”.
    - Bit 6: Identifies whether the area contains missing (lost during downlink) or suspect (contains downlink errors) data in band 5.
    A value of “1” indicates missing/suspect data. If the product does not include this band, the value is set to “0”.
    - Bit 7: Is currently set to “0”.

    The UDM information is found in band 8 of the Usable Data Mask file.
    """

    NONE = "None"
    """
    The product has no mask. Only valid for some RapidEye old products
    """


class PlanetProduct(OpticalProduct):
    """
    Super-class of Planet products.
    See
    `Earth Online <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._nsmap_key = None
        self._merged = False
        self._to_merge = False

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

        if len(self._get_stack_path(as_list=True)) > 1:
            # self._to_merge = True
            self._merge_subdatasets_mtd()

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Planet products are stacked
        self.is_stacked = True

        # Update namespace map key (if needed)
        if self.constellation == Constellation.RE:
            self._nsmap_key = "re"
        elif self.constellation == Constellation.PLA:
            self._nsmap_key = "ps"

        # Tilename
        if self.constellation in [Constellation.RE, Constellation.PLA]:
            # Get MTD XML file
            root, nsmap = self.read_mtd()

            # Manage constellation
            self.tile_name = root.findtext(f".//{nsmap[self._nsmap_key]}tileId")

        self.needs_extraction = False

        # Manage mask type
        try:
            if self.is_archived:
                self._get_archived_path(r".*udm2.*\.tif")
            else:
                next(self.path.glob("**/*udm2*.tif"))
            self._mask_type = PlanetMaskType.UDM2
        except (FileNotFoundError, StopIteration):
            try:
                if self.is_archived:
                    self._get_archived_path(r".*udm.*\.tif")
                else:
                    next(self.path.glob("**/*udm*.tif"))
                self._mask_type = PlanetMaskType.UDM
            except (FileNotFoundError, StopIteration):
                LOGGER.warning(
                    "UDM mask not found. This product won't be cleaned and won't have any cloud band."
                )
                self._mask_type = PlanetMaskType.NONE

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Manage Raw unit
        band_name = (
            path.get_filename(self._get_stack_path(as_list=False)).upper().split("_")
        )
        if "SR" in band_name:
            self._raw_units = RawUnits.REFL
        elif "DN" in band_name:
            # Seems only for basic products
            self._raw_units = RawUnits.DN
        elif "VISUAL" in band_name:
            # Seems only for basic products
            self._raw_units = RawUnits.NONE
        else:
            # If not specified, Planet product are in scaled radiance (*0.01)
            self._raw_units = RawUnits.RAD

        # Post init done by the super class
        super()._post_init(**kwargs)

    @abstractmethod
    def _get_stack_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet stack path(s)

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        raise NotImplementedError

    def _get_udm_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet UDM path

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        if self._merged:
            udm_path, _ = self._get_out_path(f"{self.condensed_name}_udm.vrt")
            if as_list:
                udm_path = [udm_path]
        else:
            udm_path = self._get_path(
                "udm", "tif", invalid_lookahead="udm2", as_list=as_list
            )

        return udm_path

    def _get_udm2_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet UDM2 path

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        if self._merged:
            udm2_path, _ = self._get_out_path(f"{self.condensed_name}_udm2.vrt")
            if as_list:
                udm2_path = [udm2_path]
        else:
            udm2_path = self._get_path("udm2", "tif", as_list=as_list)

        return udm2_path

    def _merge_subdatasets(self) -> tuple[AnyPathType, bool]:
        """
        Merge subdataset, when several Planet products avec been ordered together
        Will create a reflectance (if possible) VRT, a UDM/UDM2 VRT.

        Returns:
            tuple[AnyPathType, bool]: Analytic VRT and if already existing
        """
        if self.is_archived:
            # VRT cannot be created from inside a ZIP
            raise InvalidProductError(
                "EOReader doesn't handle archived Planet data with multiple subdataset. Please extract this product."
            )
            # TODO: merge_geotiff BUT handle reflectances for every subdataset!
            # Relevant ? Maybe not as it takes would a lot of time to merge

        if path.is_cloud_path(self.path):
            # VRT cannot be created from data stored in the cloud
            raise InvalidProductError(
                "EOReader doesn't handle cloud-stored Planet data with multiple subdataset. Please download this product on disk."
            )
            # Relevant ? Maybe not as it takes would a lot of time to download, or a lot of time to merge as geotiffs

        analytic_vrt_path, analytic_vrt_exists = self._get_out_path(
            f"{self.condensed_name}_analytic.vrt"
        )
        if not analytic_vrt_exists:
            LOGGER.debug("Creating raster VRT")
            rasters.merge_vrt(
                self._get_stack_path(as_list=True), analytic_vrt_path, abs_path=True
            )

        udm_vrt_path, udm_vrt_exists = self._get_out_path(
            f"{self.condensed_name}_udm.vrt"
        )
        if not udm_vrt_exists:
            udm_paths = self._get_udm_path(as_list=True)
            if udm_paths:
                LOGGER.debug("Creating UDM VRT")
                nodata = "1"
                rasters.merge_vrt(
                    self._get_udm_path(as_list=True),
                    udm_vrt_path,
                    abs_path=True,
                    **{"-srcnodata": nodata, "-vrtnodata": nodata},
                )

        udm2_vrt_path, udm2_vrt_exists = self._get_out_path(
            f"{self.condensed_name}_udm2.vrt"
        )
        if not udm2_vrt_exists:
            LOGGER.debug("Creating UDM2 VRT")
            # Nodata values
            # see: https://developers.planet.com/docs/data/udm-2/#udm2-bands
            # Band 1    Clear map       [0, 1] 	    0: not clear, 1: clear
            # Band 2 	Snow map 	    [0, 1] 	    0: no snow or ice, 1: snow or ice
            # Band 3 	Shadow map 	    [0, 1] 	    0: no shadow, 1: shadow
            # Band 4 	Light haze map 	[0, 1] 	    0: no light haze, 1: light haze
            # Band 5 	Heavy haze map 	[0, 1] 	    0: no heavy haze, 1: heavy haze
            # Band 6 	Cloud map 	    [0, 1] 	    0: no cloud, 1: cloud
            # Band 7 	Confidence map 	[ 0 - 100] 	percentage value: per-pixel algorithmic confidence in classification
            # Band 8 	Unusable pixels  --         Equivalent to the UDM asset: a value of “1” indicates blackfill.
            nodata = strings.to_cmd_string("0 0 0 0 0 0 0 1")
            rasters.merge_vrt(
                self._get_udm2_path(as_list=True),
                udm2_vrt_path,
                abs_path=True,
                **{"-srcnodata": nodata, "-vrtnodata": nodata},
            )

        self._merged = True

        return analytic_vrt_path, analytic_vrt_exists

    @abstractmethod
    def _merge_subdatasets_mtd(self) -> None:
        """
        Merge subdataset, when several Planet products avec been ordered together
        Will create a reflectance (if possible) VRT, a UDM/UDM2 VRT and a merged metadata XML file.

        Constellation specific
        """
        raise NotImplementedError

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

        # Vectorize the nodata band
        # Don't use convex hull as the product can be cropped to an AOI!
        footprint = rasters.vectorize(
            nodata, values=1, keep_values=False, dissolve=True
        )

        return gpd.GeoDataFrame(geometry=footprint.geometry, crs=footprint.crs)

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
                <SpectralBandNames.RED: 'RED'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
            }

        Args:
            band_list (list): List of the wanted bands
            pixel_size (float): Band pixel size
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        band_path = self._get_stack_path(as_list=False)
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, pixel_size=pixel_size, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
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
        with rasterio.open(str(band_path)) as dst:
            # Manage the case if we open a simple band (EOReader processed bands)
            if dst.count == 1:
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
            size=(band_arr.rio.width, band_arr.rio.height), **kwargs
        ).values

        # Dubious pixels mapping
        # See: https://community.planet.com/planet-s-community-forum-3/planetscope-8-bands-and-udm-mask-245?postid=436#post436
        dubious_bands = {
            BLUE: 2,
            GREEN: 3,
            RED: 4,
            VRE_1: 5,
            NIR: 6,
            NARROW_NIR: 6,
            CA: 7,
            GREEN_1: 7,
            YELLOW: 7,
        }

        # Open unusable mask
        udm = self.open_mask(
            "UNUSABLE", size=(band_arr.rio.width, band_arr.rio.height), **kwargs
        )
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
            size=(band_arr.rio.width, band_arr.rio.height), **kwargs
        ).values

        # -- Merge masks
        return self._set_nodata_mask(band_arr, no_data_mask)

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
        band_paths = self.get_band_paths(bands, pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
        )

        return band_arrays

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        """
        # NOTE: CIRRUS == HEAVY HAZE

        # FROM DOCUMENTATION: https://developers.planet.com/docs/data/udm-2/
        # Percent of heavy haze values in dataset.
        # Heavy haze values represent scene content areas (non-blackfilled) that contain thin low altitude clouds,
        # higher altitude cirrus clouds, soot and dust which allow fair recognition of land cover features,
        # but not having reliable interpretation of the radiometry or surface reflectance.
        if self._mask_type == PlanetMaskType.UDM2:
            has_band = True
        elif self._mask_type == PlanetMaskType.UDM:
            has_band = band not in [SHADOWS, CIRRUS]
        else:
            has_band = False

        return has_band

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        CIRRUS is HEAVY_HAZE

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        if self._mask_type == PlanetMaskType.UDM2:
            return self._open_clouds_udm2(bands, pixel_size, size, **kwargs)
        else:
            # UDM
            return self._open_clouds_udm(bands, pixel_size, size, **kwargs)

    def _open_clouds_udm2(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        CIRRUS is HEAVY_HAZE

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        # Load default xarray as a template
        def_xarr = self._read_band(
            self.get_default_band_path(),
            band=self.get_default_band(),
            pixel_size=pixel_size,
            size=size,
            **kwargs,
        )

        # Load nodata
        nodata = self._load_nodata(pixel_size, size, **kwargs).data

        if bands:
            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(
                        def_xarr.rename(ALL_CLOUDS.name),
                        (
                            self.open_mask("CLOUD", pixel_size, size, **kwargs).data
                            & self.open_mask("SHADOW", pixel_size, size, **kwargs).data
                            & self.open_mask(
                                "HEAVY_HAZE", pixel_size, size, **kwargs
                            ).data
                        ),
                        nodata,
                    )
                elif band == SHADOWS:
                    cloud = self._create_mask(
                        def_xarr.rename(SHADOWS.name),
                        self.open_mask("SHADOW", pixel_size, size, **kwargs).data,
                        nodata,
                    )
                elif band == CLOUDS:
                    cloud = self._create_mask(
                        def_xarr.rename(CLOUDS.name),
                        self.open_mask("CLOUD", pixel_size, size, **kwargs).data,
                        nodata,
                    )
                elif band == CIRRUS:
                    cloud = self._create_mask(
                        def_xarr.rename(CIRRUS.name),
                        self.open_mask("HEAVY_HAZE", pixel_size, size, **kwargs).data,
                        nodata,
                    )
                elif band == RAW_CLOUDS:
                    cloud = utils.read(
                        self._get_udm2_path(), pixel_size, size, **kwargs
                    )
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for {self.constellation.value}: {band}"
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _open_clouds_udm(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        CIRRUS is HEAVY_HAZE

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        # Load default xarray as a template
        def_xarr = self._read_band(
            self.get_default_band_path(),
            band=self.get_default_band(),
            pixel_size=pixel_size,
            size=size,
            **kwargs,
        )
        # Open mask (here we know we have a UDM file, as the product is supposed to have the band)
        udm = self.open_mask_udm(pixel_size, size, **kwargs)

        if bands:
            for band in bands:
                if band in [ALL_CLOUDS, CLOUDS]:
                    # Load nodata
                    nodata, clouds = rasters.read_bit_array(udm.compute(), [0, 1])

                    cloud = self._create_mask(
                        def_xarr.rename(ALL_CLOUDS.name),
                        clouds,
                        nodata,
                    )
                elif band == RAW_CLOUDS:
                    cloud = udm
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for {self.constellation.value}: {band}"
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
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> Union[xr.DataArray, None]:
        """
        Open a Planet UDM2 (Usable Data Mask) mask, band by band, as a xarray.
        Returns None if the mask is not available.

        Do not open cloud mask with this function. Use :code:`load` instead.

        See `UDM2 specifications <https://developers.planet.com/docs/data/udm-2/>`_ for more
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
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        if self._mask_type == PlanetMaskType.UDM2:
            mask = self.open_mask_udm2(mask_id, pixel_size, size, **kwargs)
        elif self._mask_type == PlanetMaskType.UDM:
            mask = self.open_mask_udm(pixel_size, size, **kwargs)
        else:
            def_xarr = self._read_band(
                self.get_default_band_path(),
                band=self.get_default_band(),
                pixel_size=pixel_size,
                size=size,
                as_type=np.uint8,
                masked=False,
                **kwargs,
            )
            mask = def_xarr.copy(data=np.zeros_like(def_xarr.data))

        return mask.rename(self._mask_type.value)

    def open_mask_udm2(
        self,
        mask_id: str,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> Union[xr.DataArray, None]:
        """
        Open a Planet UDM2 (Usable Data Mask) mask, band by band, as a xarray.
        Returns None if the mask is not available.

        Do not open cloud mask with this function. Use :code:`load` instead.

        See `UDM2 specifications <https://developers.planet.com/docs/data/udm-2/>`_ for more
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
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

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
        mask_path = self._get_udm2_path()

        # Open mask band
        mask = utils.read(
            mask_path,
            pixel_size=pixel_size,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            indexes=[band_mapping[mask_id]],
            **kwargs,
        )

        return mask.astype(np.uint8)

    def open_mask_udm(
        self, pixel_size: float = None, size: Union[list, tuple] = None, **kwargs
    ) -> Union[xr.DataArray, None]:
        """
        Open a Planet UDM (Unusable Data Mask) mask as a xarray.
        For RapidEye, the mask is subsampled to 50m, so this function will interpolate to make it to the correct pixel size
        Returns None if the mask is not available.

        Do not open cloud mask with this function. Use :code:`load` instead.

        See `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf/>`_ for more
        information.

        Args:
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        mask_path = self._get_udm_path()

        # Open mask band
        return utils.read(
            mask_path,
            pixel_size=pixel_size,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            as_type=np.uint8,
            **kwargs,
        )

    def _load_nodata(
        self, pixel_size: float = None, size: Union[list, tuple] = None, **kwargs
    ) -> Union[xr.DataArray, None]:
        """
        Load nodata (unimaged pixels) as a numpy array.

        See
        `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
        (unusable data mask) for more information.

        Args:
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            Union[xarray.DataArray, None]: Nodata array

        """
        udm = self.open_mask("UNUSABLE", pixel_size, size, **kwargs)
        nodata = udm.copy(data=rasters.read_bit_array(udm.compute(), 0))
        return nodata.rename("NODATA")

    def _get_path(
        self,
        filename: str,
        extension: str,
        invalid_lookahead: Union[str, list] = None,
        as_list=False,
    ) -> Union[list, str]:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension
            invalid_lookahead (Union[str, list]): Invalid lookahed (string that cannot be placed after the filename)

        Returns:
            Union[list, str]: Paths(s)

        """
        if invalid_lookahead is not None:
            invalid_lookahead = types.make_iterable(invalid_lookahead)

        ok_paths = []
        try:
            if self.is_archived:
                regex = rf".*{filename}\w*[_]*\.{extension}"

                ok_paths = self._get_archived_rio_path(regex, as_list=True)
            else:
                ok_paths = [
                    str(p) for p in self.path.glob(f"**/*{filename}*.{extension}")
                ]

            if invalid_lookahead:
                for ok_path in ok_paths.copy():
                    if any(
                        il in path.get_filename(ok_path) for il in invalid_lookahead
                    ):
                        ok_paths.remove(ok_path)

                if not ok_paths:
                    raise FileNotFoundError

            if not as_list:
                ok_paths = ok_paths[0]
        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return ok_paths

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
        root, nsmap = self.read_mtd()

        # Open zenith and azimuth angle
        if self.constellation == Constellation.SKY:
            try:
                elev_angle = float(root.findtext(".//sun_elevation"))
                azimuth_angle = float(root.findtext(".//sun_azimuth"))
            except TypeError as exc:
                raise InvalidProductError(
                    "Azimuth or Zenith angles not found in metadata!"
                ) from exc
        else:
            try:
                elev_angle = float(
                    root.findtext(f".//{nsmap['opt']}illuminationElevationAngle")
                )
                azimuth_angle = float(
                    root.findtext(f".//{nsmap['opt']}illuminationAzimuthAngle")
                )
            except TypeError as exc:
                raise InvalidProductError(
                    "Azimuth or Zenith angles not found in metadata!"
                ) from exc

        # From elevation to zenith
        zenith_angle = 90.0 - elev_angle

        return azimuth_angle, zenith_angle

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Open identifier
        if self.constellation == Constellation.SKY:
            name = root.findtext(".//id")
            if not name:
                raise InvalidProductError("id not found in metadata!")
        else:
            name = root.findtext(f".//{nsmap['eop']}identifier")
            if not name:
                raise InvalidProductError(
                    f"{nsmap['eop']}identifier not found in metadata!"
                )

        return name

    @cache
    def get_mean_viewing_angles(self) -> (float, float, float):
        """
        Get Mean Viewing angles (azimuth, off-nadir and incidence angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_viewing_angles()

        Returns:
            (float, float, float): Mean azimuth, off-nadir and incidence angles
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Open zenith and azimuth angle
        if self.constellation == Constellation.SKY:
            try:
                az = float(root.findtext(".//satellite_azimuth"))
                off_nadir = float(root.findtext(".//view_angle"))
                incidence_angle = None
            except TypeError as exc:
                raise InvalidProductError(
                    "satellite_azimuth or view_angle angles not found in metadata!"
                ) from exc
        else:
            try:
                az = float(root.findtext(f".//{nsmap[self._nsmap_key]}azimuthAngle"))
                off_nadir = abs(
                    float(
                        root.findtext(f".//{nsmap[self._nsmap_key]}spaceCraftViewAngle")
                    )
                )
                incidence_angle = float(
                    root.findtext(f".//{nsmap['eop']}incidenceAngle")
                )
            except TypeError as exc:
                raise InvalidProductError(
                    "azimuthAngle, spaceCraftViewAngle or incidenceAngle not found in metadata!"
                ) from exc

        return az, off_nadir, incidence_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"20210406_015904_37_2407.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element {http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}
            EarthObservation at 0x1a2621f03c8>,
            {
                'opt': '{http://earth.esa.int/opt}',
                'gml': '{http://www.opengis.net/gml}',
                'eop': '{http://earth.esa.int/eop}',
                'ps': '{http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}'
            })

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        try:
            mtd_from_path = "metadata*.xml"
            mtd_archived = r"metadata.*\.xml"

            return self._read_mtd_xml(mtd_from_path, mtd_archived)
        except InvalidProductError:
            # Some RapidEye old product don't have the correct nomenclature
            return self._read_mtd_xml("xml", "xml")

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
            if self.constellation == Constellation.SKY:
                try:
                    cc = float(root.findtext(".//cloud_percent"))

                except TypeError as exc:
                    raise InvalidProductError(
                        "'cloud_percent' not found in metadata!"
                    ) from exc
            else:
                try:
                    cc = float(root.findtext(f".//{nsmap['opt']}cloudCoverPercentage"))

                except TypeError as exc:
                    raise InvalidProductError(
                        "'opt:cloudCoverPercentage' not found in metadata!"
                    ) from exc

        except (InvalidProductError, TypeError) as ex:
            LOGGER.warning(ex)
            cc = 0

        return cc

    @cache
    def get_orbit_direction(self) -> OrbitDirection:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_orbit_direction().value
            "DESCENDING"

        Returns:
            OrbitDirection: Orbit direction (ASCENDING/DESCENDING)
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Get the orbit direction
        if self.constellation == Constellation.SKY:
            od = OrbitDirection.DESCENDING
        else:
            try:
                od = OrbitDirection.from_value(
                    root.findtext(f".//{nsmap['eop']}orbitDirection")
                )

            except TypeError as exc:
                raise InvalidProductError(
                    "eop:orbitDirection not found in metadata!"
                ) from exc

        return od

    def _get_condensed_name(self) -> str:
        """
        Get Planet products condensed name ({date}_{constellation}_{product_type}_{tile}).

        Returns:
            str: Condensed name
        """
        tile = f"_{self.tile_name}" if self.tile_name is not None else ""
        condensed_name = f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}{tile}"
        return condensed_name
