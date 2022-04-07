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
Maxar sensors (GeoEye, WorldViews...) class.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
for more information.
"""
import logging
from abc import abstractmethod
from collections import namedtuple
from datetime import datetime
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

from eoreader import cache
from eoreader.bands import BandNames
from eoreader.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.reader import Platform
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

MAXAR_BAND_MTD = {
    obn.NIR: "N",
    obn.NARROW_NIR: "N",
    obn.RED: "R",
    obn.GREEN: "G",
    obn.BLUE: "B",
    obn.WV: "N2",
    obn.VRE_1: "RE",
    obn.VRE_2: "RE",
    obn.VRE_3: "RE",
    obn.YELLOW: "Y",
    obn.CA: "C",
    obn.PAN: "P",
}

GainOffset = namedtuple("GainOffset", ["gain", "offset"], defaults=[1.0, 0.0])
MAXAR_GAIN_OFFSET = {
    Platform.GE01: {
        obn.PAN: GainOffset(gain=1.001, offset=0.0),
        obn.BLUE: GainOffset(gain=1.041, offset=0.0),
        obn.GREEN: GainOffset(gain=0.972, offset=0.0),
        obn.RED: GainOffset(gain=0.979, offset=0.0),
        obn.NIR: GainOffset(gain=0.951, offset=0.0),
        obn.NARROW_NIR: GainOffset(gain=0.951, offset=0.0),
    },  # 2018v0
    Platform.WV02: {
        obn.PAN: GainOffset(gain=0.949, offset=-5.523),
        obn.CA: GainOffset(gain=1.203, offset=-11.839),
        obn.BLUE: GainOffset(gain=1.002, offset=-9.835),
        obn.GREEN: GainOffset(gain=0.953, offset=-7.218),
        obn.YELLOW: GainOffset(gain=0.946, offset=-5.675),
        obn.RED: GainOffset(gain=0.955, offset=-5.046),
        obn.VRE_1: GainOffset(gain=0.980, offset=-6.114),
        obn.VRE_2: GainOffset(gain=0.980, offset=-6.114),
        obn.VRE_3: GainOffset(gain=0.980, offset=-6.114),
        obn.NIR: GainOffset(gain=0.966, offset=-5.096),
        obn.NARROW_NIR: GainOffset(gain=0.966, offset=-5.096),
        obn.WV: GainOffset(gain=1.01, offset=-4.059),
    },  # 2018v0
    Platform.WV03: {
        obn.PAN: GainOffset(gain=0.955, offset=-5.505),
        obn.CA: GainOffset(gain=0.938, offset=-13.099),
        obn.BLUE: GainOffset(gain=0.946, offset=-9.409),
        obn.GREEN: GainOffset(gain=0.958, offset=-7.771),
        obn.YELLOW: GainOffset(gain=0.979, offset=-5.489),
        obn.RED: GainOffset(gain=0.969, offset=-4.579),
        obn.VRE_1: GainOffset(gain=1.027, offset=-5.552),
        obn.VRE_2: GainOffset(gain=1.027, offset=-5.552),
        obn.VRE_3: GainOffset(gain=1.027, offset=-5.552),
        obn.NIR: GainOffset(gain=0.977, offset=-6.508),
        obn.NARROW_NIR: GainOffset(gain=0.977, offset=-6.508),
        obn.WV: GainOffset(gain=1.007, offset=-3.699),
    },  # 2018v0
    Platform.WV04: {
        obn.PAN: GainOffset(gain=1.0, offset=0.0),
        obn.BLUE: GainOffset(gain=1.0, offset=0.0),
        obn.GREEN: GainOffset(gain=1.0, offset=0.0),
        obn.RED: GainOffset(gain=1.0, offset=0.0),
        obn.NIR: GainOffset(gain=1.0, offset=0.0),
        obn.NARROW_NIR: GainOffset(gain=1.0, offset=0.0),
    },  # 2017v0
    Platform.QB: {
        obn.PAN: GainOffset(gain=0.870, offset=-1.491),
        obn.BLUE: GainOffset(gain=1.105, offset=-2.820),
        obn.GREEN: GainOffset(gain=1.071, offset=-3.338),
        obn.RED: GainOffset(gain=1.060, offset=-2.954),
        obn.NIR: GainOffset(gain=1.020, offset=-4.722),
        obn.NARROW_NIR: GainOffset(gain=1.020, offset=-4.722),
    },  # 2016v0.Int
    Platform.WV01: {
        obn.PAN: GainOffset(gain=1.016, offset=-1.824),
    },  # 2016v0.Int
}
"""
The TDI specific abscalfactor and effectiveBandwidth are delivered with the imagery in the metadata file. The
digital number, DN, is the pixel value found in the imagery. The Gain and Offset are the absolute radiometric
calibration band dependent adjustment factors that are given in Table 1. Note that these are not necessarily
stagnant values and they are revisited annually.

Only using last calibration as the Maxar sensors have been found to be very stable throughout their lifetime.

See `here <https://apollomapping.com/image_downloads/Maxar_AbsRadCalDataSheet2018v0.pdf>_` for the values.
"""

MAXAR_E0 = {
    Platform.GE01: {
        obn.PAN: 1610.73,
        obn.BLUE: 1993.18,
        obn.GREEN: 1828.83,
        obn.RED: 1491.49,
        obn.NIR: 1022.58,
        obn.NARROW_NIR: 1022.58,
    },
    Platform.WV02: {
        obn.PAN: 1571.36,
        obn.CA: 1773.81,
        obn.BLUE: 2007.27,
        obn.GREEN: 1829.62,
        obn.YELLOW: 1701.85,
        obn.RED: 1538.85,
        obn.VRE_1: 1346.09,
        obn.VRE_2: 1346.09,
        obn.VRE_3: 1346.09,
        obn.NIR: 1053.21,
        obn.NARROW_NIR: 1053.21,
        obn.WV: 856.599,
    },
    Platform.WV03: {
        obn.PAN: 1574.41,
        obn.CA: 1757.89,
        obn.BLUE: 2004.61,
        obn.GREEN: 1830.18,
        obn.YELLOW: 1712.07,
        obn.RED: 1535.33,
        obn.VRE_1: 1348.08,
        obn.VRE_2: 1348.08,
        obn.VRE_3: 1348.08,
        obn.NIR: 1055.94,
        obn.NARROW_NIR: 1055.94,
        obn.WV: 858.77,
    },
    Platform.WV04: {
        obn.PAN: 1608.01,
        obn.BLUE: 2009.45,
        obn.GREEN: 1831.88,
        obn.RED: 1492.12,
        obn.NIR: 937.8,
        obn.NARROW_NIR: 937.8,
    },
    Platform.QB: {
        obn.PAN: 1370.92,
        obn.BLUE: 1949.59,
        obn.GREEN: 1823.64,
        obn.RED: 1553.78,
        obn.NIR: 1102.85,
        obn.NARROW_NIR: 1102.85,
    },
    Platform.WV01: {
        obn.PAN: 1478.62,
    },
}
"""
Esun is the band-averaged Solar exoatmospheric irradiance @1AU (see Slide 7&8). DG calibration team uses the Thuillier 2003 solar curve for their calculations.
See `here <https://apollomapping.com/image_downloads/Maxar_AbsRadCalDataSheet2018v0.pdf>_` for the values.
"""


@unique
class MaxarProductType(ListEnum):
    """
    Maxar product types.

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 26)
    """

    Basic = "System Ready"
    """
    Basic Imagery, also known as System-Ready data.
    Corresponds to a Level 1B.

    Not available in EOReader.
    """

    Standard = "View Ready"
    """
    Standard Imagery, also known as View-Ready data (previously Ortho-Ready Standard).
    Corresponds to a Level 2A (Standard2A or ORStandard2A)
    """

    Ortho = "Map Ready"
    """
    Orthorectified Standard Imagery, also known as Map-Ready data (previously Standard Imagery).
    Corresponds to a Level 3

    NMAS mapping scale of the Orthorectified Product:

    - Level 3A: “1:50,000”
    - Level 3D: “1:12,000”
    - Level 3E: “1:10,000”
    - Level 3F: “1:5,000”
    - Level 3G: “1:4,800”
    - Level 3X: “Custom”
    """

    DEM = "DEM"
    """
    DEM product type.

    Not available in EOReader.
    """

    Stereo = "Stereo"
    """
    Stereo product type.

    Not available in EOReader.
    """


@unique
class MaxarBandId(ListEnum):
    """
    Maxar products band ID

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 24)
    """

    P = "Panchromatic"
    """
    Panchromatic
    """

    Multi = "Multi Spectral"
    """
    All VNIR Multi-spectral bands (4 for QB02,GE01 and 8 for WV02, WV03)
    """

    N = "NIR"
    """
    Near-InfraRed
    """

    R = "RED"
    """
    Red
    """

    G = "GREEN"
    """
    Green
    """

    B = "BLUE"
    """
    Blue
    """

    RGB = "RGB"
    """
    Red + Green + Blue
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    NRG = "NRG"
    """
    Near-IR + Red + Green
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    BGRN = "BGRN Pan-Sharpened"
    """
    Blue + Green + Red + Near-IR
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    # Only for WorldView-2 and WorldView-3
    N2 = "NIR2"
    """
    NIR2
    """

    RE = "Red-Edge"
    """
    NIR2
    """

    Y = "Yellow"
    """
    Yellow
    """

    C = "Coastal"
    """
    Coastal
    """

    MS1 = "Multi Spectral 1"
    """
    First 4 bands (N,R,G,B)
    """

    MS2 = "Multi Spectral 2"
    """
    Second 4 bands (N2,RE,Y,C)
    """


@unique
class MaxarSatId(ListEnum):
    """
    Maxar products satellite IDs

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 29)
    """

    QB02 = "Quickbird-2"
    """
    Quickbird-2
    """

    GE01 = "GeoEye-1"
    """
    GeoEye-1
    """

    WV01 = "WorldView-1"
    """
    WorldView-1
    """

    WV02 = "WorldView-2"
    """
    WorldView-2
    """

    WV03 = "WorldView-3"
    """
    WorldView-3
    """

    WV04 = "WorldView-4"
    """
    WorldView-4
    """


class MaxarProduct(VhrProduct):
    """
    Super Class of Maxar products.
    See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
    for more information.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False
        self._proj_prod_type = [MaxarProductType.Standard]

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _get_platform(self) -> Platform:
        """ Getter of the platform """
        # Maxar products are all similar, we must check into the metadata to know the sensor
        root, _ = self.read_mtd()
        sat_id = root.findtext(".//IMAGE/SATID")
        if not sat_id:
            raise InvalidProductError("Cannot find SATID in the metadata file")
        sat_id = getattr(MaxarSatId, sat_id).name
        return getattr(Platform, sat_id)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Band combination
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//IMD/BANDID")
        if not band_combi:
            raise InvalidProductError("Cannot find from BANDID in the metadata file")
        self.band_combi = getattr(MaxarBandId, band_combi)

        # Maxar products are all similar, we must check into the metadata to know the sensor
        sat_id = root.findtext(".//IMAGE/SATID")
        if not sat_id:
            raise InvalidProductError("Cannot find SATID in the metadata file")

        # Post init done by the super class
        super()._post_init(**kwargs)

    @abstractmethod
    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """

        # Band combination
        root, _ = self.read_mtd()
        resol = root.findtext(".//MAP_PROJECTED_PRODUCT/PRODUCTGSD")
        if not resol:
            raise InvalidProductError(
                "Cannot find PRODUCTGSD type in the metadata file"
            )
        return float(resol)

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()
        prod_type = root.findtext(".//IMD/PRODUCTTYPE")
        if not prod_type:
            raise InvalidProductError(
                "Cannot find the PRODUCTTYPE in the metadata file"
            )
        self.product_type = getattr(MaxarProductType, prod_type)
        if self.product_type not in (MaxarProductType.Ortho, MaxarProductType.Standard):
            raise NotImplementedError(
                f"For now, "
                f"only {MaxarProductType.Ortho.value, MaxarProductType.Standard.value} "
                f"product types are supported for Maxar products."
            )

        # Manage bands of the product
        if self.band_combi in [
            MaxarBandId.P,
            MaxarBandId.N,
            MaxarBandId.R,
            MaxarBandId.G,
            MaxarBandId.B,
            MaxarBandId.N2,
            MaxarBandId.RE,
            MaxarBandId.Y,
            MaxarBandId.C,
        ]:
            self.band_names.map_bands({obn.PAN: 1})
        elif self.band_combi == MaxarBandId.RGB:
            self.band_names.map_bands({obn.RED: 1, obn.GREEN: 2, obn.BLUE: 3})
        elif self.band_combi == MaxarBandId.NRG:
            self.band_names.map_bands(
                {obn.NIR: 1, obn.NARROW_NIR: 1, obn.RED: 2, obn.GREEN: 3}
            )
        elif self.band_combi == MaxarBandId.BGRN:
            self.band_names.map_bands(
                {obn.BLUE: 1, obn.GREEN: 2, obn.RED: 3, obn.NIR: 4, obn.NARROW_NIR: 4}
            )
        elif self.band_combi == MaxarBandId.MS1:
            self.band_names.map_bands(
                {obn.NIR: 1, obn.NARROW_NIR: 1, obn.RED: 2, obn.GREEN: 3, obn.BLUE: 4}
            )
        elif self.band_combi == MaxarBandId.MS2:
            self.band_names.map_bands({obn.WV: 1, obn.RE: 2, obn.YELLOW: 3, obn.CA: 4})
        elif self.band_combi == MaxarBandId.Multi:
            if self.sat_id in (MaxarSatId.WV02.name, MaxarSatId.WV03.name):
                self.band_names.map_bands(
                    {
                        obn.NIR: 1,
                        obn.NARROW_NIR: 1,
                        obn.RED: 2,
                        obn.GREEN: 3,
                        obn.BLUE: 4,
                        obn.WV: 5,
                        obn.VRE_1: 6,
                        obn.VRE_2: 6,
                        obn.VRE_3: 6,
                        obn.YELLOW: 7,
                        obn.CA: 8,
                    }
                )
            else:
                self.band_names.map_bands(
                    {
                        obn.NIR: 1,
                        obn.NARROW_NIR: 1,
                        obn.RED: 2,
                        obn.GREEN: 3,
                        obn.BLUE: 4,
                    }
                )
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        map_proj_name = root.findtext(".//MAPPROJNAME")
        if not map_proj_name:
            raise InvalidProductError("Cannot find MAPPROJNAME in the metadata file")
        if map_proj_name == "Geographic (Lat/Long)":
            crs = riocrs.CRS.from_string("EPSG:4326")
        elif map_proj_name == "UTM":
            map_hemi = root.findtext(".//MAPHEMI")
            map_zone = root.findtext(".//MAPZONE")
            if not map_hemi or not map_zone:
                raise InvalidProductError(
                    "Cannot find MAPHEMI or MAPZONE type in the metadata file"
                )
            crs = riocrs.CRS.from_string(
                f"EPSG:32{6 if map_hemi == 'N' else 7}{map_zone}"
            )
        else:
            raise NotImplementedError(
                "Only Geographic or UTM map projections are supported yet"
            )

        return crs

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
        # Get Raw CRS
        raw_crs = self._get_raw_crs()

        # Get CRS
        if raw_crs.is_geographic:
            # Open metadata
            root, _ = self.read_mtd()

            # Get the origin lon lat
            lon = float(root.findtext(".//ORIGINX"))
            lat = float(root.findtext(".//ORIGINY"))

            # Compute UTM crs from center long/lat
            utm = vectors.corresponding_utm_projection(lon, lat)
            utm = riocrs.CRS.from_string(utm)
        else:
            utm = raw_crs

        return utm

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format  :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
            datetime_str = root.findtext(".//EARLIESTACQTIME")
            if not datetime_str:
                datetime_str = root.findtext(".//FIRSTLINETIME")
                if not datetime_str:
                    raise InvalidProductError(
                        "Cannot find EARLIESTACQTIME or FIRSTLINETIME in the metadata file."
                    )

            # Convert to datetime
            datetime_str = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")

            if not as_datetime:
                datetime_str = datetime_str.strftime(DATETIME_FMT)

        else:
            datetime_str = self.datetime
            if not as_datetime:
                datetime_str = datetime_str.strftime(DATETIME_FMT)

        return datetime_str

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        return files.get_filename(self._get_tile_path())

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
            elev_angle = float(root.findtext(".//MEANSUNEL"))
            azimuth_angle = float(root.findtext(".//MEANSUNAZ"))
        except TypeError:
            raise InvalidProductError("Azimuth or Zenith angles not found in metadata!")

        # From elevation to zenith
        zenith_angle = 90.0 - elev_angle

        return azimuth_angle, zenith_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = ".XML"
        mtd_archived = r"\.XML"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

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
            band_arr (xr.DataArray):
            path (Union[Path, CloudPath]):
            band (BandNames):
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
        if bands:
            LOGGER.warning("Maxar products do not provide any cloud file")

        return {}

    def _get_tile_path(self) -> Union[CloudPath, Path]:
        """
        Get the DIMAP filepath

        Returns:
            Union[CloudPath, Path]: DIMAP filepath
        """
        return self._get_path(extension="TIL")

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        See
        `Absolute Radiometric Calibration: 2016v0 <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/209/ABSRADCAL_FLEET_2016v0_Rel20170606.pdf>`_
        and
        `Improvements in Calibration, and Validation of the Absolute Radiometric Response of MAXAR Earth-Observing Sensors
        <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/209/ABSRADCAL_FLEET_2016v0_Rel20170606.pdf>`_
        (3.2.2) for more information.

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        band_mtd_str = f"BAND_{MAXAR_BAND_MTD[band]}"

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            band_mtd = root.find(f".//{band_mtd_str}")
            abs_factor = float(band_mtd.findtext(".//ABSCALFACTOR"))
            effective_bandwidth = float(band_mtd.findtext(".//EFFECTIVEBANDWIDTH"))
        except TypeError:
            raise InvalidProductError(
                "ABSCALFACTOR or EFFECTIVEBANDWIDTH not found in metadata!"
            )

        gain, offset = MAXAR_GAIN_OFFSET[self.platform][band]

        coeff = gain * (abs_factor / effective_bandwidth) + offset

        LOGGER.debug(f"DN to rad coeff = {coeff}")

        toa_rad = coeff * dn_arr.data

        return dn_arr.copy(data=toa_rad)

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        See
        `Absolute Radiometric Calibration: 2016v0 <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/209/ABSRADCAL_FLEET_2016v0_Rel20170606.pdf>`_
        and
        `Improvements in Calibration, and Validation of the Absolute Radiometric Response of MAXAR Earth-Observing Sensors
        <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/209/ABSRADCAL_FLEET_2016v0_Rel20170606.pdf>`_
        (3.2.2) for more information.

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        _, sun_zenith_angle = self.get_mean_sun_angles()
        toa_refl_coeff = (
            np.pi
            * self._sun_earth_distance_variation() ** 2
            / (MAXAR_E0[self.platform][band] * np.cos(np.deg2rad(sun_zenith_angle)))
        )

        LOGGER.debug(f"rad to refl coeff = {toa_refl_coeff}")

        return rad_arr.copy(data=toa_refl_coeff * rad_arr)
