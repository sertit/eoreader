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
Sentinel-3 products

.. WARNING:
    Not georeferenced NetCDF files are badly opened by GDAL and therefore by rasterio !
    -> use xr.open_dataset that manages that correctly
"""
import io
import logging
import re
import warnings
import zipfile
from abc import abstractmethod
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from lxml.builder import E
from rasterio import crs as riocrs
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning
from sertit import files, vectors
from sertit.misc import ListEnum
from shapely.geometry import Polygon, box

from eoreader import cache, utils
from eoreader.bands import BandNames
from eoreader.bands import SpectralBandNames as spb
from eoreader.exceptions import InvalidProductError
from eoreader.products import OpticalProduct
from eoreader.reader import Constellation
from eoreader.utils import DATETIME_FMT, EOREADER_NAME, simplify

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
        **kwargs,
    ) -> None:
        self._data_type = None
        self._gcps = None

        # Radiance bands
        self._radiance_file = None
        self._radiance_subds = None

        # Geocoding
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
        self._saa_name = None  # Azimuth angle
        self._sza_name = None  # Zenith angle

        # Rad 2 Refl
        self._misc_file = None
        self._solar_flux_name = None

        self._set_preprocess_members()

        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.needs_extraction = False
        self._use_filename = True
        self.is_ortho = False

        # Post init done by the super class
        super()._pre_init(**kwargs)

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        if self.constellation == Constellation.S3_OLCI:
            self.instrument = S3Instrument.OLCI
        elif self.constellation == Constellation.S3_SLSTR:
            self.instrument = S3Instrument.SLSTR
        else:
            raise InvalidProductError(
                f"Only OLCI and SLSTR are valid Sentinel-3 instruments : {self.name}"
            )

    def _get_constellation(self) -> Constellation:
        """ Getter of the constellation """
        if "OL" in self.name:
            return Constellation.S3_OLCI
        elif "SL" in self.name:
            return Constellation.S3_SLSTR
        else:
            raise InvalidProductError(
                f"Only OLCI and SLSTR are valid Sentinel-3 instruments : {self.name}"
            )

    @abstractmethod
    def _set_preprocess_members(self):
        """ Set pre-process members """
        raise NotImplementedError

    @cache
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
            gpd.GeoDataFrame: Extent in UTM
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

        return extent

    @cache
    @simplify
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

    @cache
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
        mid_x = int(lat.rio.width / 2)
        mid_y = int(lat.rio.height / 2)
        mid_lat = lat[0, mid_y, mid_x].data
        mid_lon = lon[0, mid_y, mid_x].data

        # Deduce UTM proj from the central lon/lat
        utm = vectors.corresponding_utm_projection(mid_lon, mid_lat)

        return riocrs.CRS.from_string(utm)

    def _replace(
        self,
        ppm_to_replace: str,
        band: Union[str, BandNames] = None,
        suffix: str = None,
        view: str = None,
    ) -> str:
        """
        Replace preprocessed members strings

        Args:
            ppm_to_replace (str): Preprocessed member to replace
            band (Union[str, BandNames]): Replace the band
            suffix (str): Replace the suffix
            view (str): Replace the view

        Returns:
            Completed preprocessed member
        """
        substitutions = {
            "{band}": self.bands[band].id if isinstance(band, BandNames) else band,
            "{suffix}": suffix,
            "{view}": view,
        }
        for search, replacement in substitutions.items():
            if replacement is not None:
                ppm_to_replace = ppm_to_replace.replace(search, replacement)

        return ppm_to_replace

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//start_time")
            if not acq_date:
                raise InvalidProductError("start_time not found in metadata!")

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        name = files.get_filename(root.findtext(".//product_name"))
        if not name:
            raise InvalidProductError("product_name not found in metadata!")

        return name

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. WARNING:: If not existing, this function will orthorectify your bands !

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            Executing processing graph
            ...11%...21%...31%...42%...52%...62%...73%...83%... done.
            {
                <SpectralBandNames.GREEN: 'GREEN'>: '20191115T233722_S3_SLSTR_RBT/S1_reflectance.tif',
                <SpectralBandNames.RED: 'RED'>: '20191115T233722_S3_SLSTR_RBT/S2_reflectance.tif',
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Useless here
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(
                band, resolution=resolution, **kwargs
            )
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                # Pre-process the wanted band (does nothing if existing)
                band_paths[band] = self._preprocess(
                    band,
                    resolution=resolution,
                    **kwargs,
                )

        return band_paths

    # pylint: disable=W0613
    def _read_band(
        self,
        path: Union[CloudPath, Path],
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
        Returns:
            xr.DataArray: Band xarray

        """
        band = utils.read(
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
            **kwargs,
        )

        # Read band
        return band.astype(np.float32) * band.scale_factor

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
        # Do nothing, managed elsewhere
        return band_arr

    @abstractmethod
    def _manage_invalid_pixels(
        self, band_arr: xr.DataArray, band: BandNames, **kwargs
    ) -> xr.DataArray:
        """
        Manage invalid pixels (Nodata, saturated, defective...)

        Args:
            band_arr (xr.DataArray): Band array
            band (BandNames): Band name as an SpectralBandNames
            kwargs: Other arguments used to load bands

        Returns:
            xr.DataArray: Cleaned band array
        """
        raise NotImplementedError

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
        # Get nodata mask
        no_data = np.where(np.isnan(band_arr.data), self._mask_true, self._mask_false)

        return self._set_nodata_mask(band_arr, no_data)

    def _load_bands(
        self,
        bands: list,
        resolution: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands (list): List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
            kwargs: Other arguments used to load bands
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
        band_paths = self.get_band_paths(bands, resolution=resolution, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, resolution=resolution, size=size, **kwargs
        )

        return band_arrays

    @abstractmethod
    def _preprocess(
        self,
        band: Union[BandNames, str],
        resolution: float = None,
        to_reflectance: bool = True,
        subdataset: str = None,
        **kwargs,
    ) -> Union[CloudPath, Path]:
        """
        Pre-process S3 bands:
        - Geocode
        - Convert radiance to reflectance

        Args:
            band (Union[BandNames, str]): Band to preprocess (quality flags or others are accepted)
            resolution (float): Resolution
            to_reflectance (bool): Convert band to reflectance
            subdataset (str): Subdataset
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing {band: path}
        """
        raise NotImplementedError

    def _get_condensed_name(self) -> str:
        """
        Get S3 products condensed name ({date}_S3_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self._data_type.name}"

    @cache
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
        # Here in read_mtd we don't know which type of product we have (before we have the correct constellation)
        # Manage archives
        if self.is_archived:
            if isinstance(self.path, CloudPath):
                # Download the whole product (sadly)
                on_disk = io.BytesIO(self.path.read_bytes())
            else:
                on_disk = self.path

            # Cannot read zipped+netcdf files -> we are forced to dezip them
            with zipfile.ZipFile(on_disk, "r") as zip_ds:
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*{self._tie_geo_file}")
                with io.BytesIO(
                    zip_ds.read(list(filter(regex.match, filenames))[0])
                ) as bf:
                    netcdf_ds = xr.open_dataset(bf)
        else:
            geom_file = self.path.joinpath(self._tie_geo_file)

            if not geom_file.is_file():
                raise InvalidProductError(
                    "This Sentinel-3 product has no geometry file !"
                )

            # Open DS
            if isinstance(geom_file, CloudPath):
                with io.BytesIO(geom_file.read_bytes()) as bf:
                    netcdf_ds = xr.open_dataset(bf)
            else:
                netcdf_ds = xr.open_dataset(geom_file)

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

        # Create XML attributes
        global_attr = []
        for attr in global_attr_names:
            if hasattr(netcdf_ds, attr):
                global_attr.append(E(attr, str(getattr(netcdf_ds, attr))))

        mtd = E.s3_global_attributes(*global_attr)
        mtd_el = etree.fromstring(
            etree.tostring(
                mtd, pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
        )

        # Close dataset
        netcdf_ds.close()

        return mtd_el, {}

    def _read_nc(
        self, filename: Union[str, BandNames], subdataset: str = None, dtype=np.float32
    ) -> xr.DataArray:
        """
        Read NetCDF file (as float32) and rescaled them to their true values

        NetCDF files are supposed to be at the root of this product.

        Returns a string as it is meant to be opened by rasterio or directly a xr.DataArray (if archived)

        Caches the file if needed (rasterio does not seem to be able to open a netcdf stored in the cloud).

        Args:
            filename (Union[str, BandNames]): Filename or band
            subdataset (str): NetCDF subdataset if needed

        Returns:
            xr.DataArray: NetCDF file as a xr.DataArray
        """
        bytes_file = None
        nc_path = None

        # Try to convert to spb if existing
        try:
            filename = spb.convert_from(filename)[0]
        except TypeError:
            pass

        # Get raw band path
        if self.is_archived:
            if isinstance(self.path, CloudPath):
                # Download the whole product (sadly)
                on_disk = io.BytesIO(self.path.read_bytes())
            else:
                on_disk = self.path

            # Cannot read zipped+netcdf files -> we are forced to dezip them
            with zipfile.ZipFile(on_disk, "r") as zip_ds:
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*{filename}")
                bytes_file = zip_ds.read(list(filter(regex.match, filenames))[0])
        else:
            try:
                nc_path = next(self.path.glob(f"*{filename}*"))
            except StopIteration:
                raise FileNotFoundError(f"Non existing file {filename} in {self.path}")

            if isinstance(nc_path, CloudPath):
                # Cloud paths: instead of downloading them, read them as bytes and directly open the xr.Dataset
                bytes_file = nc_path.read_bytes()
            else:
                # Classic paths
                nc_path = str(nc_path)

        # Open the netcdf file as a dataset (from bytes)
        # mask_and_scale=True => offset and scale are automatically applied !
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            if bytes_file:
                with io.BytesIO(bytes_file) as bf:
                    # We need to load the dataset as we will do some operations and bf will close
                    nc = xr.open_dataset(bf, mask_and_scale=True)
                    if subdataset:
                        nc = getattr(nc, subdataset)

                    nc.load()
            else:
                # No need to load here
                nc = xr.open_dataset(nc_path, mask_and_scale=True, engine="h5netcdf")

                if subdataset:
                    nc = nc[subdataset]

        # WARNING: rioxarray doesn't like bytesIO -> open with xarray.h5netcdf engine
        # BUT the xr.DataArray dimensions wont be correctly formatted !
        # Align the NetCDF behaviour on rasterio's

        # Read as float32 (by default) or with given type
        nc = nc.astype(dtype)

        # Add the band dimension
        if "band" not in nc.dims:
            nc = nc.expand_dims(dim="band", axis=0)
        else:
            # band dim exists and is set last by default, invert to match rasterio order
            dims = np.array(nc.dims)
            nc = nc.swap_dims({dims[0]: "band", "band": dims[0]})

        # Set spatial dims: x = cols, y = rows, rasterio order = count, rows, cols
        dims = np.array(nc.dims)
        nc = nc.rename({dims[-1]: "x", dims[-2]: "y"})

        # http://xarray.pydata.org/en/latest/generated/xarray.open_dataset.html
        # open_dataset opens the file with read-only access.
        # When you modify values of a Dataset, even one linked to files on disk,
        # only the in-memory copy you are manipulating in xarray is modified:
        # the original file on disk is never touched.
        # -> return a copy() as we will modify it !
        return nc.copy()

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        raise NotImplementedError

    @abstractmethod
    def _set_product_type(self) -> None:
        """
        Set product type
        """
        raise NotImplementedError

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing (some providers are providing one quicklook, such as creodias)

        Returns:
            str: Quicklook path
        """
        try:
            if self.is_archived:
                quicklook_path = files.get_archived_rio_path(
                    self.path, file_regex=r".*.jpg"
                )
            else:
                quicklook_path = str(next(self.path.glob("**/*.jpg")))
        except (FileNotFoundError, StopIteration):
            quicklook_path = None

        return quicklook_path
