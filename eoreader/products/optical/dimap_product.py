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
DIMAP V2 super class.
See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
for more information.
"""
import logging
import time
from abc import abstractmethod
from datetime import date, datetime
from enum import unique
from pathlib import Path
from typing import Union

import affine
import geopandas as gpd
import numpy as np
import rasterio
from cloudpathlib import CloudPath
from lxml import etree
from rasterio import crs as riocrs
from rasterio import features, transform
from sertit import files, rasters_rio, vectors
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

from eoreader import cache, cached_property, utils
from eoreader.bands import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS, SHADOWS, BandNames
from eoreader.bands import OpticalBandNames as obn
from eoreader.bands import to_str
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import VhrProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class DimapProductType(ListEnum):
    """
    DIMAP V2 product types (processing level).

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
class DimapBandCombination(ListEnum):
    """
    DIMAP V2 products band combination

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


class DimapProduct(VhrProduct):
    """
    Super Class of DIMAP V2 products.
    See `here <www.engesat.com.br/wp-content/uploads/PleiadesUserGuide-17062019.pdf>`_
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

        self._empty_mask = []

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

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Band combination
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//SPECTRAL_PROCESSING")
        if not band_combi:
            raise InvalidProductError(
                "Cannot find the band combination (from SPECTRAL_PROCESSING) type in the metadata file"
            )
        self.band_combi = getattr(DimapBandCombination, band_combi.replace("-", "_"))

        # Post init done by the super class
        super()._post_init()

    @abstractmethod
    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        raise NotImplementedError("This method should be implemented by a child class")

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        prod_type = self.split_name[3]
        self.product_type = getattr(DimapProductType, prod_type)

        # Manage bands of the product
        if self.band_combi == DimapBandCombination.P:
            self.band_names.map_bands({obn.PAN: 1})
        elif self.band_combi in [DimapBandCombination.MS, DimapBandCombination.PMS]:
            self.band_names.map_bands(
                {obn.BLUE: 3, obn.GREEN: 2, obn.RED: 1, obn.NIR: 4, obn.NARROW_NIR: 4}
            )
        elif self.band_combi in [DimapBandCombination.MS_N, DimapBandCombination.PMS_N]:
            self.band_names.map_bands({obn.BLUE: 3, obn.GREEN: 2, obn.RED: 1})
        elif self.band_combi in [DimapBandCombination.MS_X, DimapBandCombination.PMS_X]:
            self.band_names.map_bands(
                {obn.GREEN: 1, obn.RED: 2, obn.NIR: 3, obn.NARROW_NIR: 3}
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
        crs_name = root.findtext(".//GEODETIC_CRS_CODE")
        if not crs_name:
            crs_name = root.findtext(".//PROJECTED_CRS_CODE")
            if not crs_name:
                raise InvalidProductError(
                    "Cannot find the CRS name (from GEODETIC_CRS_NAME or PROJECTED_CRS_CODE) type in the metadata file"
                )

        return riocrs.CRS.from_string(crs_name)

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
        # Open metadata
        root, _ = self.read_mtd()

        # Open the Bounding_Polygon
        vertices = [v for v in root.iterfind(".//Vertex")]

        # Get the mean lon lat
        lon = float(np.mean([float(v.findtext("LON")) for v in vertices]))
        lat = float(np.mean([float(v.findtext("LAT")) for v in vertices]))

        # Compute UTM crs from center long/lat
        utm = vectors.corresponding_utm_projection(lon, lat)
        utm = riocrs.CRS.from_string(utm)

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
        return self.open_mask("ROI").to_crs(self.crs)

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

    def _get_name(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        return files.get_filename(self._get_dimap_path()).replace("DIM_", "")

    def _get_ortho_path(self) -> Union[CloudPath, Path]:
        """
        Get the orthorectified path of the bands.

        Returns:
            Union[CloudPath, Path]: Orthorectified path
        """
        if self.product_type in [DimapProductType.SEN, DimapProductType.PRJ]:
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
                with rasterio.open(str(self._get_dimap_path())) as src:
                    out_arr, meta = self._reproject(src.read(), src.meta, src.rpcs)
                    rasters_rio.write(out_arr, meta, ortho_path)

        else:
            ortho_path = self._get_dimap_path()

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
        # array data
        width = band_arr.rio.width
        height = band_arr.rio.height
        vec_tr = transform.from_bounds(
            *band_arr.rio.bounds(), band_arr.rio.width, band_arr.rio.height
        )

        # Get detector footprint to deduce the outside nodata
        nodata = self._load_nodata(width, height, vec_tr)

        #  Load masks and merge them into the nodata
        nodata_vec = self.open_mask("DET")  # Out of order detectors
        nodata_vec.append(self.open_mask("VIS"))  # Hidden area vector mask
        nodata_vec.append(self.open_mask("SLT"))  # Straylight vector mask

        if len(nodata_vec) > 0:
            # Rasterize mask
            mask = features.rasterize(
                nodata_vec.geometry,
                out_shape=(height, width),
                fill=self._mask_false,  # Outside vector
                default_value=self._mask_true,  # Inside vector
                transform=vec_tr,
                dtype=np.uint8,
            )
            nodata = nodata | mask

        return self._set_nodata_mask(band_arr, nodata)

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
        # array data
        width = band_arr.rio.width
        height = band_arr.rio.height
        vec_tr = transform.from_bounds(
            *band_arr.rio.bounds(), band_arr.rio.width, band_arr.rio.height
        )

        # Get detector footprint to deduce the outside nodata
        nodata = self._load_nodata(width, height, vec_tr)

        return self._set_nodata_mask(band_arr, nodata)

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
            center_vals = [
                a
                for a in root.iterfind(".//Located_Geometric_Values")
                if a.findtext("LOCATION_TYPE") == "Center"
            ][0]
            elev_angle = float(center_vals.findtext(".//SUN_ELEVATION"))
            azimuth_angle = float(center_vals.findtext(".//SUN_AZIMUTH"))
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
        mtd_from_path = "DIM_*.XML"
        mtd_archived = "DIM_.*\.XML"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        if band in [CIRRUS, SHADOWS]:
            has_band = False
        else:
            has_band = True
        return has_band

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
        band_dict = {}

        if bands:
            # Load cloud vector
            cld_vec = self.open_mask("CLD")
            has_vec = len(cld_vec) > 0

            # Load default xarray as a template
            def_utm_path = self._get_default_utm_band(resolution=resolution, size=size)

            with rasterio.open(str(def_utm_path)) as dst:
                if dst.count > 1:
                    def_xarr = utils.read(
                        dst,
                        resolution=resolution,
                        size=size,
                        indexes=[self.band_names[self.get_default_band()]],
                    )
                else:
                    def_xarr = utils.read(dst, resolution=resolution, size=size)

                # Load nodata
                width = def_xarr.rio.width
                height = def_xarr.rio.height
                vec_tr = transform.from_bounds(
                    *def_xarr.rio.bounds(), def_xarr.rio.width, def_xarr.rio.height
                )
                nodata = self._load_nodata(width, height, vec_tr)

                # Rasterize features if existing vector
                if has_vec:
                    cld_arr = features.rasterize(
                        cld_vec.geometry,
                        out_shape=(height, width),
                        fill=self._mask_false,  # Outside vector
                        default_value=self._mask_true,  # Inside vector
                        transform=vec_tr,
                        dtype=np.uint8,
                    )

                    # Rasterize gives a 2D array, we want a 3D array
                    cld_arr = np.expand_dims(cld_arr, axis=0)
                else:
                    cld_arr = np.zeros(
                        (1, def_xarr.rio.height, def_xarr.rio.width), dtype=np.uint8
                    )

            for band in bands:
                if band in [ALL_CLOUDS, CLOUDS, RAW_CLOUDS]:
                    cloud = self._create_mask(
                        def_xarr,
                        cld_arr,
                        nodata,
                    )
                else:
                    raise InvalidTypeError(f"Non existing cloud band for: {band}")

                # Rename
                band_name = to_str(band)[0]
                cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name)

        return band_dict

    def open_mask(self, mask_str: str) -> gpd.GeoDataFrame:
        """
        Open DIMAP V2 mask (GML files stored in MASKS) as :code:`gpd.GeoDataFrame`.

        Masks than can be called that way are:

        - :code:`CLD`: Cloud vector mask
        - :code:`DET`: Out of order detectors vector mask
        - :code:`QTE`: Synthetic technical quality vector mask
        - :code:`ROI`: Region of Interest vector mask
        - :code:`SLT`: Straylight vector mask
        - :code:`SNW`: Snow vector mask
        - :code:`VIS`: Hidden area vector mask (optional)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"IMG_PHR1A_PMS_001"
            >>> prod.open_mask("ROI")
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((118.86239 -2.81569, 118.86255 -2.815...
            [1 rows x 3 columns]

        Args:
            mask_str (str): Mask name, such as CLD, DET, ROI...

        Returns:
            gpd.GeoDataFrame: Mask as a vector
        """
        # Check inputs
        mandatory_masks = ["CLD", "DET", "QTE", "ROI", "SLT", "SNW"]
        optional_masks = ["VIS"]
        assert mask_str in mandatory_masks + optional_masks
        crs = self.crs

        mask_name = f"{self.condensed_name}_MSK_{mask_str}.geojson"
        mask_path = self._get_band_folder().joinpath(mask_name)
        if mask_path.is_file():
            mask = vectors.read(mask_path)
        elif mask_str in self._empty_mask:
            # Empty mask cannot be written on file
            mask = gpd.GeoDataFrame(geometry=[], crs=crs)
        else:
            if self.is_archived:
                # Open the zip file
                try:
                    mask = vectors.read(
                        self.path,
                        archive_regex=f".*MASKS.*{mask_str}.*_MSK\.GML",
                        crs=crs,
                    )
                except Exception:
                    if mask_str in optional_masks:
                        mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                    else:
                        raise InvalidProductError(
                            f"Mask {mask_str} not found for {self.path}"
                        )
            else:
                try:
                    mask_gml_path = files.get_file_in_dir(
                        self.path.joinpath("MASKS"),
                        f"*{mask_str}*_MSK.GML",
                        exact_name=True,
                    )

                    mask = vectors.read(mask_gml_path, crs=crs)
                except FileNotFoundError:
                    if mask_str in optional_masks:
                        mask = gpd.GeoDataFrame(geometry=[], crs=crs)
                    else:
                        raise InvalidProductError(
                            f"Mask {mask_str} not found for {self.path}"
                        )

            # Convert mask to correct CRS
            if not mask.empty and self.product_type in [
                DimapProductType.SEN,
                DimapProductType.PRJ,
            ]:
                LOGGER.info(f"Orthorectifying {mask_str}")
                with rasterio.open(str(self._get_dimap_path())) as dim_dst:
                    # Rasterize mask (no transform as we have teh vector in image geometry)
                    LOGGER.debug(f"\tRasterizing {mask_str}")
                    mask_raster = features.rasterize(
                        mask.geometry,
                        out_shape=(dim_dst.height, dim_dst.width),
                        fill=self._mask_false,  # Outside vector
                        default_value=self._mask_true,  # Inside vector
                        dtype=np.uint8,
                    )

                    # Reproject mask raster
                    LOGGER.debug(f"\tReprojecting {mask_str}")
                    reproj_data = self._reproject(
                        mask_raster, dim_dst.meta, dim_dst.rpcs
                    )

                    # Vectorize mask raster
                    LOGGER.debug(f"\tRevectorizing {mask_str}")
                    mask = rasters_rio.vectorize(
                        reproj_data,
                        values=self._mask_true,
                        default_nodata=self._mask_false,
                    )

            # Sometimes the GML mask lacks crs (why ?)
            elif (
                not mask.empty
                and not mask.crs
                and self.product_type
                in [
                    DimapProductType.ORT,
                    DimapProductType.MOS,
                ]
            ):
                # Convert to target CRS
                mask.crs = self._get_raw_crs()
                mask = mask.to_crs(self.crs)

            # Save to file
            if mask.empty:
                # Empty mask cannot be written on file
                self._empty_mask.append(mask_str)
            else:
                mask_path = self._get_band_folder(writable=True).joinpath(mask_name)
                mask.to_file(str(mask_path), driver="GeoJSON")

        return mask

    def _load_nodata(
        self,
        width: int,
        height: int,
        transform: affine.Affine,
    ) -> Union[np.ndarray, None]:
        """
        Load nodata (unimaged pixels) as a numpy array.

        Args:
            width (int): Array width
            height (int): Array height
            transform (affine.Affine): Transform to georeference array

        Returns:
            Union[np.ndarray, None]: Nodata array

        """
        nodata_det = self.open_mask("ROI")

        # Rasterize nodata
        return features.rasterize(
            nodata_det.geometry,
            out_shape=(height, width),
            fill=self._mask_true,  # Outside ROI = nodata (inverted compared to the usual)
            default_value=self._mask_false,  # Inside ROI = not nodata
            transform=transform,
            dtype=np.uint8,
        )

    def _get_dimap_path(self) -> Union[CloudPath, Path]:
        """
        Get the DIMAP filepath

        Returns:
            Union[CloudPath, Path]: DIMAP filepath

        """
        return self._get_path("DIM_", "XML")
