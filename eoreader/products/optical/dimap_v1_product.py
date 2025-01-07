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
DIMAP V1.1 products.

- VISION-1
- GEOSAT-2 (ex DEIMOS-2)
"""

import logging
import time
from abc import abstractmethod
from datetime import date, datetime
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import crs as riocrs
from sertit import geometry, rasters, vectors
from shapely.geometry import Polygon, box

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.bands import BandNames
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


class DimapV1Product(VhrProduct):
    """
    Super Class of DIMAP V1.1 products.
    """

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
            vertices = list(root.iterfind(".//Dataset_Frame/Vertex"))

            # Get the mean lon lat
            lon = float(np.mean([float(v.findtext("FRAME_LON")) for v in vertices]))
            lat = float(np.mean([float(v.findtext("FRAME_LAT")) for v in vertices]))

            # Compute UTM crs from center long/lat
            utm = vectors.to_utm_crs(lon, lat)

        return utm

    @abstractmethod
    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        raise NotImplementedError

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
            [float(vertex.findtext("FRAME_LON")), float(vertex.findtext("FRAME_LAT"))]
            for vertex in root.iterfind(".//Dataset_Frame/Vertex")
        ]

        # When PRJ, Dataset_Frame is the footprint
        ds_frame = gpd.GeoDataFrame(
            geometry=[Polygon(corners)],
            crs=vectors.WGS84,
        ).to_crs(self.crs())

        extent = gpd.GeoDataFrame(
            geometry=[box(*ds_frame.total_bounds)],
            crs=self.crs(),
        )

        return extent

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
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
        # If ortho -> nodata is not set !
        if self.is_ortho:
            # Get footprint of the first band of the stack
            footprint_dezoom = 10
            arr = rasters.read(
                self.get_default_band_path(),
                resolution=self.pixel_size * footprint_dezoom,
                indexes=[1],
            )

            # Just in case
            arr = arr.fillna(0)

            # Vectorize the nodata band
            footprint = rasters.vectorize(
                arr, values=0, keep_values=False, dissolve=True
            )
            footprint = geometry.get_wider_exterior(footprint)
        else:
            # If not ortho -> default band has been orthorectified and nodata will be set
            footprint = rasters.get_footprint(self.get_default_band_path())

        return footprint.to_crs(self.crs())

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
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
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # GeoSAT-2
            date_str = root.findtext(".//START_TIME")

            if date_str:
                date_str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").strftime(
                    DATETIME_FMT
                )
            else:
                # Vision-1
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
                    # Sometimes without a Z
                    try:
                        time_dt = time.strptime(time_str, "%H:%M:%S.%f")
                    except ValueError:
                        # Sometimes without MICROSECONDS
                        time_dt = time.strptime(time_str, "%H:%M:%S")

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
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        name = root.findtext(".//DATASET_NAME")
        if not name:
            raise InvalidProductError("DATASET_NAME not found in metadata!")

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
        elev_angle = float(root.findtext(".//SUN_ELEVATION"))
        azimuth_angle = float(root.findtext(".//SUN_AZIMUTH"))

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
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open sensor azimuth, off nadir and incidence angles
        try:
            az = None
            for a in root.iterfind(".//Quality_Parameter"):
                if a.findtext("QUALITY_PARAMETER_CODE") == "SPACEMETRIC:SENSOR_AZIMUTH":
                    az = float(a.findtext("QUALITY_PARAMETER_VALUE"))
                    break

            incidence_angle = 90 - float(root.findtext(".//INCIDENCE_ANGLE"))
            off_nadir = float(root.findtext(".//VIEWING_ANGLE"))
        except TypeError as exc:
            raise InvalidProductError(
                "SPACEMETRIC:SENSOR_AZIMUTH, INCIDENCE_ANGLE or VIEWING_ANGLE not found in metadata!"
            ) from exc

        return az, off_nadir, incidence_angle

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band ?
        """
        return False

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        return {}

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames, e0: float, dt: float = None
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        See
        `here <https://www.intelligence-airbusds.com/automne/api/docs/v1.0/document/download/ZG9jdXRoZXF1ZS1kb2N1bWVudC02ODMwNQ==/ZG9jdXRoZXF1ZS1maWxlLTY4MzAy/vision-1-imagery-user-guide-20210217>`_
        (3.2.2) for more information.

        WARNING: in this formula, d**2 = 1 / sqrt(dt) !

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band
            e0 (float): Solar spectral irradiance for the current band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        # Compute the coefficient converting TOA radiance in TOA reflectance
        if not dt:
            dt = self._sun_earth_distance_variation()
        _, sun_zen = self.get_mean_sun_angles()
        rad_sun_zen = np.deg2rad(sun_zen)
        toa_refl_coeff = np.pi / (e0 * dt * np.cos(rad_sun_zen))

        # LOGGER.debug(f"rad to refl coeff = {toa_refl_coeff}")
        return rad_arr.copy(data=toa_refl_coeff * rad_arr)

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[-2]
