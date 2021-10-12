# -*- coding: utf-8 -*-
# Copyright 2021, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" Sentinel-3 products """
import logging
import os
from abc import abstractmethod
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import netCDF4
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from lxml.builder import E
from rasterio import crs as riocrs
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from sertit import rasters_rio, vectors
from sertit.misc import ListEnum
from sertit.rasters import MAX_CORES, XDS_TYPE
from sertit.vectors import WGS84
from shapely.geometry import Polygon, box

from eoreader import utils
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.reader import Platform
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S3ProductType(ListEnum):
    """Sentinel-3 products types (not exhaustive, only L1)"""

    OLCI_EFR = "OL_1_EFR___"
    """OLCI EFR Product Type"""

    SLSTR_RBT = "SL_1_RBT___"
    """SLSTR RBT Product Type"""


@unique
class S3Instrument(ListEnum):
    """Sentinel-3 products types"""

    OLCI = "S3_OLCI"
    """OLCI Instrument"""

    SLSTR = "S3_SLSTR"
    """SLSTR Instrument"""


@unique
class S3DataType(ListEnum):
    """Sentinel-3 data types -> only considering useful ones"""

    EFR = "EFR___"
    """EFR Data Type, for OLCI instrument"""

    RBT = "RBT__"
    """RBT Data Type, for SLSTR instrument"""


class S3Product(OpticalProduct):
    """
    Super-Class of Sentinel-3 Products
    """

    def __init__(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        remove_tmp: bool = False,
    ) -> None:
        self._data_type = None

        # Geocoding
        self._gcps = []
        self._geo_file = None
        self._lat_nc_name = None
        self._lon_nc_name = None
        self._alt_nc_name = None

        # Tie geocoding
        self._tie_geo_file = None
        self._tie_lat_nc_name = None
        self._tie_lon_nc_name = None

        # Mean Sun angles
        self._geom_file = None
        self._sza_name = None
        self._sze_name = None

        # Rad 2 Refl
        self._misc_file = None
        self._solar_flux_name = None

        self._set_preprocess_members()

        super().__init__(
            product_path, archive_path, output_path, remove_tmp
        )  # Order is important here

    @abstractmethod
    def _set_preprocess_members(self):
        """ Set pre-process members """
        raise NotImplementedError("This method should be implemented by a child class")

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Post init done by the super class
        super()._post_init()

    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile, managing the case with not orthorectified bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                                        geometry
            0  POLYGON ((1488846.028 6121896.451, 1488846.028...

        Returns:
            gpd.GeoDataFrame: Footprint in UTM
        """
        # --- EXTENT IN UTM ---
        extent = gpd.GeoDataFrame(
            geometry=[box(*self.footprint().geometry.total_bounds)],
            crs=self.crs(),
        )

        # --- EXTENT IN WGS84 ---
        # # Open lon/lat/alt files
        # lat = rioxarray.open_rasterio(self._get_nc_file_str(self._tie_geo_file, self._tie_lat_nc_name))
        # lon = rioxarray.open_rasterio(self._get_nc_file_str(self._tie_geo_file, self._tie_lon_nc_name))
        #
        # assert lat.data.shape == lon.data.shape
        #
        # # Get min/max of lat/lon
        # def _get_min_max(xds: xr.DataArray) -> tuple:
        #     corners = [xds.data[0, 0, 0], xds.data[0, 0, -1], xds.data[0, -1, 0], xds.data[0, -1, -1]]
        #     return np.min(corners) * xds.scale_factor, np.max(corners) * xds.scale_factor
        #
        # lat_min, lat_max = _get_min_max(lat)
        # lon_min, lon_max = _get_min_max(lon)
        #
        # # Create wgs84 extent (left, bottom, right, top)
        # extent_wgs84 = gpd.GeoDataFrame(
        #     geometry=[
        #         vectors.from_bounds_to_polygon(lon_min, lat_min, lon_max, lat_max)
        #     ],
        #     crs=vectors.WGS84,
        # )
        # # TODO: set CRS here also (in order not to reopen lat/lon) ?

        return extent

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get UTM footprint in UTM of the products (without nodata, *in french == emprise utile*)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((199980.000 4500000.000, 199980.000 4...

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """

        # Open lon/lat/alt files
        lat = self._read_nc(self._tie_geo_file, self._tie_lat_nc_name)
        lon = self._read_nc(self._tie_geo_file, self._tie_lon_nc_name)

        assert lat.data.shape == lon.data.shape

        # Get WGS84 vertices
        vertex = [
            (lonv, latv) for lonv, latv in zip(lon.data[0, 0, :], lat.data[0, 0, :])
        ]
        vertex += [
            (lonv, latv) for lonv, latv in zip(lon.data[0, :, -1], lat.data[0, :, -1])
        ]
        vertex += [
            (lonv, latv)
            for lonv, latv in zip(lon.data[0, -1, ::-1], lat.data[0, -1, ::-1])
        ]
        vertex += [
            (lonv, latv)
            for lonv, latv in zip(lon.data[0, ::-1, 0], lat.data[0, ::-1, 0])
        ]

        # Create wgs84 extent (left, bottom, right, top)
        extent_wgs84 = gpd.GeoDataFrame(geometry=[Polygon(vertex)], crs=vectors.WGS84)
        # TODO: set CRS here also (in order not to reopen lat/lon) ?

        return extent_wgs84.to_crs(self.crs())

    def crs(self) -> riocrs.CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.crs()
            CRS.from_epsg(32630)

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open lon/lat/alt files
        lat = self._read_nc(self._tie_geo_file, self._tie_lat_nc_name)
        lon = self._read_nc(self._tie_geo_file, self._tie_lon_nc_name)

        assert lat.data.shape == lon.data.shape

        # Get lon/lat in the middle of the band
        mid_x = int(lat.x.size / 2)
        mid_y = int(lat.y.size / 2)
        mid_lat = lat[0, mid_y, mid_x].data
        mid_lon = lon[0, mid_y, mid_x].data

        # Deduce UTM proj from the central lon/lat
        utm = vectors.corresponding_utm_projection(mid_lat, mid_lon)

        return riocrs.CRS.from_string(utm)

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 11, 15, 23, 37, 22)
            >>> prod.get_datetime(as_datetime=False)
            '20191115T233722'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        try:
            acq_date = root.findtext(".//start_time")
        except TypeError:
            raise InvalidProductError("start_time not found in metadata !")

        # Convert to datetime
        date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    @abstractmethod
    def _get_raw_band_path(self, band: Union[obn, str], subdataset: str = None) -> str:
        """
        Return the paths of raw band.

        Args:
            band (Union[obn, str]): Wanted raw bands
            subdataset (str): Subdataset

        Returns:
            str: Raw band path
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _get_preprocessed_band_path(
        self,
        band: Union[obn, str],
        resolution: Union[float, tuple, list] = None,
        writable=True,
    ) -> Union[CloudPath, Path]:
        """
        Create the pre-processed band path

        Args:
            band (band: Union[obn, str]): Wanted band (quality flags accepted)
            resolution (Union[float, tuple, list]): Resolution of the wanted UTM band
            writable (bool): Do we need to write the pre-processed band ?

        Returns:
            Union[CloudPath, Path]: Pre-processed band path
        """
        res_str = self._resolution_to_str(resolution)
        band_str = band.name if isinstance(band, obn) else band

        return self._get_band_folder(writable=True).joinpath(
            f"{self.condensed_name}_{band_str}_{res_str}.tif"
        )

    def _get_platform(self) -> Platform:
        """ Getter of the platform """
        # look in the MTD to be sure
        root, _ = self.read_mtd()
        name = root.findtext(".//product_name")

        if "OL" in name:
            # Instrument
            sat_id = S3Instrument.OLCI.value
        elif "SL" in name:
            # Instrument
            sat_id = S3Instrument.SLSTR.value
        else:
            raise InvalidProductError(
                f"Only OLCI and SLSTR are valid Sentinel-3 instruments : {self.name}"
            )

        return getattr(Platform, sat_id)

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: If not existing, this function will orthorectify your bands !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            Executing processing graph
            ...11%...21%...31%...42%...52%...62%...73%...83%... done.
            {
                <OpticalBandNames.GREEN: 'GREEN'>: '20191115T233722_S3_SLSTR_RBT\\S1_reflectance.tif',
                <OpticalBandNames.RED: 'RED'>: '20191115T233722_S3_SLSTR_RBT\\S2_reflectance.tif',
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(band, resolution=resolution)
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                # Pre-process the wanted band (does nothing if existing)
                band_paths[band] = self._preprocess(band, resolution=resolution)

        return band_paths

    # pylint: disable=W0613
    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            XDS_TYPE: Band xarray

        """
        band = utils.read(
            path, resolution=resolution, size=size, resampling=Resampling.bilinear
        )

        # Read band
        return band.astype(np.float32) * band.scale_factor

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    @abstractmethod
    def _manage_invalid_pixels(self, band_arr: XDS_TYPE, band: obn) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames

        Returns:
            XDS_TYPE: Cleaned band array
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _load_bands(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        if not isinstance(bands, list):
            bands = [bands]

        if resolution is None and size is not None:
            resolution = self._resolution_from_size(size)
        band_paths = self.get_band_paths(bands, resolution=resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays

    def _preprocess(
        self,
        band: Union[obn, str],
        resolution: float = None,
        to_reflectance: bool = True,
        subdataset: str = None,
    ) -> Union[CloudPath, Path]:
        """
        Pre-process S3 bands:
        - Geocode
        - Convert radiance to reflectance

        Args:
            band (Union[obn, str]): Band to preprocess (quality flags or others are accepted)
            resolution (float): Resolution
            to_reflectance (bool): Convert band to reflectance
            subdataset (str): Subdataset

        Returns:
            dict: Dictionary containing {band: path}
        """
        path = self._get_preprocessed_band_path(band, resolution=resolution)

        if not path.is_file():
            path = self._get_preprocessed_band_path(
                band, resolution=resolution, writable=True
            )

            # Get raw band
            # "\\sertit6\s6_dat1\_EXTRACTEO\DS3\CI\eoreader\optical\S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\S2_radiance_an.nc"
            raw_band_path = self._get_raw_band_path(band, subdataset)
            band_arr = utils.read(raw_band_path).astype(np.float32)
            band_arr *= band_arr.scale_factor

            # Convert radiance to reflectances if needed
            # Convert first pixel by pixel before reprojection !
            if to_reflectance:
                LOGGER.debug(
                    f"Converting {os.path.basename(raw_band_path)} to reflectance"
                )
                band_arr = self._rad_2_refl(band_arr, band)

            # Geocode
            LOGGER.debug(f"Geocoding {os.path.basename(raw_band_path)}")
            pp_arr = self._geocode(band_arr, resolution=resolution)

            # Write on disk
            utils.write(pp_arr, path)

        return path

    def _create_gcps(self):
        """
        Create the GCPs sequence
        """
        # Open lon/lat/alt files to populate the GCPs
        lat = self._read_nc(self._geo_file, self._lat_nc_name)
        lon = self._read_nc(self._geo_file, self._lon_nc_name)
        alt = self._read_nc(self._geo_file, self._alt_nc_name)

        assert lat.data.shape == lon.data.shape == alt.data.shape

        # Get the GCPs coordinates
        nof_gcp_x = np.linspace(0, lat.x.size - 1, dtype=int)
        nof_gcp_y = np.linspace(0, lat.y.size - 1, dtype=int)

        # Create the GCP sequence
        id = 0
        for x in nof_gcp_x:
            for y in nof_gcp_y:
                self._gcps.append(
                    GroundControlPoint(
                        row=y,
                        col=x,
                        x=lon.data[0, y, x],
                        y=lat.data[0, y, x],
                        z=alt.data[0, y, x],
                        id=id,
                    )
                )
                id += 1

    def _geocode(
        self, band_arr: xr.DataArray, resolution: float = None
    ) -> xr.DataArray:
        """
        Geocode Sentinel-3 bands

        Args:
            band_arr (xr.DataArray): Band array
            resolution (float): Resolution

        Returns:
            xr.DataArray: Geocoded DataArray
        """
        # Create GCPs if not existing
        if not self._gcps:
            self._create_gcps()

        # Assign a projection
        band_arr.rio.write_crs(WGS84, inplace=True)

        return band_arr.rio.reproject(
            dst_crs=self.crs(),
            resolution=resolution,
            gcps=self._gcps,
            nodata=self.nodata,
            num_threads=MAX_CORES,
            **{"SRC_METHOD": "GCP_TPS"},
        )

    def _rad_2_refl(self, band_arr: xr.DataArray, band: obn = None) -> xr.DataArray:
        """
        Convert radiance to reflectance

        Args:
            band_arr (xr.DataArray): Band array
            band (obn): Optical Band (for SLSTR only)

        Returns:
            dict: Dictionary containing {band: path}
        """
        rad_2_refl_path = self._get_band_folder() / "rad_2_refl.npy"

        if not rad_2_refl_path.is_file():
            rad_2_refl_path = self._get_band_folder(writable=True) / "rad_2_refl.npy"

            # Open SZA array (resampled to band_arr size)
            with rasterio.open(
                self._get_nc_path_str(self._geom_file, self._sze_name)
            ) as ds_sza:
                sza, _ = rasters_rio.read(
                    ds_sza,
                    size=(band_arr.rio.width, band_arr.rio.height),
                    resampling=Resampling.bilinear,
                    masked=False,
                )
                sza_scale = ds_sza.scales[0]
                sza_rad = sza.astype(np.float32) * sza_scale * np.pi / 180.0

            # Open solar flux (resampled to band_arr size)
            misc = self._misc_file.replace(
                "{}", self.band_names[band]
            )  # Only for SLSTR
            solar_flux_name = self._solar_flux_name.replace(
                "{}", self.band_names[band]
            )  # Only for SLSTR
            with rasterio.open(self._get_nc_path_str(misc, solar_flux_name)) as ds_e0:
                e0, _ = rasters_rio.read(
                    ds_e0,
                    size=(band_arr.rio.width, band_arr.rio.height),
                    resampling=Resampling.bilinear,
                    masked=False,
                )
                e0_scale = ds_e0.scales[0]
                e0_scaled = e0.astype(np.float32) * e0_scale
                # TODO: Manage null pixels

            # Compute rad_2_refl coeff
            rad_2_refl_coeff = (np.pi / (e0_scaled * np.cos(sza_rad))).astype(
                np.float32
            )

            # Write on disk
            np.save(rad_2_refl_path, rad_2_refl_coeff)

        else:
            # Open rad_2_refl_coeff (resampled to band_arr size)
            rad_2_refl_coeff = np.load(rad_2_refl_path)

        return band_arr * rad_2_refl_coeff

    def _get_condensed_name(self) -> str:
        """
        Get S3 products condensed name ({date}_S3_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self._data_type.name}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (78.55043955912154, 31.172127033319388)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Open sun azimuth and zenith files
        sun_az = self._read_nc(self._geom_file, self._sza_name)
        sun_ze = self._read_nc(self._geom_file, self._sze_name)

        # Sun azimuth for Sentinel-3 are in [-180, 180] and we want [0,360]
        return (sun_az.mean().data + 180.0, sun_ze.mean().data)

    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element level1Product at 0x1b845b7ab88>, '')

        Returns:
            (etree._Element, dict): Metadata XML root and its namespace
        """
        # Open first nc file as every file should have the global attributes
        # Here in read_mtd we don't know which type of product we have (before we have the correct platform)
        geom_file = self.path.joinpath(self._tie_geo_file)
        if not geom_file.is_file():
            raise InvalidProductError("This Sentinel-3 product has no geometry file !")

        # Open DS
        if isinstance(geom_file, CloudPath):
            netcdf_ds = netCDF4.Dataset(
                geom_file.download_to(self._get_band_folder(writable=True))
            )
        else:
            netcdf_ds = netCDF4.Dataset(geom_file)

        # Parsing global attributes
        global_attr_names = [
            "absolute_orbit_number",
            "comment",
            "contact",
            "creation_time",
            "history",
            "institution",
            "netCDF_version",
            "product_name",
            "references",
            "resolution",
            "source",
            "start_offset",
            "start_time",
            "stop_time",
            "title",
            # OLCI
            "ac_subsampling_factor",
            "al_subsampling_factor",
            # SLSTR
            "track_offset",
        ]

        global_attr = [
            E(attr, str(getattr(netcdf_ds, attr)))
            for attr in global_attr_names
            if hasattr(netcdf_ds, attr)
        ]

        mtd = E.s3_global_attributes(*global_attr)
        mtd_el = etree.fromstring(
            etree.tostring(
                mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
        )

        return mtd_el, {}

    def _get_nc_path_str(
        self, filename: Union[Path, CloudPath], subdataset: str = None
    ) -> str:
        """
        Get NetCDF file path.

        NetCDF paths are supposed to be at the root of this product.

        Returns a string as it is meant to be opened by rasterio.

        Caches the file if needed (rasterio does not seem to be able to open a netcdf stored in the cloud).

        Args:
            filename (Union[Path, CloudPath]): Filename
            subdataset (str): NetCDF subdataset if needed

        Returns:
            str: NetCDF file path as a string
        """
        if isinstance(self.path, CloudPath):
            path = self.path.joinpath(filename).download_to(
                self._get_band_folder(writable=True)
            )
        else:
            path = str(self.path.joinpath(filename))

        # Complete the path
        path = f"netcdf:{path}"

        if subdataset:
            path += f":{subdataset}"

        return path

    def _read_nc(
        self, filename: Union[Path, CloudPath], subdataset: str = None
    ) -> xr.DataArray:
        """
        Read NetCDF file (as float32) and rescaled them to their true values

        NetCDF files are supposed to be at the root of this product.

        Args:
            filename (Union[Path, CloudPath]): Filename
            subdataset (str): NetCDF subdataset if needed

        Returns:
            xr.DataArray: NetCDF file, rescaled
        """
        # Open with rioxarray directly as these files are not geocoded
        nc = rioxarray.open_rasterio(self._get_nc_path_str(filename, subdataset))
        return nc.astype(np.float32) * nc.scale_factor

    @abstractmethod
    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    @abstractmethod
    def _set_product_type(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError("This method should be implemented by a child class")
