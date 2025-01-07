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
"""Sentinel-2 cloud-stored products"""

import difflib
import json
import logging
from datetime import datetime
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio.enums import Resampling
from sertit import AnyPath, files, path, rasters, types
from sertit.files import CustomDecoder
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    ALL_CLOUDS,
    BLUE,
    CA,
    CIRRUS,
    CLOUDS,
    EOREADER_STAC_MAP,
    GREEN,
    NARROW_NIR,
    NIR,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    SWIR_1,
    SWIR_2,
    SWIR_CIRRUS,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    BandNames,
    SpectralBand,
    to_str,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import S2ProductType
from eoreader.products.optical.optical_product import OpticalProduct, RawUnits
from eoreader.products.stac_product import StacProduct
from eoreader.reader import Constellation
from eoreader.stac import CENTER_WV, FWHM, GSD, ID, NAME
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


class S2E84Product(OpticalProduct):
    """
    Class for Sentinel-2 stored on AWS and processed by Element 84 (COGs) products

    https://element84.com/geospatial/introducing-earth-search-v1-new-datasets-now-available/

    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.raw_no_data = 0
        self.tile_mtd = {}
        self.stac_mtd = {}

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.REFL
        self._has_cloud_cover = True
        self._use_filename = False
        self.needs_extraction = False

        # Read the JSON tileinfo mtd
        self.tile_mtd = files.read_json(
            self._get_path("tileinfo_metadata", ext="json"), print_file=False
        )
        self.stac_mtd = files.read_json(
            self._get_path(self.filename, ext="json"), print_file=False
        )

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

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation: force S2."""
        return Constellation.S2

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """
        return self.split_name[-2]

    def _set_product_type(self) -> None:
        """Set products type"""
        self.product_type = S2ProductType.from_value(self.split_name[1])

    def _set_instrument(self) -> None:
        """
        Set instrument

        Sentinel-2: https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2/instrument-payload/
        """
        self.instrument = "MSI"

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # S2: use 10m resolution, even if we have 60m and 20m resolution
        # In the future maybe use one resolution per band ?
        self.pixel_size = 10.0

    def _map_bands(self) -> None:
        """
        Map bands
        """
        l2a_bands = {
            CA: SpectralBand(
                eoreader_name=CA,
                **{NAME: "B01", ID: "01", GSD: 60, CENTER_WV: 442, FWHM: 21},
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{NAME: "B02", ID: "02", GSD: 10, CENTER_WV: 492, FWHM: 66},
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{NAME: "B03", ID: "03", GSD: 10, CENTER_WV: 560, FWHM: 36},
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{NAME: "B04", ID: "04", GSD: 10, CENTER_WV: 665, FWHM: 31},
            ),
            VRE_1: SpectralBand(
                eoreader_name=VRE_1,
                **{NAME: "B05", ID: "05", GSD: 20, CENTER_WV: 704, FWHM: 15},
            ),
            VRE_2: SpectralBand(
                eoreader_name=VRE_2,
                **{NAME: "B06", ID: "06", GSD: 20, CENTER_WV: 740, FWHM: 15},
            ),
            VRE_3: SpectralBand(
                eoreader_name=VRE_3,
                **{NAME: "B07", ID: "07", GSD: 20, CENTER_WV: 781, FWHM: 20},
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{NAME: "B08", ID: "08", GSD: 10, CENTER_WV: 833, FWHM: 106},
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{NAME: "B8A", ID: "8A", GSD: 20, CENTER_WV: 864, FWHM: 21},
            ),
            WV: SpectralBand(
                eoreader_name=WV,
                **{NAME: "B09", ID: "09", GSD: 60, CENTER_WV: 944, FWHM: 20},
            ),
            SWIR_1: SpectralBand(
                eoreader_name=SWIR_1,
                **{NAME: "B11", ID: "11", GSD: 20, CENTER_WV: 1612, FWHM: 92},
            ),
            SWIR_2: SpectralBand(
                eoreader_name=SWIR_2,
                **{NAME: "B12", ID: "12", GSD: 20, CENTER_WV: 2190, FWHM: 180},
            ),
        }

        if self.product_type == S2ProductType.L2A:
            self.bands.map_bands(l2a_bands)
        elif self.product_type == S2ProductType.L1C:
            self.bands.map_bands(
                {
                    **l2a_bands,
                    SWIR_CIRRUS: SpectralBand(
                        eoreader_name=SWIR_CIRRUS,
                        **{NAME: "B10", ID: "10", GSD: 60, CENTER_WV: 1380, FWHM: 30},
                    ),
                }
            )
        else:
            raise InvalidProductError(f"Invalid Sentinel-2 name: {self.filename}")

    def _get_path(self, file_id: str, ext: str = "tif") -> AnyPathType:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            file_id (str): file ID
            ext (str) : Extension

        Returns:
            AnyPathType: band path

        """
        if self.is_archived:
            prod_path = self._get_archived_rio_path(rf".*{file_id}\.{ext}")
        else:
            prod_path = path.get_file_in_dir(
                self.path, f"*{file_id}.{ext}", exact_name=True
            )

        return prod_path

    def open_mask(
        self, pixel_size: float = None, size: Union[list, tuple] = None, **kwargs
    ) -> Union[xr.DataArray, None]:
        """
        Open a Scene classification map (SCL) mask.
        See https://sentinels.copernicus.eu/ca/web/sentinel/technical-guides/sentinel-2-msi/level-2a/algorithm-overview
        Paragraph: Classification Mask Generation

        Values:
        - 0 : NO_DATA
        - 1 : SATURATED_OR_DEFECTIVE
        - 2 : CAST_SHADOWS
        - 3 : CLOUD_SHADOWS
        - 4 : VEGETATION
        - 5 : NOT_VEGETATED
        - 6 : WATER
        - 7 : UNCLASSIFIED
        - 8 : CLOUD_MEDIUM_PROBABILITY
        - 9 : CLOUD_HIGH_PROBABILITY
        - 10 : THIN_CIRRUS
        - 11 : SNOW or ICE

        Args:
            pixel_size (float): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        mask_path = self._get_path("SCL")

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
        mask = self.open_mask(**kwargs)
        nodata = mask.copy(
            data=np.where(mask == self.raw_no_data, 1, 0).astype(np.uint8)
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

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. WARNING::
            Sentinel-2 datetime is the datatake sensing time, not the granule sensing time !
            (the one displayed in the product's name)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 8, 24, 11, 6, 31)
            >>> prod.get_datetime(as_datetime=False)
            '20200824T110631'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Sentinel-2 datetime (in the filename) is the datatake sensing time, not the granule sensing time !
            sensing_time = self.split_name[2]

            # Convert to datetime
            date = datetime.strptime(sensing_time, "%Y%m%dT%H%M%S")
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name(self) -> str:
        """
        Set product real name.

        Returns:
            str: True name of the product (from metadata)
        """
        return self.tile_mtd["productName"]

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # No need here (_get_name reimplemented)
        pass

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
                    f"Non existing band ({band.name}) for Sentinel-2 cloud products."
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
                    # Use JP2 or COGs here ? COGs seem a better option.
                    band_paths[band] = self._get_path(band_id, ext="tif")
                except FileNotFoundError as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({band_id}) band for {self.path}"
                    ) from ex

        return band_paths

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read Granule metadata.

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = "granule_metadata.xml"
        mtd_archived = r"granule_metadata\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

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
        # The offset is always applied for E84 products: https://github.com/sertit/eoreader/discussions/120#discussioncomment-7751885
        # offset = 0
        quantif_value = 10000.0

        # Compute the correct radiometry of the band
        band_arr = band_arr / quantif_value

        return band_arr.astype(np.float32)

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
        # Get detector footprint to deduce the outside nodata
        mask = self.open_mask(
            size=(band_arr.rio.width, band_arr.rio.height),
        )

        # NO_DATA is 0, SATURATED_OR_DEFECTIVE is 1
        nodata_invalid = np.where(np.isin(mask, [0, 1]), 1, 0).astype(np.uint8)

        return self._set_nodata_mask(band_arr, nodata_invalid)

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

    def _get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile}_{product_type}_{generation_time}).

        Returns:
            str: Condensed name
        """
        # Used to make the difference between 2 products acquired on the same tile at the same date but cut differently
        # Sentinel-2 generation time: "%Y%m%dT%H%M%S" -> save only %H%M%S
        gen_time = self.split_name[-1].split("T")[-1]

        return f"{self.get_datetime()}_{self.constellation.name}_{self.tile_name}_{self.product_type.name}_{gen_time}"

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
        try:
            azimuth_angle = self.stac_mtd["properties"]["view:sun_azimuth"]
            zenith_angle = self.stac_mtd["properties"]["view:sun_elevation"]
        except IndexError as exc:
            raise InvalidProductError(
                "sun_azimuth or sun_elevation not found in metadata!"
            ) from exc

        return azimuth_angle, zenith_angle

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        L1C doesn't have any mask. SCL mask has everything.
        """
        return self.product_type != S2ProductType.L1C

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Values:
        - 0 : NO_DATA
        - 3 : CLOUD_SHADOWS
        - 8 : CLOUD_MEDIUM_PROBABILITY
        - 9 : CLOUD_HIGH_PROBABILITY
        - 10 : THIN_CIRRUS

        Only open clouds with high proba.

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
            # Open Mask
            mask = self.open_mask(pixel_size, size, **kwargs)

            # Don't use load_nodata in order not to load a 2nd time mask
            nodata_id = self.raw_no_data
            shadow_id = 3
            cloud_id = 9
            cirrus_id = 10

            nodata = np.where(mask == nodata_id, 1, 0).astype(np.uint8)

            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(
                        mask, np.isin(mask, [cirrus_id, cloud_id, shadow_id]), nodata
                    )
                elif band == SHADOWS:
                    cloud = self._create_mask(mask, mask == shadow_id, nodata)
                elif band == CLOUDS:
                    cloud = self._create_mask(mask, mask == cloud_id, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(mask, mask == cirrus_id, nodata)
                elif band == RAW_CLOUDS:
                    cloud = mask
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
        try:
            cc = self.stac_mtd["properties"]["eo:cloud_cover"]
        except (InvalidProductError, TypeError):
            LOGGER.warning("'cloud_cover' not found in metadata!")
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
                quicklook_path = self._get_archived_path(regex=r".*.jpg")
            else:
                quicklook_path = str(next(self.path.glob("*.jpg")))
        except (StopIteration, FileNotFoundError):
            pass

        return quicklook_path


class S2E84StacProduct(StacProduct, S2E84Product):
    def __init__(
        self,
        product_path: AnyPathStrType = None,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self.kwargs = kwargs
        """Custom kwargs"""

        # Copy the kwargs
        super_kwargs = kwargs.copy()

        # Get STAC Item
        self.item = self._set_item(product_path, **super_kwargs)

        if not self._is_mpc():
            self.default_clients = [self.get_e84_client(), self.get_sinergise_client()]
        self.clients = super_kwargs.pop("client", self.default_clients)

        if product_path is None:
            # Canonical link is always the second one
            # TODO: check if ok
            product_path = AnyPath(self.item.links[1].target).parent

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.REFL
        self._has_cloud_cover = True
        self._use_filename = False
        self.needs_extraction = False

        # Read the JSON tileinfo mtd
        self.tile_mtd = json.loads(
            self.read_href(self._get_path("tileinfo_metadata"), clients=self.clients),
            cls=CustomDecoder,
        )
        self.stac_mtd = self.item.to_dict()

        # Pre init done by the super class
        super(S2E84Product, self)._pre_init(**kwargs)

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation: force S2."""
        return Constellation.S2

    def _get_path(self, file_id: str, ext="tif") -> str:
        """
        Get either the archived path of the normal path of a tif file

        Args:
            band_id (str): Band ID

        Returns:
            AnyPathType: band path
        """
        if file_id.lower() in self.item.assets:
            asset_name = file_id.lower()
        elif file_id in [band.id for band in self.bands.values() if band is not None]:
            band_name = [
                band_name
                for band_name, band in self.bands.items()
                if band is not None and f"{band.id}" == file_id
            ][0]
            asset_name = EOREADER_STAC_MAP[band_name].value
        else:
            try:
                asset_name = difflib.get_close_matches(
                    file_id, self.item.assets.keys(), cutoff=0.5, n=1
                )[0]
            except Exception as exc:
                raise FileNotFoundError(
                    f"Impossible to find an asset in {list(self.item.assets.keys())} close enough to '{file_id}'"
                ) from exc

        return self.item.assets[asset_name].href

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read Landsat metadata as:

         - :code:`pandas.DataFrame` whatever its collection is (by default for collection 1)
         - XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)

        Args:
            force_pd (bool): If collection 2, return a pandas.DataFrame instead of an XML root + namespace
        Returns:
            Tuple[Union[pd.DataFrame, etree._Element], dict]:
                Metadata as a Pandas.DataFrame or as (etree._Element, dict): Metadata XML root and its namespaces
        """
        return self._read_mtd_xml_stac(self._get_path("granule_metadata"))

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        return self._get_path("thumbnail")
