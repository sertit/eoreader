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
"""
Pleiades products.
See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
for more information.
"""
import glob
import logging
import os
import re
import time
import zipfile
from datetime import date, datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import rasterio
import rioxarray
import xarray
from lxml import etree
from rasterio import features, vrt
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
class PldProductType(ListEnum):
    """
    Pleiades product types (processing level).

    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    (A.1.1.2 Variable Key Information) for more information.
    """

    SEN = "Primary"
    """
    Primary (L1A), abbreviation for Sensor.
    The Primary product is the geometric processing level closest to the natural image acquired by the sensor.
    """

    PRJ = "Projected"
    """
    Projected (L2A).
    Compared to Primary level, the projected level results from an additional process to map the image
    onto an Earth cartographic system at a fixed altitude value.
    The image is georeferenced without correction from acquisition and terrain off-nadir effects.
    This image-to-map transformation is directly compatible with GIS environment,
    for example to overlay the image on other data.
    """

    ORT = "Ortho Single Image"
    """
    Ortho (L3), single image.
    The Ortho product is a georeferenced image in Earth geometry,
    corrected from acquisition and terrain off-nadir effects.
    The Ortho is produced as a standard, with fully automatic processing.
    """

    MOS = "Ortho Mosaic Image"
    """
    Ortho (L3), mosaic image.
    The Ortho product is a georeferenced image in Earth geometry,
    corrected from acquisition and terrain off-nadir effects.
    The Ortho is produced as a standard, with fully automatic processing.
    """


@unique
class PldBandCombination(ListEnum):
    """
    Pleiades band combination

    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    (A.1.1.2 Variable Key Information) for more information.
    """

    P = "Panchromatic"
    """
    The Pléiades Panchromatic product includes only one black and white band.
    It covers wavelengths between 0.47 and 0.83 μm of the visible spectrum.
    The product pixel size is 0.5 m (Ortho).
    """

    MS = "Multi Spectral"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    """

    MS_N = "Multi Spectral in natural color"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    (3 bands: BLUE GREEN RED)
    """

    MS_X = "Multi Spectral in false color"
    """
    The Multispectral product includes four Multispectral (colour) bands: blue, red, green and near infrared.
    The product pixel size is 2 m (Ortho).
    (3 bands: GREEN RED NIR)
    """

    PMS = "Pansharpened Multi Spectral"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product (4 bands)
    """

    PMS_N = "Pansharpened Multi Spectral in natural color"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product
    (3 bands: BLUE GREEN RED)
    """

    PMS_X = "Pansharpened Multi Spectral in false color"
    """
    Pan-sharpened products combine the visual coloured information of the Multispectral data with the details
    provided by of the Panchromatic data, resulting in a higher resolution 0.5 m colour product
    (3 bands: GREEN RED NIR)
    """


class PldProduct(OpticalProduct):
    """
    Class of Pleiades products.
    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
    for more information.
    """

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.needs_extraction = False

        # Band combination
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//SPECTRAL_PROCESSING")
        if not band_combi:
            raise InvalidProductError(
                "Cannot find the band combination (from SPECTRAL_PROCESSING) type in the metadata file"
            )
        self.band_combi = getattr(PldBandCombination, band_combi.replace("-", "_"))

        # Post init done by the super class
        super()._post_init()

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # Not Pansharpened images
        if self.band_combi in [
            PldBandCombination.MS,
            PldBandCombination.MS_X,
            PldBandCombination.MS_N,
        ]:
            return 2.0
        # Pansharpened images
        else:
            return 0.5

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()
        prod_type = os.path.basename(root.find(".//DATA_FILE_PATH").base).split("_")[4]
        if not prod_type:
            raise InvalidProductError(
                "Cannot find the product type (from PROCESSING_LEVEL) type in the metadata file"
            )
        self.product_type = getattr(PldProductType, prod_type)

        # TODO
        if self.product_type == PldProductType.SEN:
            raise NotImplementedError(
                f"L1A Product (SEN) are not yet managed for Pleiades products {self.path}"
            )
        elif self.product_type == PldProductType.PRJ:
            raise NotImplementedError(
                f"L2A Product (PRJ) are not yet managed for Pleiades products {self.path}"
            )

        # Manage bands of the product
        if self.band_combi == PldBandCombination.P:
            self.band_names.map_bands({obn.PAN: 1})
        elif self.band_combi in [PldBandCombination.MS, PldBandCombination.PMS]:
            self.band_names.map_bands(
                {obn.BLUE: 1, obn.GREEN: 2, obn.RED: 3, obn.NIR: 4}
            )
        elif self.band_combi in [PldBandCombination.MS_N, PldBandCombination.PMS_N]:
            self.band_names.map_bands({obn.BLUE: 1, obn.GREEN: 2, obn.RED: 3})
        elif self.band_combi in [PldBandCombination.MS_X, PldBandCombination.PMS_X]:
            self.band_names.map_bands({obn.GREEN: 1, obn.RED: 2, obn.NIR: 3})
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
               index                                           geometry
            0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        Indeed, nodata pixels vary according to the band sensor footprint,
        whereas QA nodata is where at least one band has nodata.

        We chose to keep QA nodata values for the footprint in order to show where all bands are valid.

        **TL;DR: We use the QA nodata value to determine the product's footprint**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return self.open_mask("ROI")

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format `YYYYMMDDTHHMMSS` <-> `%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms
            >>> prod.get_datetime(as_datetime=False)
            '20190625T105728'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
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
        time_dt = time.strptime(time_str, "%H:%M:%S.%fZ")

        date_str = f"{date_dt.strftime('%Y%m%d')}T{time.strftime('%H%M%S', time_dt)}"

        if as_datetime:
            date_str = datetime.strptime(date_str, DATETIME_FMT)

        return date_str

    def get_band_paths(self, band_list: list, resolution: float = None) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands.alias import *
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <OpticalBandNames.GREEN: 'GREEN'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
                <OpticalBandNames.RED: 'RED'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        # Processed path names
        reproj_path = os.path.join(self.output, f"{self.condensed_name}_bands.tif")

        # Check band status
        is_reproj = os.path.isfile(reproj_path)

        band_paths = {}
        for band in band_list:
            # First look for reprojected bands
            if not is_reproj:
                LOGGER.info("Reprojecting Pleiades bands to UTM.")
                # Then for original data
                path = self._get_path("DIM_PHR", "XML")

                # If the CRS is not in UTM, reproject it
                # For reprojecting large datatet, use WarpedVRT as seen here:
                # https://corteva.github.io/rioxarray/stable/examples/reproject.html
                with rasterio.open(path) as src_dst:
                    with vrt.WarpedVRT(src_dst, crs=src_dst.crs) as vrt_dst:
                        img = rioxarray.open_rasterio(vrt_dst)
                        if not img.rio.crs.is_projected:
                            img_reproj = img.rio.reproject(img.rio.estimate_utm_crs())

                            # Bug workaround
                            # ValueError: failed to prevent overwriting existing key _FillValue in attrs.
                            # This is probably an encoding field used by xarray to describe how a variable is serialized
                            # To proceed, remove this key from the variable's attributes manually.
                            try:
                                rasters.write(img_reproj, reproj_path, nodata=0)
                            except ValueError:
                                img_reproj.attrs.pop("_FillValue")
                                rasters.write(img_reproj, reproj_path, nodata=0)

                            path = reproj_path
            else:
                path = reproj_path

            band_paths[band] = path

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
            path,
            resolution=resolution,
            size=size,
            resampling=Resampling.bilinear,
            indexes=[self.band_names[band]],
        )

        # If not set nodata, set it here
        if not band_xda.rio.encoded_nodata:
            band_xda = rasters.set_nodata(band_xda, 0)

        # Compute the correct radiometry of the band
        band_xda = band_xda / 10000.0

        return band_xda

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
        See
        `here <https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf>`_
        (unusable data mask) for more information.

        Args:
            band_arr (XDS_TYPE): Band array
            band (obn): Band name as an OpticalBandNames
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            XDS_TYPE: Cleaned band array
        """
        nodata_true = 1
        nodata_false = 0

        # Get detector footprint to deduce the outside nodata
        nodata = self.open_mask("ROI")

        #  Load masks and merge them into the nodata
        nodata.append(self.open_mask("DET"))  # Out of order detectors
        nodata.append(self.open_mask("VIS"))  # Hidden area vector mask
        nodata.append(self.open_mask("SLT"))  # Straylight vector mask

        if len(nodata) > 0:
            # Rasterize mask
            mask = features.rasterize(
                nodata.geometry,
                out_shape=(band_arr.rio.width, band_arr.rio.height),
                fill=nodata_false,  # OK pixels = OK value
                default_value=nodata_true,  # Discarded pixels = nodata
                transform=band_arr.rio.transform(),
                dtype=np.uint8,
            )
        else:
            mask = np.full(band_arr.shape, fill_value=nodata_false, dtype=np.uint8)

        return self._set_nodata_mask(band_arr, mask)

    def _load_bands(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load bands as numpy arrays with the same resolution (and same metadata).

        Args:
            bands list: List of the wanted bands
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        band_paths = self.get_band_paths(bands)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(band_paths, resolution=resolution, size=size)

        return band_arrays

    def _get_condensed_name(self) -> str:
        """
        Get PlanetScope products condensed name ({date}_PLD_{product_type}_{band_combi}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.product_type.name}_{self.band_combi.name}"

    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (154.554755774838, 27.5941391571236)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            center_vals = [
                a
                for a in root.iterfind(".//Located_Geometric_Values")
                if a.findtext("LOCATION_TYPE") == "Center"
            ][0]
            elev_angle = float(center_vals.findtext(".//SUN_ELEVATION"))
            azimuth_angle = float(center_vals.findtext(".//SUN_AZIMUTH"))
        except TypeError:
            raise InvalidProductError("Azimuth or Zenith angles not found")

        # From elevation to zenith
        zenith_angle = 90.0 - elev_angle

        return azimuth_angle, zenith_angle

    def read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"20210406_015904_37_2407.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element {http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}
            EarthObservation at 0x1a2621f03c8>,
            {
                'opt': '{http://earth.esa.int/opt}',
                'gml': '{http://www.opengis.net/gml}',
                'eop': '{http://earth.esa.int/eop}',
                'ps': '{http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}'
            })

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = os.path.join("DIM_PHR*.XML")
        mtd_archived = ".*DIM_PHR.*\.XML"

        return self._read_mtd(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        if band in [CIRRUS, SHADOWS]:
            has_band = False
        else:
            has_band = True
        return has_band

    def _load_clouds(
        self, bands: list, resolution: float = None, size: Union[list, tuple] = None
    ) -> dict:
        """
        Load cloud files as xarrays.

        CIRRUS is HEAVY_HAZE

        Args:
            bands (list): List of the wanted bands
            resolution (int): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        # Load default xarray as a template
        def_xarr = self._read_band(
            self.get_default_band_path(),
            band=self.get_default_band(),
            resolution=resolution,
            size=size,
        )

        # Load nodata
        nodata = self._load_nodata(resolution, size).data

        if bands:
            for res_id in bands:
                if res_id in [ALL_CLOUDS, CLOUDS, RAW_CLOUDS]:
                    band_dict[res_id] = self._create_mask(
                        def_xarr.rename(ALL_CLOUDS.name),
                        self.open_mask("CLD", resolution, size).data,
                        nodata,
                    )
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Pleiades: {res_id}"
                    )

        return band_dict

    def open_mask(self, mask_str: str) -> gpd.GeoDataFrame:
        """
        Open Pleiades mask (GML files stored in MASKS) as `gpd.GeoDataFrame`.

        Masks than can be called that way are:

        - `CLD`: Cloud vector mask
        - `DET`: Out of order detectors vector mask
        - `QTE`: Synthetic technical quality vector mask
        - `ROI`: Region of Interest vector mask
        - `SLT`: Straylight vector mask
        - `SNW`: Snow vector mask
        - `VIS`: Hidden area vector mask (optional)

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
            mask_str (str): Mask name, such as CLD, DET, ROI...

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        # Check inputs
        mandatory_masks = ["CLD", "DET", "QTE", "ROI", "SLT", "SNW"]
        optional_masks = ["VIS"]
        assert mask_str in mandatory_masks + optional_masks
        crs = self.crs()

        if self.is_archived:
            # Open the zip file
            # WE DON'T KNOW WHY BUT DO NOT USE files.read_archived_vector HERE !!!
            with zipfile.ZipFile(self.path, "r") as zip_ds:
                filenames = [f.filename for f in zip_ds.filelist]
                regex = re.compile(f".*MASKS.*{mask_str}_PHR.*_MSK\.GML")
                try:
                    mask_path_zip = list(filter(regex.match, filenames))[0]
                    with zip_ds.open(mask_path_zip) as mask_path:
                        mask = vectors.open_gml(mask_path, crs=crs)
                except IndexError:
                    if mask_str in optional_masks:
                        mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                    else:
                        raise InvalidProductError(
                            f"Mask {mask_str} not found for {self.path}"
                        )
        else:
            try:
                # Get mask path
                mask_path = files.get_file_in_dir(
                    os.path.join(self.path, "MASKS"),
                    f"{mask_str}_PHR*_MSK.GML",
                    exact_name=True,
                )

                mask = vectors.open_gml(mask_path, crs=crs)
            except FileNotFoundError:
                if mask_str in optional_masks:
                    mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                else:
                    raise InvalidProductError(
                        f"Mask {mask_str} not found for {self.path}"
                    )

        return mask

    def _load_nodata(
        self,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> Union[xarray.DataArray, None]:
        """
        Load nodata (unimaged pixels) as a numpy array.

        Args:
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            Union[xarray.DataArray, None]: Nodata array

        """
        band_arr = rasters.read(
            self.get_default_band_path(),
            resolution=resolution,
            size=size,
            indexes=[self.band_names[self.get_default_band()]],
        )
        nodata_det = self.open_mask("ROI")

        # Rasterize nodata
        return features.rasterize(
            nodata_det.geometry,
            out_shape=(band_arr.rio.width, band_arr.rio.height),
            fill=1,  # Outside ROI = nodata
            default_value=0,  # Inside ROI = acceptable value
            transform=band_arr.rio.transform(),
            dtype=np.uint8,
        )

    def _get_path(self, filename: str, extension: str) -> str:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension
            as_list (bool): If true, returns a list of all matches, else tyhe first match as a string

        Returns:
            Union[list, str]: Path or list of paths (needs this because of potential mosaic)

        """
        path = []
        try:
            if self.is_archived:
                path = files.get_archived_rio_path(
                    self.path,
                    f".*{filename}.*\.{extension}",
                )
            else:
                path = glob.glob(os.path.join(self.path, f"*{filename}*.{extension}"))[
                    0
                ]

        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return path
