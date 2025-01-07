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
Harmonized Landsat-Sentinel (HLS) products
- https://lpdaac.usgs.gov/documents/1326/HLS_User_Guide_V2.pdf
- https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/
"""

import logging
import os
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from rasterio.enums import Resampling
from sertit import path, rasters, types, xml
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    BLUE,
    CA,
    CIRRUS,
    CLOUDS,
    GREEN,
    NARROW_NIR,
    NIR,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SWIR_1,
    SWIR_2,
    SWIR_CIRRUS,
    TIR_1,
    TIR_2,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    BandNames,
    SpectralBand,
    to_str,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import OpticalProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.stac import ASSET_ROLE, BT, GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class HlsProductType(ListEnum):
    """
    `HLS products types <https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/#hls-data-processing>`_
    """

    S30 = "HLS.S30"
    """
    MSI harmonized surface reflectance resampled to 30 m into the Sentinel-2 tiling system and adjusted to Landsat 8 spectral response function.
    """

    L30 = "HLS.L30"
    """
    OLI harmonized surface reflectance and Top-of-Atmosphere (TOA) brightness temperature resampled to 30 m into the Sentinel-2 tiling system.
    """


@unique
class HlsInstrument(ListEnum):
    """HLS instruments"""

    OLI_TIRS = "OLI-TIRS"
    """Landsat OLI-TIRS instruments combined,, for Landsat-8 and 9 constellation"""

    MSI = "TIRS"
    """Sentinel-2 Instrument, for Sentinel-2 constellation"""


class HlsProduct(OpticalProduct):
    """
    Class for Harmonized Landsat-Sentinel (HLS) products
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.REFL
        self._has_cloud_cover = True
        self._use_filename = True
        self.needs_extraction = False

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _get_path(self, band_id: str) -> AnyPathType:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            AnyPathType: band path

        """
        if self.is_archived:
            prod_path = self._get_archived_rio_path(rf".*{band_id}\.tif")
        else:
            prod_path = path.get_file_in_dir(
                self.path, f"*{band_id}.tif", exact_name=True
            )

        return prod_path

    def _get_fmask_path(self) -> AnyPathType:
        """
        Get either the archived path of the normal path of the Fmask path

        Returns:
            AnyPathType: band path

        """

        return self._get_path("Fmask")

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        self.pixel_size = 30.0

    def open_mask(
        self, pixel_size: float = None, size: Union[list, tuple] = None, **kwargs
    ) -> Union[xr.DataArray, None]:
        """
        Open a HLS Fmask

        Args:
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        mask_path = self._get_fmask_path()

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
        fmask = self.open_mask(**kwargs)
        nodata = fmask.copy(
            data=np.where(fmask == self._mask_nodata, 1, 0).astype(np.uint8)
        )
        return nodata.rename("NODATA")

    @cache
    @simplify
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
        nodata = self._load_nodata()

        # Vectorize the nodata band
        footprint = rasters.vectorize(
            nodata, values=1, keep_values=False, dissolve=True
        )
        # footprint = geometry.get_wider_exterior(footprint)  # No need here

        # Keep only the convex hull
        footprint.geometry = footprint.geometry.convex_hull

        return footprint

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"HLS.S30.T60HTE.2022103T222539.v2.0.B01.tif"
            >>> prod = Reader().open(path)
            >>> prod.get_tile_name()
            'T60HTE'

        Returns:
            str: Tile name
        """
        return self.split_name[2]

    def _set_product_type(self) -> None:
        """
        Set product type.
        """
        # Processing level
        prod_type = self.split_name[1]
        self.product_type = getattr(HlsProductType, prod_type)

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        if self.split_name[1] == "L30":
            self.instrument = HlsInstrument.OLI_TIRS
        else:
            self.instrument = HlsInstrument.MSI

    def _map_bands(self) -> None:
        """
        Map bands
        """
        if self.instrument == HlsInstrument.OLI_TIRS:
            self._map_bands_oli()
        elif self.instrument == HlsInstrument.MSI:
            self._map_bands_msi()

    def _map_bands_oli(self) -> None:
        """
        Map bands OLI-TIRS
        """
        oli_bands = {
            CA: SpectralBand(
                eoreader_name=CA,
                **{
                    NAME: "Coastal aerosol",
                    ID: "01",
                    GSD: 30,
                    WV_MIN: 430,
                    WV_MAX: 450,
                },
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "Blue",
                    ID: "02",
                    GSD: 30,
                    WV_MIN: 450,
                    WV_MAX: 510,
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "Green",
                    ID: "03",
                    GSD: 30,
                    WV_MIN: 530,
                    WV_MAX: 590,
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "Red",
                    ID: "04",
                    GSD: 30,
                    WV_MIN: 640,
                    WV_MAX: 670,
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "NIR Narrow",
                    ID: "05",
                    GSD: 30,
                    WV_MIN: 850,
                    WV_MAX: 880,
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "NIR Narrow",
                    ID: "05",
                    GSD: 30,
                    WV_MIN: 850,
                    WV_MAX: 880,
                },
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "SWIR 1",
                    ID: "06",
                    GSD: 30,
                    WV_MIN: 1570,
                    WV_MAX: 1650,
                },
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{
                    NAME: "SWIR 2",
                    ID: "07",
                    GSD: 30,
                    WV_MIN: 2110,
                    WV_MAX: 2290,
                },
            ),
            SWIR_CIRRUS: SpectralBand(
                eoreader_name=SWIR_CIRRUS,
                **{
                    NAME: "Cirrus",
                    ID: "09",
                    GSD: 30,
                    WV_MIN: 1360,
                    WV_MAX: 1380,
                },
            ),
            TIR_1: SpectralBand(
                eoreader_name=TIR_1,
                **{
                    NAME: "Thermal Infrared (TIRS) 1",
                    ID: "10",
                    GSD: 100,
                    WV_MIN: 10600,
                    WV_MAX: 11190,
                    ASSET_ROLE: BT,
                },
            ),
            TIR_2: SpectralBand(
                eoreader_name=TIR_2,
                **{
                    NAME: "Thermal Infrared (TIRS) 2",
                    ID: "11",
                    GSD: 100,
                    WV_MIN: 11500,
                    WV_MAX: 12510,
                    ASSET_ROLE: BT,
                },
            ),
        }

        self.bands.map_bands(oli_bands)

    def _map_bands_msi(self) -> None:
        """
        Map bands MSI
        """
        msi_bands = {
            CA: SpectralBand(
                eoreader_name=CA,
                **{
                    NAME: "Coastal aerosol",
                    ID: "01",
                    GSD: 30,
                    WV_MIN: 430,
                    WV_MAX: 450,
                },
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{
                    NAME: "Blue",
                    ID: "02",
                    GSD: 30,
                    WV_MIN: 450,
                    WV_MAX: 510,
                },
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{
                    NAME: "Green",
                    ID: "03",
                    GSD: 30,
                    WV_MIN: 530,
                    WV_MAX: 590,
                },
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{
                    NAME: "Red",
                    ID: "04",
                    GSD: 30,
                    WV_MIN: 640,
                    WV_MAX: 670,
                },
            ),
            VRE_1: SpectralBand(
                eoreader_name=VRE_1,
                **{
                    NAME: "Red-Edge 1",
                    ID: "05",
                    GSD: 20,
                    WV_MIN: 690,
                    WV_MAX: 710,
                },
            ),
            VRE_2: SpectralBand(
                eoreader_name=VRE_2,
                **{
                    NAME: "Red-Edge 2",
                    ID: "06",
                    GSD: 20,
                    WV_MIN: 730,
                    WV_MAX: 750,
                },
            ),
            VRE_3: SpectralBand(
                eoreader_name=VRE_3,
                **{
                    NAME: "Red-Edge 3",
                    ID: "07",
                    GSD: 20,
                    WV_MIN: 770,
                    WV_MAX: 790,
                },
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{
                    NAME: "NIR Broad",
                    ID: "08",
                    GSD: 30,
                    WV_MIN: 780,
                    WV_MAX: 880,
                },
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{
                    NAME: "NIR Narrow",
                    ID: "8A",
                    GSD: 30,
                    WV_MIN: 850,
                    WV_MAX: 880,
                },
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{
                    NAME: "SWIR 1",
                    ID: "11",
                    GSD: 30,
                    WV_MIN: 1570,
                    WV_MAX: 1650,
                },
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{
                    NAME: "SWIR 2",
                    ID: "12",
                    GSD: 30,
                    WV_MIN: 2110,
                    WV_MAX: 2290,
                },
            ),
            WV: SpectralBand(
                eoreader_name=WV,
                **{
                    NAME: "Water Vapor",
                    ID: "09",
                    GSD: 60,
                    WV_MIN: 930,
                    WV_MAX: 950,
                },
            ),
            SWIR_CIRRUS: SpectralBand(
                eoreader_name=SWIR_CIRRUS,
                **{
                    NAME: "Cirrus",
                    ID: "10",
                    GSD: 30,
                    WV_MIN: 1360,
                    WV_MAX: 1380,
                },
            ),
        }

        self.bands.map_bands(msi_bands)

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        TODO

        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//SENSING_TIME")
            if not acq_date:
                raise InvalidProductError("'SENSING_TIME' not found in metadata!")

            # Convert to datetime
            try:
                date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                # Too many microseconds. Removing them.
                date = datetime.strptime(acq_date.split(".")[0], "%Y-%m-%dT%H:%M:%S")

        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name(self) -> str:
        """
        Set product real name. Overrides get_name due to points in name.
        TODO: Keep points in name ?

        Returns:
            str: True name of the product (from metadata)
        """
        mask_path = self._get_fmask_path()
        name = os.path.basename(mask_path).replace(".Fmask.tif", "")
        return name

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # No need here (_get_name reimplemented)
        pass

    def _get_split_name(self) -> list:
        """
        Get split name (with points !)

        Returns:
            list: Split products name
        """
        return [x for x in self.name.split(".") if x]

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2/LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',
                <SpectralBandNames.RED: 'RED'>:
                    'LC08_L1GT_023030_20200518_20200527_01_T2/LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF'
            }

        Args:
            band_list (list): List of the wanted bands
            pixel_size (float): Useless here
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            if not self.has_band(band):
                raise InvalidProductError(
                    f"Non existing band ({band.name}) for HLS products."
                )
            band_id = self.bands[band].id

            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, pixel_size=pixel_size, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                try:
                    band_paths[band] = self._get_path(f"B{band_id}")
                except FileNotFoundError as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({band_id}) band for {self.path}"
                    ) from ex

        return band_paths

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read HLS metadata.

        Available fields (both L30 and S30):
            - 'ACCODE',
            - 'AREA_OR_POINT',
            - 'arop_ave_xshift(meters)',
            - 'arop_ave_yshift(meters)',
            - 'arop_ncp',
            - 'arop_rmse(meters)',
            - 'arop_s2_refimg',
            - 'cloud_coverage',
            - 'HLS_PROCESSING_TIME',
            - 'HORIZONTAL_CS_NAME',
            - 'L1_PROCESSING_TIME',
            - 'MEAN_SUN_AZIMUTH_ANGLE',
            - 'MEAN_SUN_ZENITH_ANGLE',
            - 'MEAN_VIEW_AZIMUTH_ANGLE',
            - 'MEAN_VIEW_ZENITH_ANGLE',
            - 'NBAR_SOLAR_ZENITH',
            - 'NCOLS',
            - 'NROWS',
            - 'OVR_RESAMPLING_ALG',
            - 'SENSING_TIME',
            - 'spatial_coverage',
            - 'SPATIAL_RESOLUTION',
            - 'ULX',
            - 'ULY'

        Specific fields for L30:
            - 'LANDSAT_PRODUCT_ID',
            - 'LANDSAT_SCENE_ID',
            - 'PROCESSING_LEVEL',
            - 'SENSOR',
            - 'SENTINEL2_TILEID',
            - 'TIRS_SSM_MODEL',
            - 'TIRS_SSM_POSITION_STATUS',
            - 'USGS_SOFTWARE'

        Specific fields for S30:
            - 'DATASTRIP_ID',
            - 'HORIZONTAL_CS_CODE',
            - 'L1C_IMAGE_QUALITY',
            - 'MSI band 01 bandpass adjustment slope and offset',
            - 'MSI band 02 bandpass adjustment slope and offset',
            - 'MSI band 03 bandpass adjustment slope and offset',
            - 'MSI band 04 bandpass adjustment slope and offset',
            - 'MSI band 11 bandpass adjustment slope and offset',
            - 'MSI band 12 bandpass adjustment slope and offset',
            - 'MSI band 8a bandpass adjustment slope and offset',
            - 'PROCESSING_BASELINE',
            - 'PRODUCT_URI'
            - 'SPACECRAFT_NAME'
            - 'TILE_ID'

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mask_path = self._get_fmask_path()

        with rasterio.open(str(mask_path)) as ds:
            tags = ds.tags()
            tags.pop("_FillValue", None)

        return xml.dict_to_xml(tags), {}

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
        band_arr = utils.read(
            band_path,
            pixel_size=pixel_size,
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
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # Works either with reflectance  (scale = 0.0001) and tb (scale = 0.01)
        with rasterio.open(str(band_path)) as ds:
            tags = ds.tags()
            offset = float(tags["add_offset"])
            scale_factor = float(tags["scale_factor"])

        return band_arr * scale_factor + offset

    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as a SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        # There is no invalid pixels in HLS products
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
        # Nodata is loaded by default (COG file)
        return band_arr

    def _load_bands(
        self,
        bands: Union[list, BandNames],
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same pixel size (and same metadata).

        Args:
            bands (list, BandNames): List of the wanted bands
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
        bands = types.make_iterable(bands)

        if pixel_size is None and size is not None:
            pixel_size = self._pixel_size_from_img_size(size)
        band_paths = self.get_band_paths(bands, pixel_size=pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
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
        mtd_data, _ = self.read_mtd()
        try:
            azimuth_angle = float(mtd_data.findtext(".//MEAN_SUN_AZIMUTH_ANGLE"))
            zenith_angle = float(mtd_data.findtext(".//MEAN_SUN_ZENITH_ANGLE"))
        except TypeError as exc:
            raise InvalidProductError(
                "MEAN_SUN_AZIMUTH_ANGLE or MEAN_SUN_ZENITH_ANGLE not found in metadata!"
            ) from exc

        return azimuth_angle, zenith_angle

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_Lx{instrument}_{tile}_{product_type}).

        Returns:
            str: Condensed Landsat name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{self.tile_name}"

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Fmask has all cloud bands
        """
        return True

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read Landsat clouds from Fmask.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            # Open Fmask
            fmask = self.open_mask(pixel_size, size, **kwargs)

            # Don't use load_nodata in order not to load a 2nd time fmask
            nodata = np.where(fmask == self._mask_nodata, 1, 0)
            cirrus_id = 0
            cloud_id = 1
            shadow_id = 3

            cir, cld, shd = rasters.read_bit_array(
                fmask, [cirrus_id, cloud_id, shadow_id]
            )

            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(fmask, cld | shd | cir, nodata)
                elif band == SHADOWS:
                    cloud = self._create_mask(fmask, shd, nodata)
                elif band == CLOUDS:
                    cloud = self._create_mask(fmask, cld, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(fmask, cir, nodata)
                elif band == RAW_CLOUDS:
                    cloud = fmask
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for {self.constellation.value} constellations: {band}"
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

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
        root, _ = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(".//cloud_coverage"))
        except (InvalidProductError, TypeError):
            LOGGER.warning("'cloud_coverage' not found in metadata!")
            cc = 0

        return cc

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(regex=r".*.jpg")
            else:
                quicklook_path = str(next(self.path.glob("*.jpg")))
        except (StopIteration, FileNotFoundError):
            pass

        return quicklook_path
