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
Maxar super class.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
for more information.
"""
import logging
from abc import abstractmethod
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import rasterio
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import crs as riocrs
from sertit import files, rasters, rasters_rio, vectors
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

from eoreader import cache, cached_property
from eoreader.bands import BandNames
from eoreader.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.reader import Platform
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


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

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        self.ortho_path = None
        """
        Orthorectified path.
        Can be set to use manually orthorectified or pansharpened data, especially useful for VHR data on steep terrain.
        """

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp)

    def _pre_init(self) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False

        # Post init done by the super class
        super()._pre_init()

    def _get_platform(self) -> Platform:
        """ Getter of the platform """
        # Maxar products are all similar, we must check into the metadata to know the sensor
        root, _ = self.read_mtd()
        sat_id = root.findtext(".//IMAGE/SATID")
        if not sat_id:
            raise InvalidProductError("Cannot find SATID in the metadata file")
        sat_id = getattr(MaxarSatId, sat_id).name
        return getattr(Platform, sat_id)

    def _post_init(self) -> None:
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
        super()._post_init()

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
                        obn.WV: 5,
                        obn.RE: 6,
                        obn.YELLOW: 7,
                        obn.CA: 8,
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

    @cached_property
    def crs(self) -> riocrs.CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.crs
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

    @cached_property
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.footprint
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((707025.261 9688613.833, 707043.276 9...
            [1 rows x 3 columns]

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # Get footprint
        # TODO: Optimize that
        return rasters.get_footprint(self.get_default_band_path()).to_crs(self.crs)

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
                raise InvalidProductError(
                    "Cannot find EARLIESTACQTIME in the metadata file."
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
        return files.get_filename(self._get_til_path())

    def _get_ortho_path(self) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """

        if self.product_type == MaxarProductType.Standard:
            ortho_name = f"{self.condensed_name}_ortho.tif"
            ortho_path = self._get_band_folder().joinpath(ortho_name)
            if not ortho_path.is_file():
                ortho_path = self._get_band_folder(writable=True).joinpath(ortho_name)
                LOGGER.info(
                    f"Manually orthorectified stack not given by the user. "
                    f"Reprojecting data here: {ortho_path} "
                    "(May be inaccurate on steep terrain, depending on the DEM resolution.)"
                )

                # Reproject and write on disk data
                with rasterio.open(str(self._get_til_path())) as src:
                    out_arr, meta = self._reproject(src.read(), src.meta, src.rpcs)
                    rasters_rio.write(out_arr, meta, ortho_path)

        else:
            ortho_path = self._get_til_path()

        return ortho_path

    def _manage_invalid_pixels(
        self, band_arr: XDS_TYPE, band: obn, **kwargs
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See
        `here <https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf>`_
        (unusable data mask) for more information.

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            kwargs: Other arguments used to load bands

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Do nothing
        return band_arr

    def _manage_nodata(self, band_arr: XDS_TYPE, band: obn, **kwargs) -> XDS_TYPE:
        """
        Manage only nodata pixels

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            kwargs: Other arguments used to load bands

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Do nothing
        return band_arr

    def _get_condensed_name(self) -> str:
        """
        Get PlanetScope products condensed name ({date}_PLD_{product_type}_{band_combi}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.product_type.name}_{self.band_combi.name}"

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
        mtd_archived = "\.XML"

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
        if bands:
            LOGGER.warning("Maxar products do not provide any cloud file")

        return {}

    def _get_til_path(self) -> Union[CloudPath, Path]:
        """
        Get the DIMAP filepath

        Returns:
            Union[CloudPath, Path]: DIMAP filepath
        """
        return self._get_path(extension="TIL")
