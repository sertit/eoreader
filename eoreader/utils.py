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
import geopandas as gpd
import xarray as xr
from lxml import etree
from rasterio import errors
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning
from rasterio.rpc import RPC
from sertit import AnyPath, files, geometry, path, rasters, misc
from sertit.snap import SU_MAX_CORE
from sertit.types import AnyPathStrType, AnyPathType, AnyXrDataStructure

from eoreader import EOREADER_NAME, cache
from eoreader.bands import is_index, is_sat_band, to_str
from eoreader.env_vars import (
    NOF_BANDS_IN_CHUNKS,
    TILE_SIZE,
    USE_DASK,
    BAND_RESAMPLING,
    DEFAULT_DRIVER,
)
from eoreader.exceptions import InvalidProductError
from eoreader.keywords import _prune_keywords

LOGGER = logging.getLogger(EOREADER_NAME)
DEFAULT_TILE_SIZE = 1024
DEFAULT_NOF_BANDS_IN_CHUNKS = 1
UINT16_NODATA = rasters.UINT16_NODATA


# Workaround for now, remove this asap
def read_bit_array(
    bit_mask: Union[xr.DataArray, np.ndarray], bit_id: Union[list, int]
) -> Union[np.ndarray, list]:
    """
    Read 8 bit arrays as a succession of binary masks.

    Forces array to :code:`np.uint8`.

    See :py:func:`rasters.read_bit_array`.

    Args:
        bit_mask (np.ndarray): Bit array to read
        bit_id (int): Bit ID of the slice to be read
          Example: read the bit 0 of the mask as a cloud mask (Theia)

    Returns:
        Union[np.ndarray, list]: Binary mask or list of binary masks if a list of bit_id is given
    """
    if misc.compare_version("sertit", "1.47.0", ">="):
        return rasters.read_bit_array(bit_mask, bit_id)
    else:
        # Suppress nan nodata and convert back to original dtype if known

        if isinstance(bit_mask, np.ndarray):
            bit_mask = np.nan_to_num(bit_mask)
        elif isinstance(bit_mask, xr.DataArray):
            orig_dtype = bit_mask.encoding.get("dtype")
            bit_mask = bit_mask.fillna(0).data
            if orig_dtype is not None and bit_mask.dtype != orig_dtype:
                bit_mask = bit_mask.astype(orig_dtype)

        else:
            bit_mask = bit_mask.fillna(0)
        from sertit import rasters_rio

        return rasters_rio.read_bit_array(bit_mask, bit_id)


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
        size (Union[tuple, list]): Size of the array (width, height). Overrides pixel_size if provided.
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
                resolution=pixel_size if size is None else None,
                resampling=resampling,
                masked=masked,
                indexes=indexes,
                size=size,
                window=window,
                chunks=chunks,
                **_prune_keywords(
                    additional_keywords=[
                        "resolution",
                        "resampling",
                        "masked",
                        "indexes",
                        "size",
                        "window",
                        "chunks",
                        "driver",
                    ],
                    **kwargs,
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

            arr = write_path_in_attrs(arr, raster_path)

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

    # TODO: drop this when python > 3.9
    # WORKAROUND TO: https://github.com/numpy/numpy/releases/tag/v2.2.3
    # Computing the stats for COGs and dask bugs with numpy 2.0 (fixed with 2.1)
    # However python 3.9 is limited to 2.0.x, so be careful with that (really not nice to have no stats when reading the files)
    write_cogs_with_dask = not (
        misc.compare_version("numpy", "2.0", ">=")
        and misc.compare_version("numpy", "2.1", "<")
    )

    rasters.write(
        xds,
        output_path=filepath,
        driver=get_driver(kwargs),
        write_cogs_with_dask=write_cogs_with_dask,
        **_prune_keywords(["window", "driver"], **kwargs),
    )

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


def write_path_in_attrs(
    xda: AnyXrDataStructure, path: AnyPathStrType
) -> AnyXrDataStructure:
    """
    Write path in attrs

    Args:
        xda (AnyXrDataStructure): Xarray to complete
        path (AnyPathStrType): Path to write

    Returns:
        AnyXrDataStructure: Output xarray
    """
    xda.attrs["path"] = str(path)
    return xda


def convert_to_uint16(xds: AnyXrDataStructure) -> (AnyXrDataStructure, type):
    """
    Convert an array to uint16 before saving it to disk.

    Args:
        xds (AnyXrDataStructure): Array to convert

    Returns:
        Converted array

    """
    scale = 10000
    round_nb = 1000
    round_min = -0.1

    if not isinstance(xds, xr.DataArray):
        xda = xds.to_array()
    else:
        xda = xds

    try:
        stack_min = float(xda.quantile(0.001))
    except ValueError:
        stack_min = np.nanpercentile(xda, 1)

    if np.round(stack_min * round_nb) / round_nb < round_min:
        LOGGER.warning(
            f"Cannot convert the stack to uint16 as it has negative values ({stack_min} < {round_min}). Keeping it in float32."
        )
        dtype = np.float32
    else:
        dtype = np.uint16
        if stack_min < 0:
            LOGGER.warning(
                "Small negative values ]-0.1, 0] have been found. Clipping to 0."
            )
            xds = xds.clip(min=0, max=None, keep_attrs=True)

        for band, band_xda in xds.items():
            # SCALING
            # NOT ALL bands need to be scaled, only:
            # - Satellite bands
            # - index
            if is_sat_band(band) or is_index(band):
                if np.nanmax(band_xda) > UINT16_NODATA / scale:
                    LOGGER.debug(
                        f"Band {to_str(band, as_list=False)} seems already scaled, keeping it as is (the values will be rounded to integers though)."
                    )
                else:
                    xds[band] = band_xda * scale

        # Fill no data and convert to uint16
        xds = xds.fillna(UINT16_NODATA).astype(dtype)

    return xds, dtype


def stack(band_xds: xr.Dataset, **kwargs) -> (xr.DataArray, type):
    """
    Stack a dictionary containing bands in a DataArray

    Args:
        band_xds (xr.Dataset): Dataset containing the bands

    Returns:
        (xr.DataArray, type): Stack as a DataArray and its dtype
    """
    # Convert into dataset with str as names
    LOGGER.debug("Stacking")

    # Save as integer
    dtype = kwargs.get("dtype", np.float32)
    nodata = kwargs.get("nodata", rasters.get_nodata_value_from_dtype(dtype))

    # Create dataset, with dims well-ordered
    stack = (
        band_xds.fillna(nodata)
        .to_stacked_array(new_dim="bands", sample_dims=("x", "y"))
        .transpose("bands", "y", "x")
    )

    # Set nodata if needed (NaN values are already set)
    if dtype == np.float32 and stack.rio.encoded_nodata != nodata:
        stack = rasters.set_nodata(stack.astype(dtype), nodata)

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
    from sertit.rasters import get_dim_img_path

    return get_dim_img_path(dim_path, img_name, get_list=True)


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
    try:
        from sertit.perf import get_max_cores

        return get_max_cores()
    except ModuleNotFoundError:
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
    file = files.read_archived_file(
        archive_path=archive_path, regex=regex, file_list=file_list
    )
    return file


@cache
def read_archived_xml(archive_path: AnyPathStrType, regex: str, file_list: list = None):
    """
    Overload of sertit.files.read_archived_xml to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    xml = files.read_archived_xml(
        archive_path=archive_path,
        regex=regex,
        file_list=file_list,
    )
    return xml


@cache
def read_archived_html(
    archive_path: AnyPathStrType, regex: str, file_list: list = None
):
    """
    Overload of sertit.files.read_archived_html to cache its reading:
    this operation is expensive when done with large archives (especially tars) stored on the cloud (and thus better done only once)
    """
    html = files.read_archived_html(
        archive_path=archive_path,
        regex=regex,
        file_list=file_list,
    )
    return html


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


def get_band_resampling():
    """Overrides the default band resampling (bilinear) with the env variable "EOREADER_BAND_RESAMPLING", if existing and valid"""
    resampling = Resampling.bilinear
    with contextlib.suppress(ValueError, TypeError):
        resampling = Resampling(int(os.getenv(BAND_RESAMPLING)))
        LOGGER.debug(f"Band resampling overridden to '{resampling.name}'.")

    return resampling


def get_window_suffix(window) -> str:
    """Get the window suffix to add it into band filenames"""
    win_suffix = ""
    if window is not None:
        if path.is_path(window):
            win_suffix = path.get_filename(window)
        elif isinstance(window, gpd.GeoDataFrame):
            win_suffix = window.attrs.get("name")
        if not win_suffix:
            win_suffix = f"win{files.hash_file_content(str(window))}"

    return win_suffix


def get_driver(kwargs: dict) -> str:
    """Pop the driver to write a file on disk from kwargs."""
    driver = kwargs.get("driver")
    if driver is None:
        driver = os.environ.get(DEFAULT_DRIVER, "COG")
    return driver
