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
Vision-1 products.
See `here <https://www.intelligence-airbusds.com/imagery/constellation/vision1/>`_
for more information.
"""
import io
import logging
import time
from datetime import date, datetime
from enum import unique
from pathlib import Path
from typing import Union

import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import crs as riocrs
from sertit import files, vectors
from sertit.misc import ListEnum

from eoreader import cache, utils
from eoreader._stac import *
from eoreader.bands import BandNames, SpectralBand
from eoreader.bands import spectral_bands as spb
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

_VIS1_E0 = {
    spb.PAN: 1828,
    spb.BLUE: 2003,
    spb.GREEN: 1828,
    spb.RED: 1618,
    spb.NIR: 1042,
    spb.NARROW_NIR: 1042,
}
"""
Solar spectral irradiance, E0b, (commonly known as ESUN) is a constant value specific to each band of the Vision-1 imager.
It is determined by using well know models of Solar Irradiance with the measured spectral transmission of the imager for each incident wavelength.
It has units of Wm-2μm-1. The applicable values for Vision-1 are provided in the table.
"""


@unique
class Vis1BandCombination(ListEnum):
    """
    band combination of Vision-1 data
    See :code:`vision-1-imagery-user-guide-20210217.pdf` file for more information.
    """

    BUN = "Bundle"
    """
    BUN products provide both the 4-band multispectral, and the panchromatic data
    from the same acquisition in a single product package. Data is provided as 16-bit
    GeoTiffs with pixel sizes of 3.5m and 0.87m for MS and PAN data respectively.
    """

    PSH = "Pansharpened"
    """
    Pansharpened products combine the spectral information of the four multispectral
    bands with the high-resolution detail provided within the panchromatic data,
    resulting in a single 0.87m colour product.
    """

    MS4 = "Multispectral"
    """
    The single multispectral product includes four multispectral (colour) bands: Blue,
    Green, Red and Near Infrared. The product pixel size is 3.5m.
    """

    PAN = "Panchromatic"
    """
    The Vision-1 panchromatic product includes data contained within a single high-
    resolution black and white band. It covers wavelengths between 450 and 650nm
    within the visible spectrum. The product pixel size is 0.87m.
    """


@unique
class Vis1ProductType(ListEnum):
    """
    This is the processing level of the given product, either projected or orthorectified.
    See :code:`vision-1-imagery-user-guide-20210217.pdf` file for more information.
    """

    PRJ = "PROJECTED"
    """
    Projected (not ortho)
    """

    ORTP = "ORTHORECTIFIED"
    """
    Orthorectified
    """


class Vis1Product(VhrProduct):
    """
    Class of Vision-1 products.
    See `here <https://www.intelligence-airbusds.com/imagery/constellation/vision1/>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._pan_res = 0.9
        self._ms_res = 3.5
        self.needs_extraction = False
        self._proj_prod_type = [Vis1ProductType.PRJ]

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.band_combi = getattr(Vis1BandCombination, self.split_name[1])

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # Not Pansharpened images
        if self.band_combi == Vis1BandCombination.MS4:
            return self._ms_res
        # Pansharpened images
        else:
            return self._pan_res

    def _set_product_type(self) -> None:
        """
        Set products type

        See Vision-1_web_201906.pdf for more information.
        """
        # Get MTD XML file
        prod_type = self.split_name[3]
        self.product_type = getattr(Vis1ProductType, prod_type)

        # Create spectral bands
        pan = SpectralBand(
            eoreader_name=spb.PAN,
            **{NAME: "PAN", ID: 1, GSD: self._pan_res, WV_MIN: 450, WV_MAX: 650},
        )

        blue = SpectralBand(
            eoreader_name=spb.BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self._ms_res, WV_MIN: 440, WV_MAX: 510},
        )

        green = SpectralBand(
            eoreader_name=spb.GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self._ms_res, WV_MIN: 510, WV_MAX: 590},
        )

        red = SpectralBand(
            eoreader_name=spb.RED,
            **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 600, WV_MAX: 670},
        )

        nir = SpectralBand(
            eoreader_name=spb.NIR,
            **{NAME: "NIR", ID: 4, GSD: self._ms_res, WV_MIN: 760, WV_MAX: 910},
        )

        # Manage bands of the product
        if self.band_combi == Vis1BandCombination.PAN:
            self.bands.map_bands({spb.PAN: pan})
        elif self.band_combi in [
            Vis1BandCombination.MS4,
            Vis1BandCombination.BUN,
        ]:
            self.bands.map_bands(
                {
                    spb.BLUE: blue,
                    spb.GREEN: green,
                    spb.RED: red,
                    spb.NIR: nir,
                    spb.NARROW_NIR: nir,
                }
            )
            if self.band_combi == Vis1BandCombination.BUN:
                LOGGER.warning(
                    "Bundle mode has never been tested by EOReader, use it at your own risk!"
                )
        elif self.band_combi == Vis1BandCombination.PSH:
            self.bands.map_bands(
                {
                    spb.BLUE: blue.update(gsd=self._pan_res),
                    spb.GREEN: green.update(gsd=self._pan_res),
                    spb.RED: red.update(gsd=self._pan_res),
                    spb.NIR: nir.update(gsd=self._pan_res),
                    spb.NARROW_NIR: nir.update(gsd=self._pan_res),
                }
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
        # Open metadata
        root, _ = self.read_mtd()

        # Open the Bounding_Polygon
        vertices = list(root.iterfind(".//Dataset_Frame/Vertex"))

        # Get the mean lon lat
        lon = float(np.mean([float(v.findtext("FRAME_LON")) for v in vertices]))
        lat = float(np.mean([float(v.findtext("FRAME_LAT")) for v in vertices]))

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
        crs_name = root.findtext(".//HORIZONTAL_CS_CODE")
        if not crs_name:
            crs_name = root.findtext(".//GEOGRAPHIC_CS_CODE")
            if not crs_name:
                raise InvalidProductError(
                    "Cannot find the CRS name (from GEOGRAPHIC_CS_CODE or HORIZONTAL_CS_CODE) type in the metadata file"
                )

        return riocrs.CRS.from_string(crs_name)

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
        # TODO: SAME AS DIMAP
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
                time_dt = time.strptime(
                    time_str, "%H:%M:%S.%f"
                )  # Sometimes without a Z

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

    def _get_name_sensor_specific(self) -> str:
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

        # Compute the correct radiometry of the band
        original_dtype = band_arr.encoding.get("dtype", band_arr.dtype)
        if original_dtype == "uint16":
            band_arr /= 100.0

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return self._toa_rad_to_toa_refl(band_arr, band)

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = "DIM_*.xml"
        mtd_archived = r"DIM_.*\.xml"

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

    def _get_tile_path(self) -> Union[CloudPath, Path]:
        """
        Get the DIMAP filepath

        Returns:
            Union[CloudPath, Path]: DIMAP filepath
        """
        return self._get_path("DIM_", "xml")

    def _get_ortho_path(self, **kwargs) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """
        # Compute RPCSs
        if self.is_archived:
            rpcs_file = io.BytesIO(files.read_archived_file(self.path, r".*\.rpc"))
        else:
            rpcs_file = self.path.joinpath(self.name + ".rpc")

        rpcs = utils.open_rpc_file(rpcs_file)
        return super()._get_ortho_path(rpcs=rpcs, **kwargs)

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
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

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        # Compute the coefficient converting TOA radiance in TOA reflectance
        dt = self._sun_earth_distance_variation()
        _, sun_zen = self.get_mean_sun_angles()
        rad_sun_zen = np.deg2rad(sun_zen)
        e0 = _VIS1_E0[band]
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
                    self.path, file_regex="Preview.tif"
                )
            else:
                quicklook_path = str(next(self.path.glob("Preview.tif")))
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path
