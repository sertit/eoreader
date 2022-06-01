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
""" Utils: mostly getting directories relative to the project """
import logging
import os
import platform
import warnings
from functools import wraps
from pathlib import Path
from typing import Callable, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from cloudpathlib import AnyPath, CloudPath
from lxml import etree
from rasterio import errors
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning
from rasterio.rpc import RPC
from sertit import rasters

from eoreader.env_vars import USE_DASK
from eoreader.exceptions import InvalidProductError
from eoreader.keywords import _prune_keywords

EOREADER_NAME = "eoreader"
DATETIME_FMT = "%Y%m%dT%H%M%S"
LOGGER = logging.getLogger(EOREADER_NAME)


def get_src_dir() -> Union[CloudPath, Path]:
    """
    Get src directory.

    Returns:
        str: Root directory
    """
    return AnyPath(__file__).parent


def get_root_dir() -> Union[CloudPath, Path]:
    """
    Get root directory.

    Returns:
        str: Root directory
    """
    return get_src_dir().parent


def get_data_dir() -> Union[CloudPath, Path]:
    """
    Get data directory.

    Returns:
        str: Data directory
    """
    data_dir = get_src_dir().joinpath("data")
    if not data_dir.is_dir() or not list(data_dir.iterdir()):
        data_dir = None
        # Last resort try
        if platform.system() == "Linux":
            data_dirs = AnyPath("/usr", "local", "lib").glob("**/eoreader/data")
        else:
            data_dirs = AnyPath("/").glob("**/eoreader/data")

        # Look for non empty directories
        for ddir in data_dirs:
            if len(os.listdir(ddir)) > 0:
                data_dir = ddir
                break

        if not data_dir:
            raise FileNotFoundError("Impossible to find the data directory.")

    return data_dir


def get_split_name(name: str) -> list:
    """
    Get split name (with _). Removes empty indexes.

    Args:
        name (str): Name to split

    Returns:
        list: Split name
    """
    return [x for x in name.split("_") if x]


# flake8: noqa
def use_dask():
    """Use Dask or not"""
    # Check environment variable
    use_dask = os.getenv(USE_DASK, "0").lower() in ("1", "true")

    # Check installed libs
    if use_dask:
        try:
            import dask
            import distributed
        except ImportError:
            use_dask = False

    return use_dask


def read(
    path: Union[str, CloudPath, Path],
    resolution: Union[tuple, list, float] = None,
    size: Union[tuple, list] = None,
    resampling: Resampling = Resampling.nearest,
    masked: bool = True,
    indexes: Union[int, list] = None,
    **kwargs,
) -> xr.DataArray:
    """
    Overload of :code:`sertit.rasters.read()` managing  DASK in EOReader's way.

    .. code-block:: python

        >>> raster_path = "path/to/raster.tif"
        >>> xds1 = read(raster_path)
        >>> # or
        >>> with rasterio.open(raster_path) as dst:
        >>>    xds2 = read(dst)
        >>> xds1 == xds2
        True

    Args:
        path (Union[str, CloudPath, Path]): Path to the raster
        resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
        size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        resampling (Resampling): Resampling method
        masked (bool): Get a masked array
        indexes (Union[int, list]): Indexes to load. Load the whole array if None.
        **kwargs: Optional keyword arguments to pass into rioxarray.open_rasterio().
    Returns:
        xr.DataArray: Masked xarray corresponding to the raster data and its meta data

    """
    if use_dask():
        chunks = True
    else:
        chunks = None

    try:
        # Disable georef warnings here as the SAR/Sentinel-3 products are not georeferenced
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            return rasters.read(
                path,
                resolution=resolution,
                size=size,
                resampling=resampling,
                masked=masked,
                indexes=indexes,
                chunks=chunks,
                **_prune_keywords(**kwargs),
            )
    except errors.RasterioIOError as ex:
        if str(path).endswith("jp2") or str(path).endswith("tif"):
            raise InvalidProductError(f"Corrupted file: {path}") from ex
        else:
            raise


def write(xds: xr.DataArray, path: Union[str, CloudPath, Path], **kwargs) -> None:
    """
    Overload of :code:`sertit.rasters.write()` managing DASK in EOReader's way.

    .. code-block:: python

        >>> raster_path = "path/to/raster.tif"
        >>> raster_out = "path/to/out.tif"

        >>> # Read raster
        >>> xds = read(raster_path)

        >>> # Rewrite it
        >>> write(xds, raster_out)


    Args:
        xds (xr.DataArray): Path to the raster or a rasterio dataset or a xarray
        path (Union[str, CloudPath, Path]): Path where to save it (directories should be existing)
        **kwargs: Overloading metadata, ie :code:`nodata=255` or :code:`dtype=np.uint8`
    """
    if use_dask():
        from distributed import Lock, get_client

        lock = Lock("rio", client=get_client())
    else:
        lock = None

    # Reset the long name as a list to write it down
    previous_long_name = xds.attrs.get("long_name")
    if previous_long_name and xds.rio.count > 1:
        try:
            xds.attrs["long_name"] = xds.attrs.get(
                "long_name", xds.attrs.get("name", "")
            ).split(" ")
        except AttributeError:
            pass

    # Write
    rasters.write(xds, path=path, lock=lock, **_prune_keywords(**kwargs))

    # Set back the previous long name
    if previous_long_name and xds.rio.count > 1:
        xds.attrs["long_name"] = previous_long_name


def create_gcps(lon: xr.DataArray, lat: xr.DataArray, alt: xr.DataArray) -> list:
    """
    Create GCPs from an array of longitude, latitude and altitude (based on Sentinel-3 geocoding).

    Args:
        lon (xr.DataArray): Longitude array
        lat (xr.DataArray): Latitude array
        alt (xr.DataArray): Altitude array

    Returns:
        list: List of GroundControlPoints

    """
    gcps = []
    assert lat.data.shape == lon.data.shape == alt.data.shape

    # Get the GCPs coordinates
    nof_gcp_x = np.linspace(0, lat.rio.width - 1, dtype=int)
    nof_gcp_y = np.linspace(0, lat.rio.height - 1, dtype=int)

    # Create the GCP sequence
    gcp_id = 0
    for x in nof_gcp_x:
        for y in nof_gcp_y:
            curr_lon = lon.data[0, y, x]
            curr_lat = lat.data[0, y, x]
            curr_alt = alt.data[0, y, x]
            if (
                not np.isnan(curr_lon)
                and not np.isnan(curr_lat)
                and not np.isnan(curr_alt)
            ):
                gcps.append(
                    GroundControlPoint(
                        row=y,
                        col=x,
                        x=lon.data[0, y, x],
                        y=lat.data[0, y, x],
                        z=alt.data[0, y, x],
                        id=gcp_id,
                    )
                )
                gcp_id += 1

    return gcps


def quick_xml_to_dict(element: etree._Element) -> tuple:
    """
    Convert a lxml root to a nested dict (quick and dirty)

    https://lxml.de/FAQ.html#how-can-i-map-an-xml-tree-into-a-dict-of-dicts:


        How can I map an XML tree into a dict of dicts?

        Note that this beautiful quick-and-dirty converter expects children to have unique tag names and will silently
        overwrite any data that was contained in preceding siblings with the same name.
        For any real-world application of xml-to-dict conversion, you would better write your own,
        longer version of this.

    Args:
        element (etree._Element): Element to convert into a dict

    Returns:
        : XML as a nested dict

    """
    return element.tag, dict(map(quick_xml_to_dict, element)) or element.text


def open_rpc_file(path: Union[CloudPath, Path]) -> RPC:
    """
    Create a rasterio RPC object from a :code:`.rpc` file.
    Used for Vision-1 product

    Args:
        path: Path of the RPC file

    Returns:
        RPC: RPC object
    """

    def to_float(pd_table, field) -> float:
        pd_field = pd_table.T[field]
        val = None
        for val in pd_field.values[0].split(" "):
            if val:
                break
        return float(val)

    def to_list(pd_table, field) -> list:
        pd_list = pd_table[pd_table.index.str.contains(field)].values
        return [float(val[0]) for val in pd_list]

    try:
        rpcs_file = pd.read_csv(
            path, delimiter=":", names=["name", "value"], index_col=0
        )

        height_off = to_float(rpcs_file, "HEIGHT_OFF")
        height_scale = to_float(rpcs_file, "HEIGHT_SCALE")
        lat_off = to_float(rpcs_file, "LAT_OFF")
        lat_scale = to_float(rpcs_file, "LAT_SCALE")
        line_den_coeff = to_list(rpcs_file, "LINE_DEN_COEFF")
        line_num_coeff = to_list(rpcs_file, "LINE_NUM_COEFF")
        line_off = to_float(rpcs_file, "LINE_OFF")
        line_scale = to_float(rpcs_file, "LINE_SCALE")
        long_off = to_float(rpcs_file, "LONG_OFF")
        long_scale = to_float(rpcs_file, "LONG_SCALE")
        samp_den_coeff = to_list(rpcs_file, "SAMP_DEN_COEFF")
        samp_num_coeff = to_list(rpcs_file, "SAMP_NUM_COEFF")
        samp_off = to_float(rpcs_file, "SAMP_OFF")
        samp_scale = to_float(rpcs_file, "SAMP_SCALE")
        return RPC(
            height_off,
            height_scale,
            lat_off,
            lat_scale,
            line_den_coeff,
            line_num_coeff,
            line_off,
            line_scale,
            long_off,
            long_scale,
            samp_den_coeff,
            samp_num_coeff,
            samp_off,
            samp_scale,
            err_bias=None,
            err_rand=None,
        )
    except KeyError as msg:
        raise KeyError(f"Invalid RPC file, missing key: {msg}")


def simplify_footprint(
    footprint: gpd.GeoDataFrame, resolution: float, max_nof_vertices: int = 50
) -> gpd.GeoDataFrame:
    """
    Simplify footprint

    Args:
        footprint (gpd.GeoDataFrame): Footprint to be simplified
        resolution (float): Corresponding resolution
        max_nof_vertices (int): Maximum number of vertices of the wanted footprint

    Returns:
        gpd.GeoDataFrame: Simplified footprint
    """
    # Number of pixels of tolerance
    tolerance = [1, 2, 4, 8, 16, 32, 64]

    # Process only if given footprint is too complex (too many vertices)
    def simplify_geom(value):
        nof_vertices = len(value.exterior.coords)
        if nof_vertices > max_nof_vertices:
            for tol in tolerance:
                # Simplify footprint
                value = value.simplify(
                    tolerance=tol * resolution, preserve_topology=True
                )

                # Check if OK
                nof_vertices = len(value.exterior.coords)
                if nof_vertices < max_nof_vertices:
                    break
        return value

    footprint.geometry = footprint.geometry.apply(simplify_geom)

    return footprint


def simplify(footprint_fct: Callable):
    """
    Simplify footprint decorator

    Args:
        function (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(footprint_fct)
    def simplify_wrapper(self):
        """ Simplify footprint wrapper """
        footprint = footprint_fct(self)
        return simplify_footprint(footprint, self.resolution)

    return simplify_wrapper
