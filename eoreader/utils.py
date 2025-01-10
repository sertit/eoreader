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
"""Utils: mostly getting directories relative to the project"""

import contextlib
import logging
import os
import platform
import warnings
from functools import wraps
from typing import Callable, Union

import numpy as np
import pandas as pd
import xarray as xr
from lxml import etree
from rasterio import errors
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning
from rasterio.rpc import RPC
from sertit import AnyPath, files, geometry, logs, path, rasters
from sertit.snap import SU_MAX_CORE
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import EOREADER_NAME, cache
from eoreader.bands import is_index, is_sat_band
from eoreader.env_vars import NOF_BANDS_IN_CHUNKS, TILE_SIZE, USE_DASK
from eoreader.exceptions import InvalidProductError
from eoreader.keywords import _prune_keywords

LOGGER = logging.getLogger(EOREADER_NAME)
DEFAULT_TILE_SIZE = 1024
DEFAULT_NOF_BANDS_IN_CHUNKS = 1
UINT16_NODATA = rasters.UINT16_NODATA


def get_src_dir() -> AnyPathType:
    """
    Get src directory.

    Returns:
        str: Root directory
    """
    return AnyPath(__file__).parent


def get_root_dir() -> AnyPathType:
    """
    Get root directory.

    Returns:
        str: Root directory
    """
    return get_src_dir().parent


def get_data_dir() -> AnyPathType:
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

        # Look for non-empty directories
        for ddir in data_dirs:
            if len(os.listdir(ddir)) > 0:
                data_dir = ddir
                break

        if not data_dir:
            raise FileNotFoundError("Impossible to find the data directory.")

    return data_dir


def get_split_name(name: str, sep: str = "_") -> list:
    """
    Get split name (with _). Removes empty indexes.

    Args:
        name (str): Name to split
        sep (str): Separator

    Returns:
        list: Split name
    """
    return [x for x in name.split(sep) if x]


# flake8: noqa
def use_dask():
    """Use Dask or not"""
    # Check environment variable
    _use_dask = os.getenv(USE_DASK, "1").lower() in ("1", "true")

    # Check installed libs
    if _use_dask:
        try:
            import dask
            import distributed
        except ImportError:
            _use_dask = False

    return _use_dask


def read(
    raster_path: AnyPathStrType,
    pixel_size: Union[tuple, list, float] = None,
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
        raster_path (AnyPathStrType): Path to the raster
        pixel_size (Union[tuple, list, float]): Size of the pixels of the wanted band, in dataset unit (X, Y)
        size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
        resampling (Resampling): Resampling method
        masked (bool): Get a masked array
        indexes (Union[int, list]): Indexes to load. Load the whole array if None.
        **kwargs: Optional keyword arguments to pass into rioxarray.open_rasterio().
    Returns:
        xr.DataArray: Masked xarray corresponding to the raster data and its metadata

    """
    window = kwargs.get("window")

    # Always use chunks
    tile_size = os.getenv(TILE_SIZE, DEFAULT_TILE_SIZE)
    nof_bands_in_chunks = os.getenv(NOF_BANDS_IN_CHUNKS, DEFAULT_NOF_BANDS_IN_CHUNKS)

    if use_dask():
        if tile_size in [True, "auto", "True", "true"]:
            chunks = kwargs.get("chunks", "auto")
        else:
            chunks = kwargs.get(
                "chunks",
                {"band": nof_bands_in_chunks, "x": int(tile_size), "y": int(tile_size)},
            )
        # LOGGER.debug(f"Current chunking: {chunks}")
    else:
        # LOGGER.debug("Dask use is not enabled. No chunk will be used, but you may encounter memory overflow errors.")
        chunks = None

    try:
        # Disable georef warnings here as the SAR/Sentinel-3 products are not georeferenced
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            arr = rasters.read(
                raster_path,
                resolution=pixel_size,
                resampling=resampling,
                masked=masked,
                indexes=indexes,
                size=size,
                window=window,
                chunks=chunks,
                **_prune_keywords(
                    additional_keywords=["window", "chunks", "resolution"], **kwargs
                ),
            )

            # In EOReader, we don't care about the band coordinate of a band loaded from a stack.
            # Overwrite it (don't keep the number "2" if we loaded the second band of the stack)
            nof_bands = len(arr.coords["band"])
            arr = arr.assign_coords(
                {
                    "band": np.arange(start=1, stop=nof_bands + 1, dtype=int),
                }
            )
            return arr

    except errors.RasterioIOError as ex:
        if not isinstance(raster_path, str) and (
            str(raster_path).endswith("jp2")
            or str(raster_path).endswith("tif")
            and raster_path.exists()
        ):
            raise InvalidProductError(f"Corrupted file: {raster_path}") from ex
        else:
            raise


def write(xds: xr.DataArray, filepath: AnyPathStrType, **kwargs) -> None:
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
        filepath (AnyPathStrType): Path where to save it (directories should be existing)
        **kwargs: Overloading metadata, ie :code:`nodata=255` or :code:`dtype=np.uint8`
    """
    # Reset the long name as a list to write it down
    previous_long_name = xds.attrs.get("long_name")
    if previous_long_name and xds.rio.count > 1:
        try:
            xds.attrs["long_name"] = xds.attrs.get(
                "long_name", xds.attrs.get("name", "")
            ).split(" ")
        except AttributeError:
            pass

    # Write windowed in case of big rasters (> 5 Go)
    # Workaround to avoid core dumps
    with contextlib.suppress(Exception):
        if (
            "windowed" not in kwargs
            and xds.data.itemsize * xds.size / 1024 / 1024 / 1024 > 5
        ):
            kwargs["windowed"] = True

    rasters.write(xds, output_path=filepath, **_prune_keywords(["window"], **kwargs))

    # Set back the previous long name
    if previous_long_name and xds.rio.count > 1:
        xds.attrs["long_name"] = previous_long_name


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


def open_rpc_file(rpc_path: AnyPathType) -> RPC:
    """
    Create a rasterio RPC object from a :code:`.rpc` file.
    Used for Vision-1 product

    Args:
        rpc_path: Path of the RPC file

    Returns:
        RPC: RPC object
    """

    def to_float(pd_table, field) -> float:
        pd_field = pd_table.T[field]
        val = None
        for val in pd_field.iat[0].split(" "):
            if val:
                break
        return float(val)

    def to_list(pd_table, field) -> list:
        pd_list = pd_table[pd_table.index.str.contains(field)].values
        return [float(val[0]) for val in pd_list]

    try:
        rpcs_file = pd.read_csv(
            rpc_path, delimiter=":", names=["name", "value"], index_col=0
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


def simplify(footprint_fct: Callable):
    """
    Simplify footprint decorator

    Args:
        footprint_fct (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(footprint_fct)
    def simplify_wrapper(self):
        """Simplify footprint wrapper"""
        footprint = footprint_fct(self)
        return geometry.simplify_footprint(footprint, self.pixel_size)

    return simplify_wrapper


def stack_dict(
    bands: list, band_xds: xr.Dataset, save_as_int: bool, nodata: float, **kwargs
) -> (xr.DataArray, type):
    """
    Stack a dictionary containing bands in a DataArray

    Args:
        bands (list): List of bands (to keep the right order of the stack)
        band_xds (xr.Dataset): Dataset containing the bands
        save_as_int (bool): Convert stack to uint16 to save disk space (and therefore multiply the values by 10.000)
        nodata (float): Nodata value

    Returns:
        (xr.DataArray, type): Stack as a DataArray and its dtype
    """
    logs.deprecation_warning(
        "Deprecated function. Please use `utils.stack` instead. 'bands' is not necessary anymore"
    )
    return stack(band_xds, save_as_int, nodata, **kwargs)


def stack(
    band_xds: xr.Dataset, save_as_int: bool, nodata: float, **kwargs
) -> (xr.DataArray, type):
    """
    Stack a dictionary containing bands in a DataArray

    Args:
        band_xds (xr.Dataset): Dataset containing the bands
        save_as_int (bool): Convert stack to uint16 to save disk space (and therefore multiply the values by 10.000)
        nodata (float): Nodata value

    Returns:
        (xr.DataArray, type): Stack as a DataArray and its dtype
    """
    # Convert into dataset with str as names
    LOGGER.debug("Stacking")

    # Save as integer
    dtype = np.float32
    if save_as_int:
        scale = 10000
        round_nb = 1000
        round_min = -0.1
        try:
            stack_min = float(band_xds.to_array().quantile(0.001))
        except ValueError:
            stack_min = np.nanpercentile(band_xds.to_array(), 1)

        if np.round(stack_min * round_nb) / round_nb < round_min:
            LOGGER.warning(
                f"Cannot convert the stack to uint16 as it has negative values ({stack_min} < {round_min}). Keeping it in float32."
            )
        else:
            if stack_min < 0:
                LOGGER.warning(
                    "Small negative values ]-0.1, 0] have been found. Clipping to 0."
                )
                band_xds = band_xds.clip(min=0, max=None, keep_attrs=True)

            # Scale to uint16, fill nan and convert to uint16
            dtype = np.uint16
            for band, band_xda in band_xds.items():
                # SCALING
                # NOT ALL bands need to be scaled, only:
                # - Satellite bands
                # - index
                if is_sat_band(band) or is_index(band):
                    if np.nanmax(band_xda) > UINT16_NODATA / scale:
                        LOGGER.debug(
                            "Band not in reflectance, keeping them as is (the values will be rounded)"
                        )
                    else:
                        band_xds[band] = band_xda * scale

            # Fill no data
            band_xds = band_xds.fillna(nodata)

    # Create dataset, with dims well-ordered
    stack = band_xds.to_stacked_array(
        new_dim="bands", sample_dims=("x", "y")
    ).transpose("bands", "y", "x")

    if dtype == np.float32:
        # Set nodata if needed (NaN values are already set)
        if stack.rio.encoded_nodata != nodata:
            stack = stack.rio.write_nodata(nodata, encoded=True, inplace=True)

    return stack, dtype


def get_dim_img_path(dim_path: AnyPathStrType, img_name: str = "*") -> list:
    """
    Get the image path from a :code:`BEAM-DIMAP` data.

    A :code:`BEAM-DIMAP` file cannot be opened by rasterio, although its :code:`.img` file can.

    .. code-block:: python

        >>> dim_path = "path/to/dimap.dim"  # BEAM-DIMAP image
        >>> img_path = get_dim_img_path(dim_path)

        >>> # Read raster
        >>> raster, meta = read(img_path)

    Args:
        dim_path (AnyPathStrType): DIM path (.dim or .data)
        img_name (str): .img file name (or regex), in case there are multiple .img files (ie. for S3 data)

    Returns:
        list: .img files as a list
    """
    dim_path = AnyPath(dim_path)
    if dim_path.suffix == ".dim":
        dim_path = dim_path.with_suffix(".data")

    assert dim_path.suffix == ".data" and dim_path.is_dir()

    return path.get_file_in_dir(
        dim_path, img_name, extension="img", exact_name=True, get_list=True
    )


def load_np(path_to_load: AnyPathStrType, output: AnyPathStrType) -> np.ndarray:
    """
    Load numpy pickles, with a handling of cloud-stored files.

    Args:
        path_to_load (AnyPathStrType): Pickle path
        output (AnyPathStrType): Where to download the pickle if it's stored on the cloud

    Returns:
        np.ndarray: Numpy array
    """
    if path.is_cloud_path(path_to_load):
        path_to_load = path_to_load.download_to(output)
    return np.load(str(path_to_load))


def get_max_cores():
    return int(os.getenv(SU_MAX_CORE, os.cpu_count() - 2))


@cache
def get_archived_file_list(archive_path: AnyPathStrType):
    """
    Overload of sertit.path.get_archived_file_list to cache its retrieval:
    this operation is expensive when done with large archives stored on the cloud (and thus better done only once)
    """
    file_list = path.get_archived_file_list(archive_path=archive_path)
    return file_list


@cache
def read_archived_file(
    archive_path: AnyPathStrType, regex: str, file_list: list = None
):
    """
    Overload of sertit.files.read_archived_file to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    file_list = files.read_archived_file(
        archive_path=archive_path, regex=regex, file_list=file_list
    )
    return file_list


@cache
def read_archived_xml(archive_path: AnyPathStrType, regex: str, file_list: list = None):
    """
    Overload of sertit.files.read_archived_xml to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    file_list = files.read_archived_xml(
        archive_path=archive_path,
        regex=regex,
        file_list=file_list,
    )
    return file_list


@cache
def read_archived_html(
    archive_path: AnyPathStrType, regex: str, file_list: list = None
):
    """
    Overload of sertit.files.read_archived_html to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    file_list = files.read_archived_html(
        archive_path=archive_path,
        regex=regex,
        file_list=file_list,
    )
    return file_list


@cache
def get_archived_path(
    archive_path: AnyPathStrType,
    regex: str,
    as_list: bool = False,
    case_sensitive: bool = False,
    file_list: list = None,
) -> Union[list, AnyPathType]:
    """
    Overload of sertit.path.get_archived_path to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    file_list = path.get_archived_path(
        archive_path=archive_path,
        regex=regex,
        as_list=as_list,
        case_sensitive=case_sensitive,
        file_list=file_list,
    )
    return file_list


@cache
def get_archived_rio_path(
    archive_path: AnyPathStrType,
    regex: str,
    as_list: bool = False,
    file_list: list = None,
) -> Union[list, AnyPathType]:
    """
    Overload of sertit.path.get_archived_path to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    file_list = path.get_archived_rio_path(
        archive_path=archive_path,
        regex=regex,
        as_list=as_list,
        file_list=file_list,
    )
    return file_list


def is_uint16(band_arr: xr.DataArray):
    """Is this array saved as uint16 on disk?"""
    return band_arr.encoding.get("dtype") in ["uint16", np.uint16]
