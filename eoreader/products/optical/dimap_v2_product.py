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
DIMAP V2 super class.
See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
for more information.
"""

import contextlib
import logging
import time
from abc import abstractmethod
from datetime import date, datetime
from enum import unique
from functools import reduce

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from rasterio import crs as riocrs
from rasterio import features, transform
from sertit import geometry, path, rasters, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType
from sertit.vectors import WGS84
from shapely.geometry import Polygon, box

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
    PAN,
    RAW_CLOUDS,
    RED,
    SHADOWS,
    VRE_1,
    VRE_2,
    VRE_3,
    BandNames,
    DimapV2MaskBandNames,
    to_str,
)
from eoreader.bands.band_names import DEEP_BLUE
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import VhrProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.reader import Constellation
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)

_DIMAP_BAND_MTD = {
    PAN: "P",
    BLUE: "B0",
    GREEN: "B1",
    RED: "B2",
    NIR: "B3",
    NARROW_NIR: "B3",
}

_PNEO_BAND_MTD = {
    PAN: "P",
    BLUE: "B",
    GREEN: "G",
    RED: "R",
    NIR: "NIR",
    NARROW_NIR: "NIR",
    VRE_1: "RE",
    VRE_2: "RE",
    VRE_3: "RE",
    CA: "DB",  # deep blue
}


@unique
class DimapV2ProductType(ListEnum):
    """
    DIMAP V2 product types (processing level).

    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    (A.1.1.2 Variable Key Information) for more information.
    """

    SEN = "Primary"
    """
    Primary (L1A), abbreviation for Sensor.
    The Primary product is the geometric processing level closest to the natural image acquired by the sensor.
    """

    PRJ = "Projected"
    """
    Projected (L2A).
    Compared to Primary level, the projected level results from an additional process to map the image
    onto an Earth cartographic system at a fixed altitude value.
    The image is georeferenced without correction from acquisition and terrain off-nadir effects.
    This image-to-map transformation is directly compatible with GIS environment,
    for example to overlay the image on other data.
    """

    ORT = "Ortho Single Image"
    """
    Ortho (L3), single image.
    The Ortho product is a georeferenced image in Earth geometry,
    corrected from acquisition and terrain off-nadir effects.
    The Ortho is produced as a standard, with fully automatic processing.
    """

    MOS = "Ortho Mosaic Image"
    """
    Ortho (L3), mosaic image.
    The Ortho product is a georeferenced image in Earth geometry,
    corrected from acquisition and terrain off-nadir effects.
    The Ortho is produced as a standard, with fully automatic processing.
    """


@unique
class DimapV2RadiometricProcessing(ListEnum):
    """
    DIMAP V2 radiometric processing.

    See `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    (Paragraph 2.4) for more information.
    """

    BASIC = "BASIC"
    """
    In the BASIC radiometric option, the imagery values are digital numbers (DN)
    quantifying the energy recorded by the detector corrected relative
    to the other detectors to avoid non-uniformity noise.
    """

    REFLECTANCE = "REFLECTANCE"
    """
    In the REFLECTANCE radiometric option, the imagery values are corrected
    from radiometric sensor calibration and systematic effects of the atmosphere
    (molecular or Rayleigh diffusion and given in reflectance physical unit).
    """

    LINEAR_STRETCH = "LINEAR_STRETCH"
    """
    Relates to the BASIC option at 8-bit depth.
    """

    SEAMLESS = "SEAMLESS"
    """
    Relates to the mosaic option.
    In this case, the spectral properties cannot be retrieved since the initial images have undergone several radiometric adjustments for aesthetic rendering.
    """

    DISPLAY = "DISPLAY"
    """
    In the Display radiometric option, a true colour curve has been applied to the image directly usable for visualisation on screen. 
    The colour curve is the LUT computed by the Reflectance processing. 
    The image true colour is properly retrieved from sensor calibration and correction of systematic effects of the atmosphere.
    """


@unique
class DimapV2BandCombination(ListEnum):
    """
    DIMAP V2 products band combination

    See `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    (A.1.1.2 Variable Key Information) for more information.
    """

    P = "Panchromatic"
    """
    The Pléiades Panchromatic product includes only one black and white band.
    It covers wavelengths between 0.47 and 0.83 μm of the visible spectrum.
    The product pixel size is 0.5 m (Ortho).
    """

    MS = "Multi Spectral"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    """

    MS_N = "Multi Spectral in natural color"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    (3 bands: BLUE GREEN RED)
    """

    MS_X = "Multi Spectral in false color"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    (3 bands: GREEN RED NIR)
    """

    MS_FS = "Multi Spectral Full"
    """
    Full MS: Multispectral (6 bands).
    Only Pleiades-Neo
    """

    PMS = "Pansharpened Multi Spectral"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product (4 bands)
    """

    PMS_N = "Pansharpened Multi Spectral in natural color"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product
    (3 bands: BLUE GREEN RED)
    """

    PMS_X = "Pansharpened Multi Spectral in false color"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product
    (3 bands: GREEN RED NIR)
    """

    PMS_FS = "Pansharpened Multi Spectral Full"
    """
    Full PMS: Pansharpening (6 bands).
    Only Pleiades-Neo
    """


class DimapV2Product(VhrProduct):
    """
    Super Class of DIMAP V2 products.
    See `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    for more information.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._empty_mask = []
        self._altitude = None
        self._rad_proc = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._has_cloud_cover = True
        self.needs_extraction = False
        self._proj_prod_type = [DimapV2ProductType.SEN, DimapV2ProductType.PRJ]

        # Raw units
        root, _ = self.read_mtd()
        self._rad_proc = DimapV2RadiometricProcessing.from_value(
            root.findtext(".//RADIOMETRIC_PROCESSING")
        )

        if self._rad_proc == DimapV2RadiometricProcessing.REFLECTANCE:
            self._raw_units = RawUnits.REFL
        elif self._rad_proc in [
            DimapV2RadiometricProcessing.BASIC,
            DimapV2RadiometricProcessing.LINEAR_STRETCH,
        ]:
            self._raw_units = RawUnits.DN
        else:
            self._raw_units = RawUnits.NONE

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Band combination
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//SPECTRAL_PROCESSING")
        if not band_combi:
            raise InvalidProductError(
                "Cannot find the band combination (from SPECTRAL_PROCESSING) type in the metadata file"
            )
        self.band_combi = getattr(DimapV2BandCombination, band_combi.replace("-", "_"))

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Not Pansharpened images
        if self.band_combi in [
            DimapV2BandCombination.MS,
            DimapV2BandCombination.MS_X,
            DimapV2BandCombination.MS_N,
            DimapV2BandCombination.MS_FS,
        ]:
            self.pixel_size = self._ms_res
        # Pansharpened images
        else:
            self.pixel_size = self._pan_res

    def _map_bands_core(self, **kwargs) -> None:
        """
        Map bands
        """
        # Open spectral bands
        pan = kwargs.get("pan")
        blue = kwargs.get("blue")
        deep_blue = kwargs.get("deep_blue")
        green = kwargs.get("green")
        red = kwargs.get("red")
        nir = kwargs.get("nir")
        ca = kwargs.get("ca")
        vre = kwargs.get("vre")

        # Manage bands of the product
        if self.band_combi == DimapV2BandCombination.P:
            self.bands.map_bands({PAN: pan.update(id=1)})
        elif self.band_combi == DimapV2BandCombination.MS:
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3),
                    GREEN: green.update(id=2),
                    RED: red.update(id=1),
                    NARROW_NIR: nir.update(id=4),
                    NIR: nir.update(id=4),
                }
            )
        elif self.band_combi == DimapV2BandCombination.PMS:
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3, gsd=self._pan_res),
                    GREEN: green.update(id=2, gsd=self._pan_res),
                    RED: red.update(id=1, gsd=self._pan_res),
                    NARROW_NIR: nir.update(id=4, gsd=self._pan_res),
                    NIR: nir.update(id=4, gsd=self._pan_res),
                }
            )
        elif self.band_combi == DimapV2BandCombination.MS_N:
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3),
                    GREEN: green.update(id=2),
                    RED: red.update(id=1),
                }
            )
        elif self.band_combi == DimapV2BandCombination.PMS_N:
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3, gsd=self._pan_res),
                    GREEN: green.update(id=2, gsd=self._pan_res),
                    RED: red.update(id=1, gsd=self._pan_res),
                }
            )
        elif self.band_combi == DimapV2BandCombination.MS_X:
            self.bands.map_bands(
                {
                    GREEN: green.update(id=1),
                    RED: red.update(id=2),
                    NIR: nir.update(id=3),
                    NARROW_NIR: nir.update(id=3),
                }
            )
        elif self.band_combi == DimapV2BandCombination.PMS_X:
            self.bands.map_bands(
                {
                    GREEN: green.update(id=1, gsd=self._pan_res),
                    RED: red.update(id=2, gsd=self._pan_res),
                    NIR: nir.update(id=3, gsd=self._pan_res),
                    NARROW_NIR: nir.update(id=3, gsd=self._pan_res),
                }
            )
        elif self.band_combi == DimapV2BandCombination.MS_FS:
            # Only PLD-Neo
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3),
                    GREEN: green.update(id=2),
                    RED: red.update(id=1),
                    NIR: nir.update(id=4),
                    NARROW_NIR: nir.update(id=4),
                    VRE_1: vre.update(id=5),
                    VRE_2: vre.update(id=5),
                    VRE_3: vre.update(id=5),
                    CA: ca.update(id=6),
                    DEEP_BLUE: deep_blue.update(id=6),
                }
            )
        elif self.band_combi == DimapV2BandCombination.PMS_FS:
            # Only PLD-Neo
            self.bands.map_bands(
                {
                    BLUE: blue.update(id=3, gsd=self._pan_res),
                    GREEN: green.update(id=2, gsd=self._pan_res),
                    RED: red.update(id=1, gsd=self._pan_res),
                    NIR: nir.update(id=4, gsd=self._pan_res),
                    NARROW_NIR: nir.update(id=4, gsd=self._pan_res),
                    VRE_1: vre.update(id=5, gsd=self._pan_res),
                    VRE_2: vre.update(id=5, gsd=self._pan_res),
                    VRE_3: vre.update(id=5, gsd=self._pan_res),
                    CA: ca.update(id=6, gsd=self._pan_res),
                    DEEP_BLUE: ca.update(id=6, gsd=self._pan_res),
                }
            )
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

    def _set_product_type(self) -> None:
        """Set products type"""

        # Get product type
        try:
            self.product_type = getattr(DimapV2ProductType, self.split_name[3])
        except AttributeError:
            # In some cases...
            self.product_type = getattr(DimapV2ProductType, self.split_name[4])

        # Manage not orthorectified product
        if self.product_type in [DimapV2ProductType.SEN, DimapV2ProductType.PRJ]:
            self.is_ortho = False

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        crs_name = root.findtext(".//GEODETIC_CRS_CODE")
        if not crs_name:
            crs_name = root.findtext(".//PROJECTED_CRS_CODE")
            if not crs_name:
                raise InvalidProductError(
                    "Cannot find the CRS name (from GEODETIC_CRS_NAME or PROJECTED_CRS_CODE) type in the metadata file"
                )

        return riocrs.CRS.from_string(crs_name)

    @cache
    def crs(self) -> riocrs.CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.crs()
            CRS.from_epsg(32618)

        Returns:
            rasterio.crs.CRS: CRS object
        """
        raw_crs = self._get_raw_crs()

        if raw_crs.is_projected:
            utm = raw_crs
        else:
            # Open metadata
            root, _ = self.read_mtd()

            # Open the Bounding_Polygon
            vertices = list(root.iterfind(".//Vertex"))

            # Get the mean lon lat
            lon = float(np.mean([float(v.findtext("LON")) for v in vertices]))
            lat = float(np.mean([float(v.findtext("LAT")) for v in vertices]))

            # Compute UTM crs from center long/lat
            utm = vectors.to_utm_crs(lon, lat)

        return utm

    @cache
    def extent(self, **kwargs) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile.

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Compute extent corners
        corners = [
            [float(vertex.findtext("LON")), float(vertex.findtext("LAT"))]
            for vertex in root.iterfind(".//Dataset_Extent/Vertex")
        ]

        extent_wgs84 = gpd.GeoDataFrame(
            geometry=[Polygon(corners)],
            crs=vectors.WGS84,
        )

        # Not square extent
        utm_extent_raw = extent_wgs84.to_crs(self.crs())

        utm_extent = gpd.GeoDataFrame(
            geometry=[box(*utm_extent_raw.total_bounds)],
            crs=self.crs(),
        )

        return utm_extent

    @cache
    @simplify
    def footprint(self, **kwargs) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((707025.261 9688613.833, 707043.276 9...
            [1 rows x 3 columns]

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return self._open_mask_as_vec("ROI", **kwargs).to_crs(self.crs())

    def get_datetime(self, as_datetime: bool = False) -> str | datetime:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 5, 11, 2, 31, 58)
            >>> prod.get_datetime(as_datetime=False)
            '20200511T023158'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             str | dt.datetime: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()
            date_str = root.findtext(".//IMAGING_DATE")
            time_str = root.findtext(".//IMAGING_TIME")
            if not date_str or not time_str:
                raise InvalidProductError(
                    "Cannot find the product imaging date and time in the metadata file."
                )

            # Convert to datetime
            date_dt = date.fromisoformat(date_str)
            try:
                time_dt = time.strptime(time_str, "%H:%M:%S.%fZ")
            except ValueError:
                try:
                    time_dt = time.strptime(
                        time_str, "%H:%M:%S.%f"
                    )  # Sometimes without a Z
                except ValueError:
                    time_dt = time.strptime(
                        time_str, "%H:%M:%S"
                    )  # Sometimes without microseconds

            date_str = (
                f"{date_dt.strftime('%Y%m%d')}T{time.strftime('%H%M%S', time_dt)}"
            )

            if as_datetime:
                date_str = datetime.strptime(date_str, DATETIME_FMT)

        else:
            date_str = self.datetime
            if not as_datetime:
                date_str = date_str.strftime(DATETIME_FMT)

        return date_str

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        return path.get_filename(self._get_tile_path()).replace("DIM_", "")

    def _manage_invalid_pixels(
        self,
        band_arr: xr.DataArray,
        band: BandNames,
        pixel_size: float = None,
        **kwargs,
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
        # array data
        width = band_arr.rio.width
        height = band_arr.rio.height
        mask_path, mask_exists = self._get_out_path(
            f"{self.condensed_name}_other_masks_{int(width)}x{int(height)}.npy"
        )

        if not mask_exists:
            nodata = self._load_masks(
                [DimapV2MaskBandNames.ROI],
                size=[width, height],
                pixel_size=pixel_size,
                **kwargs,
            )[DimapV2MaskBandNames.ROI]

            # Nodata is where ROI is false (ROI = valid data)
            nodata = rasters.where(
                nodata == self._mask_true, self._mask_false, self._mask_true, nodata
            )

            with contextlib.suppress(InvalidProductError):
                masks = self._load_masks(
                    [DimapV2MaskBandNames.DET, DimapV2MaskBandNames.VIS],
                    pixel_size=pixel_size,
                    size=[width, height],
                    **kwargs,
                )

                mask_det = rasters.collocate(nodata, masks[DimapV2MaskBandNames.DET])
                mask_vis = rasters.collocate(nodata, masks[DimapV2MaskBandNames.VIS])

                nodata = reduce(
                    lambda x, y: x.fillna(0).astype(np.uint8)
                    | y.fillna(0).astype(np.uint8),
                    [
                        nodata,
                        mask_det,
                        mask_vis,
                    ],
                )
            np.save(str(mask_path), nodata)
        else:
            nodata = utils.load_np(mask_path, self._tmp_process)

        return self._set_nodata_mask(band_arr, nodata)

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        See
        `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
        (Appendix D page 103)

        Args:
            band_arr (xr.DataArray):
            band_path (AnyPathType):
            band (BandNames):
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        if self._raw_units == RawUnits.REFL:
            # Compute the correct radiometry of the band
            if utils.is_uint16(band_arr):
                band_arr /= 10000.0
        elif self._raw_units == RawUnits.DN:
            # Convert DN into radiance
            band_arr = self._dn_to_toa_rad(band_arr, band)

            # Convert radiance into reflectance
            band_arr = self._toa_rad_to_toa_refl(band_arr, band)

        else:
            LOGGER.warning(
                f"The spectral properties of a {self._rad_proc.value} radiometric processed image "
                "cannot be retrieved since the initial images have undergone "
                "several radiometric adjustments for aesthetic rendering. "
                "Returned as is."
            )

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

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
        # Get detector footprint to deduce the outside nodata
        LOGGER.debug("Load nodata")
        nodata = self._load_masks(
            [DimapV2MaskBandNames.ROI],
            pixel_size=pixel_size,
            size=[band_arr.rio.width, band_arr.rio.height],
            **kwargs,
        )[DimapV2MaskBandNames.ROI]

        # Nodata is where ROI is false (ROI = valid data)
        # No need to propagate attributes here, it's only a mask that will be applied later: we can use xr.where instead of rasters.where
        nodata = xr.where(nodata == self._mask_true, self._mask_false, self._mask_true)

        LOGGER.debug("Set nodata mask")
        return self._set_nodata_mask(band_arr, nodata)

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1A_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (45.6624568841367, 30.219881316357643)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            center_vals = [
                a
                for a in root.iterfind(".//Located_Geometric_Values")
                if a.findtext("LOCATION_TYPE") == "Center"
            ][0]
            elev_angle = float(center_vals.findtext(".//SUN_ELEVATION"))
            azimuth_angle = float(center_vals.findtext(".//SUN_AZIMUTH"))
        except TypeError as exc:
            raise InvalidProductError(
                "Azimuth or Zenith angles not found in metadata!"
            ) from exc

        # From elevation to zenith
        zenith_angle = 90.0 - elev_angle

        return azimuth_angle, zenith_angle

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

        def incidence_to_off_nadir(inc_angle: float, orbit_h: float = 695000) -> float:
            earth_radius = 6378137
            orbit_coeff = (earth_radius + orbit_h) / earth_radius
            return np.rad2deg(
                np.arcsin(np.sin(np.deg2rad(90 - inc_angle)) / orbit_coeff)
            )

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            center_vals = [
                a
                for a in root.iterfind(".//Located_Geometric_Values")
                if a.findtext("LOCATION_TYPE") == "Center"
            ][0]
            incidence_angle = float(center_vals.findtext(".//INCIDENCE_ANGLE"))
            az = float(center_vals.findtext(".//AZIMUTH_ANGLE"))
        except TypeError as exc:
            raise InvalidProductError(
                "Azimuth or Zenith angles not found in metadata!"
            ) from exc

        # Compute off nadir angles
        off_nadir = incidence_to_off_nadir(
            inc_angle=incidence_angle, orbit_h=self._altitude
        )

        return az, off_nadir, incidence_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "DIM_*.XML"
        mtd_archived = r"DIM_.*\.XML"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band?
        """
        return band not in [CIRRUS, SHADOWS]

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            cld_arr = self._load_masks(
                [DimapV2MaskBandNames.CLD], pixel_size=pixel_size, size=size
            )[DimapV2MaskBandNames.CLD]

            for band in bands:
                if band not in [ALL_CLOUDS, CLOUDS, RAW_CLOUDS]:
                    raise InvalidTypeError(f"Non existing cloud band for: {band}")

                # Rename
                band_name = to_str(band)[0]
                cld_arr.attrs["long_name"] = band_name
                band_dict[band] = cld_arr.rename(band_name).astype(np.float32)

        return band_dict

    def _has_mask(self, mask: BandNames) -> bool:
        """
        Can the specified mask be loaded from this product?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_index(DETFOO)
            True

        Args:
            mask (BandNames): Mask

        Returns:
            bool: True if the specified mask is provided by the current product
        """
        return mask in [
            DimapV2MaskBandNames.CLD,
            DimapV2MaskBandNames.DET,
            DimapV2MaskBandNames.QTE,
            DimapV2MaskBandNames.ROI,
            DimapV2MaskBandNames.SLT,
            DimapV2MaskBandNames.SNW,
            DimapV2MaskBandNames.VIS,
        ]

    def _open_masks(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Open a list of mask files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        for band in bands:
            # Load cloud vector
            mask_vec = self._open_mask_as_vec(band.name, **kwargs)
            has_vec = len(mask_vec) > 0

            # Load default xarray as a template
            def_utm_path = self._get_default_utm_band(pixel_size=pixel_size, size=size)

            with rasterio.open(str(def_utm_path)) as ds:
                if ds.count > 1:
                    def_xarr = utils.read(
                        ds,
                        pixel_size=pixel_size,
                        size=size,
                        indexes=[self.bands[self.get_default_band()].id],
                        **kwargs,
                    )
                else:
                    def_xarr = utils.read(
                        ds, pixel_size=pixel_size, size=size, **kwargs
                    )

            # Load nodata
            width = def_xarr.rio.width
            height = def_xarr.rio.height
            vec_tr = transform.from_bounds(
                *def_xarr.rio.bounds(), def_xarr.rio.width, def_xarr.rio.height
            )

            # Rasterize features if existing vector
            if has_vec:
                mask_path, mask_exists = self._get_out_path(
                    f"{self.condensed_name}_{band.name.lower()}_{int(width)}x{int(height)}.npy"
                )
                if not mask_exists:
                    LOGGER.debug(f"Rasterizing {band.name} mask")
                    # Rasterize nodata
                    mask_arr = features.rasterize(
                        mask_vec.geometry,
                        out_shape=(height, width),
                        fill=self._mask_false,  # Outside vector
                        default_value=self._mask_true,  # Inside vector
                        transform=vec_tr,
                        dtype=np.uint8,
                    )
                    np.save(str(mask_path), mask_arr)
                else:
                    mask_arr = utils.load_np(mask_path, self._tmp_process)

                # Rasterize gives a 2D array, we want a 3D array
                mask_arr = np.expand_dims(mask_arr, axis=0)
            else:
                mask_arr = np.zeros(
                    (1, def_xarr.rio.height, def_xarr.rio.width), dtype=np.uint8
                )

            # Create mask xarray
            mask = (
                def_xarr.copy(
                    data=xr.where(mask_arr, self._mask_true, self._mask_false)
                )
                .fillna(self._mask_nodata)
                .astype(np.uint8)
            )
            mask.rio.write_nodata(self._mask_nodata, inplace=True)
            mask.encoding["dtype"] = np.uint8

            # Rename
            band_name = to_str(band)[0]
            mask.attrs["long_name"] = band_name
            band_dict[band] = mask.rename(band_name)

        return band_dict

    def _open_mask_as_vec(self, mask_str: str, **kwargs) -> gpd.GeoDataFrame:
        """
        Open DIMAP V2 mask (GML files stored in MASKS) as :code:`gpd.GeoDataFrame`.

        Masks than can be called that way are:

        - :code:`CLD`: Cloud vector mask
        - :code:`DET`: Out of order detectors vector mask
        - :code:`QTE`: Synthetic technical quality vector mask
        - :code:`ROI`: Region of Interest vector mask
        - :code:`SLT`: Straylight vector mask
        - :code:`SNW`: Snow vector mask
        - :code:`VIS`: Hidden area vector mask (optional)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"IMG_PHR1A_PMS_001"
            >>> prod.open_mask("ROI")
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((118.86239 -2.81569, 118.86255 -2.815...
            [1 rows x 3 columns]

        Args:
            mask_str (str): Mask name, such as CLD, DET, ROI...

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        # Check inputs
        mandatory_masks = ["CLD", "DET", "QTE", "ROI", "SLT", "SNW"]
        optional_masks = ["VIS"]
        assert mask_str in mandatory_masks + optional_masks
        crs = self.crs()

        mask_name = f"{self.condensed_name}_MSK_{mask_str}.geojson"

        mask_path, mask_exists = self._get_out_path(mask_name)
        if mask_exists:
            mask = vectors.read(mask_path)
        elif mask_str in self._empty_mask:
            # Empty mask cannot be written on file
            mask = gpd.GeoDataFrame(geometry=[], crs=crs)
        else:
            try:
                if self.is_archived:
                    # Open the zip file
                    mask = self._read_archived_vector(
                        archive_regex=rf".*MASKS.*{mask_str}.*\.GML",
                        crs=crs,
                    )
                else:
                    mask_gml_path = path.get_file_in_dir(
                        self.path.joinpath("MASKS"),
                        f"*{mask_str}*.GML",
                        exact_name=True,
                    )

                    mask = vectors.read(mask_gml_path, crs=crs)
            except FileNotFoundError as exc:
                if mask_str in optional_masks:
                    mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                else:
                    raise InvalidProductError(
                        f"Mask {mask_str} not found for {self.path.joinpath('MASKS')}"
                    ) from exc

            # Convert mask to correct CRS
            if not mask.empty and self.product_type in [
                DimapV2ProductType.SEN,
                DimapV2ProductType.PRJ,
            ]:
                # Sometimes the GML mask lacks crs (why?)
                if not mask.crs:
                    mask.crs = self._get_raw_crs()

                mask.crs = WGS84
                LOGGER.info(f"Orthorectifying {mask_str}")

                # Rasterize mask (no transform as we have the vector in image geometry)
                LOGGER.debug(f"\tRasterizing {mask_str}")
                tile = utils.read(self._get_tile_path())[0:1, ...]

                mask_raster = rasters.rasterize(
                    tile,
                    mask,
                    default_nodata=self._mask_false,  # Outside vector
                    default_value=self._mask_true,  # Inside vector
                    dtype=np.uint8,
                )
                # Check mask validity (to avoid reprojecting)
                # All null
                if mask_raster.max() == 0:
                    mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                else:
                    ortho_name = f"{path.get_filename(mask_name)}_ortho.tif"
                    ortho_path, ortho_exists = self._get_out_path(ortho_name)
                    if not ortho_exists:
                        # Reproject mask raster
                        LOGGER.debug(f"\tReprojecting {mask_str}")
                        dem_path = self._get_dem_path(**kwargs)

                        # TODO: change this when available in rioxarray
                        # See https://github.com/corteva/rioxarray/issues/837
                        with rasterio.open(str(self._get_tile_path())) as ds:
                            rpcs = ds.rpcs

                        reproj_data = self._orthorectify(
                            mask_raster,
                            rpcs=rpcs,
                            dem_path=dem_path,
                            ortho_path=ortho_path,
                            long_name=mask_str,
                            **kwargs,
                        )
                    else:
                        reproj_data = utils.read(ortho_path)

                    # Vectorize mask raster
                    LOGGER.debug(f"\tRevectorizing {mask_str}")
                    mask = rasters.vectorize(
                        reproj_data,
                        values=self._mask_true,
                        default_nodata=self._mask_false,
                    )

                    # Do not keep pixelized mask
                    mask = geometry.simplify_footprint(mask, self.pixel_size)

            # Sometimes the GML mask lacks crs (why?)
            elif (
                not mask.empty
                and not mask.crs
                and self.product_type
                in [
                    DimapV2ProductType.ORT,
                    DimapV2ProductType.MOS,
                ]
            ):
                # Convert to target CRS
                mask.crs = self._get_raw_crs()
                mask = mask.to_crs(self.crs())

            # Save to file
            if mask.empty:
                # Empty mask cannot be written on file
                self._empty_mask.append(mask_str)
            else:
                mask.to_file(str(mask_path), driver="GeoJSON")

        return mask

    def _get_tile_path(self) -> AnyPathType:
        """
        Get the DIMAP filepath

        Returns:
            AnyPathType: DIMAP filepath

        """
        return self._get_path("DIM_", "XML")

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        See
        `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
        for more information. (Appendix D page 103)

        Args:
            dn_arr (xr.DataArray): DN array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Radiance array
        """
        if self.constellation == Constellation.PNEO:
            band_mtd_str = _PNEO_BAND_MTD[band]
        else:
            band_mtd_str = _DIMAP_BAND_MTD[band]

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Convert DN to TOA radiance
        # <MEASURE_DESC>Raw radiometric counts (DN) to TOA Radiance (L). Formulae L=DN/GAIN+BIAS</MEASURE_DESC>
        try:
            rad_gain = None
            rad_bias = None
            for br in root.iterfind(".//Band_Radiance"):
                if br.findtext("BAND_ID") == band_mtd_str:
                    rad_gain = float(br.findtext("GAIN"))
                    rad_bias = float(br.findtext("BIAS"))
                    break

            if rad_gain is None or rad_bias is None:
                raise TypeError

        except TypeError as exc:
            raise InvalidProductError(
                "GAIN and BIAS from Band_Radiance not found in metadata!"
            ) from exc
        return dn_arr / rad_gain + rad_bias

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        See
        `here <https://engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
        for more information. (Appendix D page 103)

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        if self.constellation == Constellation.PNEO:
            band_mtd_str = _PNEO_BAND_MTD[band]
        else:
            band_mtd_str = _DIMAP_BAND_MTD[band]

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Get the solar irradiance value of raw radiometric Band (in watt/m2/micron)
        try:
            e0 = None
            for br in root.iterfind(".//Band_Solar_Irradiance"):
                if br.findtext("BAND_ID") == band_mtd_str:
                    e0 = float(br.findtext("VALUE"))
                    break

            if e0 is None:
                raise TypeError

        except TypeError as exc:
            raise InvalidProductError(
                "VALUE from Band_Solar_Irradiance not found in metadata!"
            ) from exc

        return self._toa_rad_to_toa_refl_formula(rad_arr, e0)

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
            cc = float(root.findtext(".//CLOUD_COVERAGE"))
        except (InvalidProductError, TypeError):
            LOGGER.warning("'CLOUD_COVERAGE' not found in metadata!")
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
                quicklook_path = self.path / self._get_archived_path(
                    regex=".*PREVIEW.*JPG"
                )
            else:
                quicklook_path = next(self.path.glob("*PREVIEW*.JPG"))
            quicklook_path = str(quicklook_path)
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[-1]

    @abstractmethod
    def _map_bands(self) -> None:
        """
        Map bands
        """
        raise NotImplementedError

    @abstractmethod
    def _set_instrument(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError
