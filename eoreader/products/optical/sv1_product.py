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
SuperView-1 products.
See `here <http://en.spacewillinfo.com/uploads/soft/210106/8-210106153503.pdf>`_
for more information.
"""
import logging
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import pytz
import rasterio
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import crs as riocrs
from sertit import files, rasters_rio, vectors
from sertit.misc import ListEnum
from shapely.geometry import box

from eoreader import cache
from eoreader.bands import BandNames, SpectralBand
from eoreader.bands import spectral_bands as spb
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import DATETIME_FMT, EOREADER_NAME, simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Sv1BandCombination(ListEnum):
    """
    Band combination of SuperView-1 data
    See :code:`http://en.spacewillinfo.com/uploads/soft/210106/8-210106153503.pdf` file for more information.
    """

    PMS = "Panchromatic and Multiple Spectral"
    """
    The product is combined of panchromatic and multiple spectral bands.
    - Panchromatic (PAN): The product includes 1 band and is black and white, its ground sampling distance (GSD) is 50 cm;
    - Multiple Spectral (MUX): The product includes 4 bands that are Blue, Green, Red and Near-infrared. The ground sampling distance (GSD) is 2 meters.
    """

    PSH = "Pansharpened"
    """
    Pan-sharpened product combines the visual information of the multispectral data with the spatial information of the panchromatic data, resulting in a higher resolution color product.
    SuperView-1 pan-sharpen imagery products are offered as 4-band and stereo products.
    The GSD of a pan-sharpened product is 0.5 m.
    The Pan-sharpened product is delivered with geotiff format.
    """


@unique
class Sv1ProductType(ListEnum):
    """
    This is the processing level of SuperView-1 data
    See :code:`http://en.spacewillinfo.com/uploads/soft/210106/8-210106153503.pdf` file for more information.

    **Note**: Stereo product are not handled.
    """

    L1B = "Basic Product"
    """
    Basic Products are radiometrically corrected and sensor corrected, but not geometrically corrected or projected to a plane using a map projection or datum.
    The sensor correction blends all pixels from all detectors into the synthetic array to form a single image.
    The main radiometric processing includes:
    - Relative radiometric response between detectors;
    - Correction of differences in sensitivity between the detectors;

    The sensor corrections include:
    - Internal detector geometry;
    - Optical distortion correction;
    - Registration of the panchromatic and multispectral bands
    """

    L2A = "Ortho Ready Standard Product"
    """
    Ortho Ready Standard Products are radiometrically corrected, sensor corrected, and projected to a ellipsoid using current image mean elevation for each panchromatic and multispectral.
    All Ortho Ready Standard Products can have a uniform GSD throughout the entire product.
    The default projection is UTM projection.
    Ortho Ready Standard Products are available in panchromatic at 0.5 meters and multi-spectral bands at 2 meters.
    The radiometric corrections applied to the Ortho Ready Standard Product include relative radiometric response between detectors and non-responsive detectors.
    The sensor corrections include internal detector geometry, optical distortion, scan distortion, any line-rate variations, and registration of the panchromatic and multispectral bands.
    Geometric corrections remove spacecraft orbit position and attitude uncertainty, Earth rotation and curvature, and panoramic distortion.
    """


class Sv1Product(VhrProduct):
    """
    Class of SuperView-1 products.
    See :code:`http://en.spacewillinfo.com/uploads/soft/210106/8-210106153503.pdf` file for more information.
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._pan_res = 0.5
        self._ms_res = 2.0
        self.needs_extraction = False
        self._proj_prod_type = [Sv1ProductType.L1B]

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        try:
            if self.is_archived:
                files.get_archived_path(self.path, r".*PSH\.xml")
            else:
                next(self.path.glob("*PSH.xml"))
            self.band_combi = Sv1BandCombination.PSH
        except (FileNotFoundError, StopIteration):
            self.band_combi = Sv1BandCombination.PMS

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        # Not Pansharpened images
        if self.band_combi == Sv1BandCombination.PMS:
            # TODO: manage default resolution for PAN band ?
            return self._ms_res
        # Pansharpened images
        else:
            return self._pan_res

    def _set_instrument(self) -> None:
        """
        Set instrument

        SuperView-1: https://space-test.oscar.wmo.int/oscar-test/instruments/view/pms_3
        """
        self.instrument = "PMS-3"

    def _set_product_type(self) -> None:
        """
        Set products type

        See Vision-1_web_201906.pdf for more information.
        """
        # Get MTD XML file
        prod_type = self.split_name[2][:3]
        self.product_type = getattr(Sv1ProductType, prod_type)

        # Manage not orthorectified product
        if self.product_type == Sv1ProductType.L1B:
            self.is_ortho = False

    def _map_bands(self) -> None:
        """
        Map bands, see https://space-test.oscar.wmo.int/oscar-test/instruments/view/pms_3
        """
        # Create spectral bands
        pan = SpectralBand(
            eoreader_name=spb.PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 450, WV_MAX: 900},
        )

        blue = SpectralBand(
            eoreader_name=spb.BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self._ms_res, WV_MIN: 450, WV_MAX: 520},
        )

        green = SpectralBand(
            eoreader_name=spb.GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self._ms_res, WV_MIN: 520, WV_MAX: 590},
        )

        red = SpectralBand(
            eoreader_name=spb.RED,
            **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 630, WV_MAX: 690},
        )

        nir = SpectralBand(
            eoreader_name=spb.NIR,
            **{NAME: "NIR", ID: 4, GSD: self._ms_res, WV_MIN: 770, WV_MAX: 890},
        )

        # Manage bands of the product
        if self.band_combi == Sv1BandCombination.PMS:
            self.bands.map_bands(
                {
                    spb.PAN: pan,
                    spb.BLUE: blue,
                    spb.GREEN: green,
                    spb.RED: red,
                    spb.NIR: nir,
                    spb.NARROW_NIR: nir,
                }
            )
        elif self.band_combi == Sv1BandCombination.PSH:
            self.bands.map_bands(
                {
                    spb.BLUE: blue,
                    spb.GREEN: green,
                    spb.RED: red,
                    spb.NIR: nir,
                    spb.NARROW_NIR: nir,
                }
            )
            LOGGER.warning(
                "Bundle mode has never been tested by EOReader, use it at your own risk!"
            )
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

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

            # Get the mean lon lat
            lon = float(root.findtext(".//CenterLongitude"))
            lat = float(root.findtext(".//CenterLatitude"))

            # Compute UTM crs from center long/lat
            utm = vectors.corresponding_utm_projection(lon, lat)
            utm = riocrs.CRS.from_string(utm)

        return utm

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        crs_name = root.findtext(".//MapProjection")

        if not crs_name:
            crs_name = vectors.WGS84

        return riocrs.CRS.from_string(crs_name)

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        if self.is_archived:
            footprint = vectors.read(self.path, archive_regex=r".*\.shp")
        else:
            footprint = vectors.read(next(self.path.glob("*.shp")))

        return footprint.to_crs(self.crs())

    @cache
    def extent(self, **kwargs) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile.

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        return gpd.GeoDataFrame(
            geometry=[box(*self.footprint().total_bounds)],
            crs=self.crs(),
        )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        **Note**:
        According to :code:`http://en.spacewillinfo.com/uploads/soft/210106/8-210106153503.pdf`:,
        all absolute times are in Beijing Time in the format of :code:`YYYY-MM-DDThh:mm:ss.ddddddZ`:, unless otherwise specified!

        The datetime is then be converted to UTC.

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
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()
            datetime_str = root.findtext(".//StartTime")
            if not datetime_str:
                raise InvalidProductError("Cannot find StartTime in the metadata file.")

            # WARNING: in Beijing time!
            date_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=pytz.timezone("Asia/Shanghai")
            )

            # Convert to UTC time
            date_utc = date_dt.astimezone(pytz.UTC)

        else:
            date_utc = self.datetime

        # Remove timezone
        date_utc = date_utc.replace(tzinfo=None)

        # Convert to str
        if not as_datetime:
            date_utc = date_utc.strftime(DATETIME_FMT)

        return date_utc

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """

        try:
            if self.is_archived:
                footprint_path = files.get_archived_path(self.path, r".*\.shp")
            else:
                footprint_path = next(self.path.glob("*.shp"))
        except (FileNotFoundError, StopIteration):
            raise InvalidProductError(
                "Footprint shapefile cannot be found in the product!"
            )

        # Open identifier
        name = files.get_filename(footprint_path)

        return name

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
        zenith_angle = float(root.findtext(".//SolarZenith"))
        azimuth_angle = float(root.findtext(".//SolarAzimuth"))

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
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            az = float(root.findtext(".//SatelliteAzimuth"))
            off_nadir = float(root.findtext(".//ViewAngle"))
            incidence_angle = float(root.findtext(".//incidenceAngle"))
        except TypeError:
            raise InvalidProductError(
                "SatelliteAzimuth, ViewAngle or incidenceAngle not found in metadata!"
            )

        return az, off_nadir, incidence_angle

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
        # Delivered in uint16

        # Convert DN into radiance
        band_arr = self._dn_to_toa_rad(band_arr, band)

        # Convert radiance into reflectance
        band_arr = self._toa_rad_to_toa_refl(band_arr, band)

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "MUX*.xml"
        mtd_archived = r"MUX.*\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    @cache
    def read_pan_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the PAN metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "PAN*.xml"
        mtd_archived = r"PAN.*\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        return False

    def _open_clouds(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        return {}

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
            raw_band_paths[band] = self._get_tile_path(band=band, **kwargs)
        return raw_band_paths

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
                    path = self._get_ortho_path(band=band, **kwargs)
                else:
                    path = reproj_path

                band_paths[band] = path

        return band_paths

    def _get_tile_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get the VHR tile path

        Returns:
            Union[CloudPath, Path]: VHR filepath
        """
        band = kwargs.pop("band")
        if band == spb.PAN:
            tile_path = self._get_path("PAN", "tiff")
        else:
            tile_path = self._get_path("MUX", "tiff")

        return tile_path

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
                with rasterio.open(str(self._get_tile_path(**kwargs))) as src:

                    out_arr, meta = self._reproject(
                        src.read(), src.meta, src.rpcs, dem_path, **kwargs
                    )
                    rasters_rio.write(out_arr, meta, ortho_path)

        else:
            ortho_path = self._get_tile_path(**kwargs)

        return ortho_path

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        See
        `here <https://apollomapping.com/image_downloads/Maxar_AbsRadCalDataSheet2018v0.pdf>`_
        for more information.

        Args:
            dn_arr (xr.DataArray): DN array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Radiance array
        """
        if band == spb.PAN:
            # Get PAN MTD XML file
            root, _ = self.read_pan_mtd()
            gain = float(root.findtext(".//Gain"))
            offset = float(root.findtext(".//Offset"))

        else:
            band_idx = self.bands[band].id - 1

            # Get MUX MTD XML file
            root, _ = self.read_mtd()
            gain = float(root.findtext(".//Gain").split(",")[band_idx])
            offset = float(root.findtext(".//Offset").split(",")[band_idx])

        # Compute the coefficient converting DN in TOA radiance
        return dn_arr.copy(data=gain * dn_arr.data + offset)

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        See
        `here <https://apollomapping.com/image_downloads/Maxar_AbsRadCalDataSheet2018v0.pdf>`_
        for more information.

        WARNING: in this formula, d**2 = 1 / sqrt(dt) !

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        if band == spb.PAN:
            # Get PAN MTD XML file
            root, _ = self.read_pan_mtd()
            e0 = float(root.findtext(".//ESUN"))

        else:
            band_idx = self.bands[band].id - 1

            # Get MUX MTD XML file
            root, _ = self.read_mtd()
            e0 = float(root.findtext(".//ESUN").split(",")[band_idx])

        # Compute the coefficient converting TOA radiance in TOA reflectance
        dt = self._sun_earth_distance_variation() ** 2
        _, sun_zen = self.get_mean_sun_angles()
        rad_sun_zen = np.deg2rad(sun_zen)
        toa_refl_coeff = np.pi / (e0 * dt * np.cos(rad_sun_zen))

        # LOGGER.debug(f"rad to refl coeff = {toa_refl_coeff}")
        return rad_arr.copy(data=toa_refl_coeff * rad_arr)

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = files.get_archived_rio_path(
                    self.path, file_regex=r".*MUX\.jpg"
                )
            else:
                quicklook_path = str(next(self.path.glob("*MUX.jpg")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[2][3:]
