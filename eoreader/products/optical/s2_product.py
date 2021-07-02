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
""" Sentinel-2 products """

import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio import features, transform
from rasterio.enums import Resampling

from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS, SHADOWS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME
from sertit import files, rasters, vectors
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class S2ProductType(ListEnum):
    """Sentinel-2 products types (L1C or L2A)"""

    L1C = "L1C"
    L2A = "L2A"


BAND_DIR_NAMES = {
    S2ProductType.L1C: "IMG_DATA",
    S2ProductType.L2A: {
        "01": ["R60m"],
        "02": ["R10m", "R20m", "R60m"],
        "03": ["R10m", "R20m", "R60m"],
        "04": ["R10m", "R20m", "R60m"],
        "05": ["R20m", "R60m"],
        "06": ["R20m", "R60m"],
        "07": ["R20m", "R60m"],
        "08": ["R10m"],
        "8A": ["R20m", "R60m"],
        "09": ["R60m"],
        "11": ["R20m", "R60m"],
        "12": ["R20m", "R60m"],
    },
}


class S2Product(OpticalProduct):
    """
    Class of Sentinel-2 Products

    You can use directly the .zip file
    """

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.tile_name = self._get_tile_name()
        self.needs_extraction = False

        # Post init done by the super class
        super()._post_init()

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # S2: use 20m resolution, even if we have 60m and 10m resolution
        # In the future maybe set one resolution per band ?
        return 20.0

    def _get_tile_name(self) -> str:
        """
        Retrieve tile name

        Returns:
            str: Tile name
        """
        return self.split_name[-2]

    def _set_product_type(self) -> None:
        """Set products type"""
        if "MSIL2A" in self.name:
            self.product_type = S2ProductType.L2A
            self.band_names.map_bands(
                {
                    obn.CA: "01",
                    obn.BLUE: "02",
                    obn.GREEN: "03",
                    obn.RED: "04",
                    obn.VRE_1: "05",
                    obn.VRE_2: "06",
                    obn.VRE_3: "07",
                    obn.NIR: "08",
                    obn.NARROW_NIR: "8A",
                    obn.WV: "09",
                    obn.SWIR_1: "11",
                    obn.SWIR_2: "12",
                }
            )
        elif "MSIL1C" in self.name:
            self.product_type = S2ProductType.L1C
            self.band_names.map_bands(
                {
                    obn.CA: "01",
                    obn.BLUE: "02",
                    obn.GREEN: "03",
                    obn.RED: "04",
                    obn.VRE_1: "05",
                    obn.VRE_2: "06",
                    obn.VRE_3: "07",
                    obn.NIR: "08",
                    obn.NARROW_NIR: "8A",
                    obn.WV: "09",
                    obn.SWIR_CIRRUS: "10",
                    obn.SWIR_1: "11",
                    obn.SWIR_2: "12",
                }
            )
        else:
            raise InvalidProductError(f"Invalid Sentinel-2 name: {self.name}")

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
        def_band = self.band_names[self.get_default_band()]
        det_footprint = self.open_mask("DETFOO", def_band)
        footprint_gs = det_footprint.dissolve().convex_hull
        return gpd.GeoDataFrame(geometry=footprint_gs.geometry, crs=footprint_gs.crs)

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 8, 24, 11, 6, 31)
            >>> prod.get_datetime(as_datetime=False)
            '20200824T110631'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """

        date = self.split_name[2]

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def _get_res_band_folder(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the folder containing the bands of a proper S2 products.
        (IMG_DATA for L1C, IMG_DATA/Rx0m for L2A)

        Args:
            band_list (list): Wanted bands (listed as 01, 02...)
            resolution (float): Band resolution for Sentinel-2 products {R10m, R20m, R60m}.
                                The wanted bands will be chosen in this proper folder.

        Returns:
            dict: Dictionary containing the folder path for each queried band
        """
        # Open the band directory names
        s2_bands_folder = {}

        # Manage L2A
        band_dir = BAND_DIR_NAMES[self.product_type]
        for band in band_list:
            assert band in obn
            band_nb = self.band_names[band]
            if band_nb is None:
                raise InvalidProductError(
                    f"Non existing band ({band.name}) for S2-{self.product_type.name} products"
                )

            # If L2A products, we care about the resolution
            if self.product_type == S2ProductType.L2A:
                # If we got a true S2 resolution, open the corresponding band
                if resolution and f"R{int(resolution)}m" in band_dir[band_nb]:
                    dir_name = f"R{int(resolution)}m"

                # Else open the first one, it will be resampled when the ban will be read
                else:
                    dir_name = band_dir[band_nb][0]
            # If L1C, we do not
            else:
                dir_name = band_dir

            if self.is_archived:
                # Open the zip file
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    # Get the band folder (use dirname is the first of the list is a band)
                    s2_bands_folder[band] = [
                        os.path.dirname(f.filename)
                        for f in zip_ds.filelist
                        if dir_name in f.filename
                    ][0]
            else:
                # Search for the name of the folder into the S2 products
                s2_bands_folder[band] = next(self.path.glob(f"**/*/{dir_name}"))

        for band in band_list:
            if band not in s2_bands_folder:
                raise InvalidProductError(
                    f"Band folder for band {band.value} not found in {self.path}"
                )

        return s2_bands_folder

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <OpticalBandNames.GREEN: 'GREEN'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',
                <OpticalBandNames.RED: 'RED'>: 'zip+file://S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_folders = self._get_res_band_folder(band_list, resolution)
        band_paths = {}
        for band in band_list:
            # Get clean band path
            clean_band = self._get_clean_band_path(band, resolution=resolution)
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                try:
                    if self.is_archived:
                        band_paths[band] = files.get_archived_rio_path(
                            self.path,
                            f".*{band_folders[band]}.*_B{self.band_names[band]}.*.jp2",
                        )
                    else:
                        band_paths[band] = files.get_file_in_dir(
                            band_folders[band],
                            "_B" + self.band_names[band],
                            extension="jp2",
                        )
                except (FileNotFoundError, IndexError) as ex:
                    raise InvalidProductError(
                        f"Non existing {band} ({self.band_names[band]}) band for {self.path}"
                    ) from ex

        return band_paths

    def _read_band(
        self,
        path: str,
        band: BandNames = None,
        resolution: Union[tuple, list, float] = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Read band from disk.

        .. WARNING::
            Invalid pixels are not managed here

        Args:
            path (str): Band path
            band (BandNames): Band to read
            resolution (Union[tuple, list, float]): Resolution of the wanted band, in dataset resolution unit (X, Y)
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            XDS_TYPE: Band xarray

        """
        # Read band
        band_xda = rasters.read(
            path, resolution=resolution, size=size, resampling=Resampling.bilinear
        )

        # Compute the correct radiometry of the band
        original_dtype = band_xda.encoding.get("dtype", band_xda.dtype)
        if original_dtype == "uint16":
            band_xda /= 10000.0

        return band_xda.astype(np.float32)

    def open_mask(self, mask_str: str, band: Union[obn, str]) -> gpd.GeoDataFrame:
        """
        Open S2 mask (GML files stored in QI_DATA) as `gpd.GeoDataFrame`.

        Masks than can be called that way are:

        - `TECQUA`: Technical quality mask
        - `SATURA`: Saturated Pixels
        - `NODATA`: Pixel nodata (inside the detectors)
        - `DETFOO`: Detectors footprint -> used to process nodata outside the detectors
        - `DEFECT`: Defective pixels
        - `CLOUDS`, **only with `00` as a band !**

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod.open_mask("NODATA", GREEN)
            Empty GeoDataFrame
            Columns: [geometry]
            Index: []
            >>> prod.open_mask("SATURA", GREEN)
            Empty GeoDataFrame
            Columns: [geometry]
            Index: []
            >>> prod.open_mask("DETFOO", GREEN)
                                    gml_id  ...                                           geometry
            0  detector_footprint-B03-02-0  ...  POLYGON Z ((199980.000 4500000.000 0.000, 1999...
            1  detector_footprint-B03-03-1  ...  POLYGON Z ((222570.000 4500000.000 0.000, 2225...
            2  detector_footprint-B03-05-2  ...  POLYGON Z ((273050.000 4500000.000 0.000, 2730...
            3  detector_footprint-B03-07-3  ...  POLYGON Z ((309770.000 4453710.000 0.000, 3097...
            4  detector_footprint-B03-04-4  ...  POLYGON Z ((248080.000 4500000.000 0.000, 2480...
            5  detector_footprint-B03-06-5  ...  POLYGON Z ((297980.000 4500000.000 0.000, 2979...
            [6 rows x 3 columns]

        Args:
            mask_str (str): Mask name, such as DEFECT, NODATA, SATURA...
            band (Union[obn, str]): Band number as an OpticalBandNames or str (for clouds: 00)

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        # Check inputs
        assert mask_str in ["DEFECT", "DETFOO", "NODATA", "SATURA", "TECQUA", "CLOUDS"]
        if mask_str == "CLOUDS":
            band = "00"

        # Get QI_DATA path
        if isinstance(band, obn):
            band_name = self.band_names[band]
        else:
            band_name = band

        tmp_dir = tempfile.TemporaryDirectory()
        try:
            if self.is_archived:
                # Open the zip file
                # WE DON'T KNOW WHY BUT DO NOT USE files.read_archived_vector HERE !!!
                with zipfile.ZipFile(self.path, "r") as zip_ds:
                    filenames = [f.filename for f in zip_ds.filelist]
                    regex = re.compile(
                        f".*GRANULE.*QI_DATA.*MSK_{mask_str}_B{band_name}.gml"
                    )
                    mask_path = zip_ds.extract(
                        list(filter(regex.match, filenames))[0], tmp_dir.name
                    )
            else:
                # Get mask path
                mask_path = files.get_file_in_dir(
                    self.path,
                    f"**/*GRANULE/*/QI_DATA/MSK_{mask_str}_B{band_name}.gml",
                    exact_name=True,
                )

            # Read vector
            mask = vectors.read(mask_path, crs=self.crs())

        except Exception as ex:
            raise InvalidProductError(ex) from ex

        finally:
            tmp_dir.cleanup()

        return mask

    # pylint: disable=R0913
    # R0913: Too many arguments (6/5) (too-many-arguments)
    def _manage_invalid_pixels(
        self,
        band_arr: XDS_TYPE,
        band: obn,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> XDS_TYPE:
        """
        Manage invalid pixels (Nodata, saturated, defective...)
        See there: https://sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            XDS_TYPE: Cleaned band array
        """
        # Get detector footprint to deduce the outside nodata
        nodata_det = self.open_mask(
            "DETFOO", band
        )  # Detector nodata, -> pixels that are outside of the detectors

        # Rasterize nodata
        mask = features.rasterize(
            nodata_det.geometry,
            out_shape=(band_arr.rio.height, band_arr.rio.width),
            fill=self._mask_true,  # Outside detector = nodata (inverted compared to the usual)
            default_value=self._mask_false,  # Inside detector = not nodata
            transform=transform.from_bounds(
                *band_arr.rio.bounds(), band_arr.rio.width, band_arr.rio.height
            ),
            dtype=np.uint8,
        )

        #  Load masks and merge them into the nodata
        nodata_pix = self.open_mask(
            "NODATA", band
        )  # Pixel nodata, not pixels that are outside of the detectors !!!
        if len(nodata_pix) > 0:
            # Discard pixels corrected during crosstalk
            nodata_pix = nodata_pix[nodata_pix.gml_id == "QT_NODATA_PIXELS"]
        nodata_pix.append(self.open_mask("DEFECT", band))
        nodata_pix.append(self.open_mask("SATURA", band))

        # Technical quality mask
        tecqua = self.open_mask("TECQUA", band)
        if len(tecqua) > 0:
            # Do not take into account ancillary data
            tecqua = tecqua[tecqua.gml_id.isin(["MSI_LOST", "MSI_DEG"])]
        nodata_pix.append(tecqua)

        if len(nodata_pix) > 0:
            # Rasterize mask
            mask_pix = features.rasterize(
                nodata_pix.geometry,
                out_shape=(band_arr.rio.height, band_arr.rio.width),
                fill=self._mask_false,  # Outside vector
                default_value=self._mask_true,  # Inside vector
                transform=transform.from_bounds(
                    *band_arr.rio.bounds(), band_arr.rio.width, band_arr.rio.height
                ),
                dtype=np.uint8,
            )

            mask[mask_pix] = self._mask_true

        return self._set_nodata_mask(band_arr, mask)

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

        band_paths = self.get_band_paths(bands, resolution)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays

    def _get_condensed_name(self) -> str:
        """
        Get S2 products condensed name ({date}_S2_{tile}_{product_type}_{processed_hours}).

        Returns:
            str: Condensed name
        """
        # Used to make the difference between 2 products acquired on the same tile at the same date but cut differently
        proc_time = self.split_name[-1].split("T")[-1]
        return f"{self.get_datetime()}_{self.platform.name}_{self.tile_name}_{self.product_type.value}_{proc_time}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (149.148155074489, 32.6627897525474)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Read metadata
        root, _ = self.read_mtd()

        try:
            mean_sun_angles = root.find(".//Mean_Sun_Angle")
            zenith_angle = float(mean_sun_angles.findtext("ZENITH_ANGLE"))
            azimuth_angle = float(mean_sun_angles.findtext("AZIMUTH_ANGLE"))
        except TypeError:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        return azimuth_angle, zenith_angle

    def read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element {https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd}Level-2A_Tile_ID at ...>,
            {'nl': '{https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd}'})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        mtd_from_path = "GRANULE/*/*.xml"
        mtd_archived = "GRANULE.*\.xml"

        return self._read_mtd(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks
        """
        if band == SHADOWS:
            has_band = False
        else:
            has_band = True
        return has_band

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read S2 cloud mask .GML files (both valid for L2A and L1C products).
        https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            cloud_vec = self.open_mask("CLOUDS", "00")

            # Open a bands to mask it
            def_band = self._read_band(
                self.get_default_band_path(),
                self.get_default_band(),
                resolution=resolution,
                size=size,
            )
            nodata = np.where(np.isnan(def_band), 1, 0)

            for band in bands:
                if band == ALL_CLOUDS:
                    band_dict[band] = self._rasterize(def_band, cloud_vec, nodata)
                elif band == CIRRUS:
                    try:
                        cirrus = cloud_vec[cloud_vec.maskType == "CIRRUS"]
                    except AttributeError:
                        # No masktype -> empty
                        cirrus = gpd.GeoDataFrame(geometry=[], crs=cloud_vec.crs)
                    band_dict[band] = self._rasterize(def_band, cirrus, nodata)
                elif band == CLOUDS:
                    try:
                        clouds = cloud_vec[cloud_vec.maskType == "OPAQUE"]
                    except AttributeError:
                        # No masktype -> empty
                        clouds = gpd.GeoDataFrame(geometry=[], crs=cloud_vec.crs)
                    band_dict[band] = self._rasterize(def_band, clouds, nodata)
                elif band == RAW_CLOUDS:
                    band_dict[band] = self._rasterize(def_band, cloud_vec, nodata)
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Sentinel-2: {band}"
                    )

        return band_dict

    def _rasterize(
        self, xds: XDS_TYPE, geometry: gpd.GeoDataFrame, nodata: np.ndarray
    ) -> xr.DataArray:
        """
        Rasterize a vector on a memory dataset

        Args:
            xds: xarray
            geometry (gpd.GeoDataFrame): Geometry to rasterize
            nodata (np.ndarray): Nodata mask

        Returns:
            xr.DataArray: Rasterized vector
        """
        if not geometry.empty:
            # Just in case
            if geometry.crs != xds.rio.crs:
                geometry = geometry.to_crs(xds.rio.crs)

            # Rasterize mask
            cond = features.rasterize(
                geometry.geometry,
                out_shape=(xds.rio.height, xds.rio.width),
                fill=self._mask_false,  # Pixels outside mask
                default_value=self._mask_true,  # Pixels inside mask
                transform=transform.from_bounds(
                    *xds.rio.bounds(), xds.rio.width, xds.rio.height
                ),
                dtype=np.uint8,
            )
            cond = np.expand_dims(cond, axis=0)

        else:
            # If empty geometry, just
            cond = np.full(
                shape=(xds.rio.count, xds.rio.height, xds.rio.width),
                fill_value=self._mask_false,
                dtype=np.uint8,
            )
        return self._create_mask(xds, cond, nodata)
