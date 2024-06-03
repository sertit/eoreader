# -*- coding: utf-8 -*-
# Copyright 2024, SERTIT-ICube - France, https://sertit.unistra.fr/
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
COSMO-SkyMed products.
More info `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
"""
import logging
import os
import tempfile
from datetime import datetime
from enum import unique
from io import BytesIO
from typing import Union

import geopandas as gpd
import h5netcdf
import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from lxml.builder import E
from rasterio import merge
from sertit import AnyPath, path, rasters, rasters_rio, strings, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType
from shapely.geometry import Polygon, box

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.exceptions import InvalidProductError
from eoreader.products import SarProduct, SarProductType
from eoreader.products.product import OrbitDirection
from eoreader.products.sar.sar_product import SAR_PREDICTOR

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CosmoProductType(ListEnum):
    """
    COSMO-SkyMed (both generations) products types.

    The product classed are not specified here.

    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    RAW = "RAW"
    """Level 0"""

    SCS = "SCS"
    """Level 1A, Single-look Complex Slant"""

    DGM = "DGM"
    """Level 1B, Detected Ground Multi-look"""

    GEC = "GEC"
    """Level 1C, Geocoded Ellipsoid Corrected"""

    GTC = "GTC"
    """Level 1D, Geocoded Terrain Corrected"""


class CosmoProduct(SarProduct):
    """
    Class for COSMO-SkyMed (both generations) Products
    More info
    `here <https://egeos.my.salesforce.com/sfc/p/#1r000000qoOc/a/69000000JXxZ/WEEbowzi5cmY8vLqyfAAMKZ064iN1eWw_qZAgUkTtXI>`_.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        try:
            product_path = AnyPath(product_path)
            self._img_path = next(product_path.glob("*.h5"))
        except (IndexError, StopIteration) as ex:
            raise InvalidProductError(
                f"Image file (*.h5) not found in {product_path}"
            ) from ex

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        # Private attributes
        self._raw_band_regex = "*_{}_*.h5"
        self._band_folder = self.path
        self.snap_filename = self._img_path.name

        # SNAP cannot process its archive
        self.needs_extraction = True

        # Get the number of swaths of this product
        with h5netcdf.File(self._img_path, phony_dims="access") as raw_h5:
            self.nof_swaths = len(list(raw_h5.groups))

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    @cache
    def wgs84_extent(self) -> gpd.GeoDataFrame:
        """
        Get the WGS84 extent of the file before any reprojection.
        This is useful when the SAR pre-process has not been done yet.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1011117-766193"
            >>> prod = Reader().open(path)
            >>> prod.wgs84_extent()
                                                        geometry
            0  POLYGON ((108.09797 15.61011, 108.48224 15.678...

        Returns:
            gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame

        """
        root, _ = self.read_mtd()

        # Open extent coordinates
        try:

            def from_str_to_arr(geo_coord: str):
                return np.array(strings.str_to_list(geo_coord), dtype=float)[:2][::-1]

            bl_corner = from_str_to_arr(root.findtext(".//GeoCoordBottomLeft"))
            br_corner = from_str_to_arr(root.findtext(".//GeoCoordBottomRight"))
            tl_corner = from_str_to_arr(root.findtext(".//GeoCoordTopLeft"))
            tr_corner = from_str_to_arr(root.findtext(".//GeoCoordTopRight"))

            if bl_corner is None:
                raise InvalidProductError("Invalid XML: missing extent.")

            extent_wgs84 = gpd.GeoDataFrame(
                geometry=[Polygon([tl_corner, tr_corner, br_corner, bl_corner])],
                crs=vectors.WGS84,
            )
        except ValueError:

            def from_str_to_arr(geo_coord: str):
                str_list = [
                    it
                    for it in strings.str_to_list(geo_coord, additional_separator="\n")
                    if "+" not in it
                ]

                # Create tuples of 2D coords
                coord_list = []
                coord = [0.0, 0.0]
                for it_id, it in enumerate(str_list):
                    if it_id % 3 == 0:
                        # Invert lat and lon
                        coord[1] = float(it)
                    elif it_id % 3 == 1:
                        # Invert lat and lon
                        coord[0] = float(it)
                    elif it_id % 3 == 2:
                        # Z coordinates: do not store it

                        # Append the last coordinates
                        coord_list.append(coord.copy())

                        # And reinit it
                        coord = [0.0, 0.0]

                return coord_list

            bl_corners = from_str_to_arr(root.findtext(".//GeoCoordBottomLeft"))
            br_corners = from_str_to_arr(root.findtext(".//GeoCoordBottomRight"))
            tl_corners = from_str_to_arr(root.findtext(".//GeoCoordTopLeft"))
            tr_corners = from_str_to_arr(root.findtext(".//GeoCoordTopRight"))

            if not bl_corners:
                raise InvalidProductError("Invalid XML: missing extent.")

            assert (
                len(bl_corners) == len(br_corners) == len(tl_corners) == len(tr_corners)
            )

            polygons = [
                Polygon(
                    [
                        tl_corners[coord_id],
                        tr_corners[coord_id],
                        br_corners[coord_id],
                        bl_corners[coord_id],
                    ]
                )
                for coord_id in range(len(bl_corners))
            ]
            extents_wgs84 = gpd.GeoDataFrame(
                geometry=polygons,
                crs=vectors.WGS84,
            )

            extent_wgs84 = gpd.GeoDataFrame(
                geometry=[box(*extents_wgs84.total_bounds)],
                crs=vectors.WGS84,
            )

        return extent_wgs84

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()

        # DGM_B, or SCS_B -> remove last 2 characters
        prod_type = root.findtext(".//ProductType")[:-2]
        if not prod_type:
            raise InvalidProductError("mode not found in metadata!")

        self.product_type = CosmoProductType.from_value(prod_type)

        if self.product_type == CosmoProductType.DGM:
            self.sar_prod_type = SarProductType.GDRG
        elif self.product_type == CosmoProductType.SCS:
            self.sar_prod_type = SarProductType.CPLX
        else:
            raise NotImplementedError(
                f"{self.product_type.value} product type is not available for {self.name}"
            )

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1011117-766193"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 10, 28, 22, 46, 25)
            >>> prod.get_datetime(as_datetime=False)
            '20201028T224625'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             Union[str, datetime.datetime]: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//SceneSensingStartUTC")
            if not acq_date:
                raise InvalidProductError("SceneSensingStartUTC not found in metadata!")

            # Convert to datetime
            # 2020-10-28 22:46:24.808662850
            # To many milliseconds (strptime accepts max 6 digits) -> needs to be cropped
            date = datetime.strptime(acq_date[:-3], "%Y-%m-%d %H:%M:%S.%f")
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
        name = path.get_filename(root.findtext(".//ProductName"))
        if not name:
            raise InvalidProductError("ProductName not found in metadata!")

        return name

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"1001513-735093"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element DeliveryNote at 0x2454ad4ee88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        try:
            mtd_from_path = "DFDN_*.h5.xml"

            return self._read_mtd_xml(mtd_from_path)
        except InvalidProductError:
            try:
                field_map = {
                    # ProductInfo
                    "ProductName": "Product Filename",
                    # "ProductId": ,
                    "MissionId": "Mission ID",
                    # "UniqueIdentifier": ,
                    "ProductGenerationDate": "Product Generation UTC",
                    # "UserRequestId": ,
                    # "ServiceRequestName": ,
                    # ProductDefinitionData
                    "ProductType": "Product Type",
                    "SceneSensingStartUTC": "Scene Sensing Start UTC",
                    "SceneSensingStopUTC": "Scene Sensing Stop UTC",
                    # "GeoCoordTopRightEN": ,
                    "GeoCoordSceneCentre": "Scene Centre Geodetic Coordinates",
                    "SatelliteId": "Satellite ID",
                    "AcquisitionMode": "Acquisition Mode",
                    "LookSide": "Look Side",
                    "ProjectionId": "Projection ID",
                    "DeliveryMode": "Delivery Mode",
                    "AcquisitionStationId": "Acquisition Station ID",
                    # ProcessingInfo
                    # "ProcessingLevel":,
                    # ProductCharacteristics
                    "AzimuthGeometricResolution": "Azimuth Geometric Resolution",
                    "GroundRangeGeometricResolution": "Ground Range Geometric Resolution",
                }

                sbi_field_map = {
                    "GeoCoordBottomLeft": "Bottom Left Geodetic Coordinates",
                    "GeoCoordBottomRight": "Bottom Right Geodetic Coordinates",
                    "GeoCoordTopLeft": "Top Left Geodetic Coordinates",
                    "GeoCoordTopRight": "Top Right Geodetic Coordinates",
                    # "GeoCoordTopRightEN": "Top Right East-North",
                    "NearLookAngle": "Near Look Angle",
                    "FarLookAngle": "Far Look Angle",
                }

                def h5_to_str(h5_val):
                    str_val = str(h5_val)
                    str_val = str_val.replace("[", "")
                    str_val = str_val.replace("]", "")
                    return str_val

                with h5netcdf.File(self._img_path) as netcdf_ds:
                    # Create XML attributes
                    global_attr = []
                    for xml_attr, h5_attr in field_map.items():
                        try:
                            global_attr.append(
                                E(xml_attr, h5_to_str(netcdf_ds.attrs[h5_attr]))
                            )
                        except KeyError:
                            # CSG products don't have their ProductName in the h5 file...
                            if xml_attr == "ProductName":
                                global_attr.append(
                                    E(xml_attr, path.get_filename(self._img_path))
                                )

                    try:
                        # CSK products
                        sbi = netcdf_ds.groups["S01"].variables["SBI"]
                    except KeyError:
                        # CSG products
                        sbi = netcdf_ds.groups["S01"].variables["IMG"]

                    for xml_attr, h5_attr in sbi_field_map.items():
                        global_attr.append(E(xml_attr, h5_to_str(sbi.attrs[h5_attr])))

                    mtd = E.s3_global_attributes(*global_attr)
                    mtd_el = etree.fromstring(
                        etree.tostring(
                            mtd,
                            pretty_print=True,
                            xml_declaration=True,
                            encoding="UTF-8",
                        )
                    )

                return mtd_el, {}
            except KeyError:
                raise InvalidProductError(
                    "Missing the XML metadata file. Cannot read the product."
                )

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        qlk_path, qlk_exists = self._get_out_path(f"{self.condensed_name}_QLK.tif")
        if not qlk_exists:
            with rasterio.open(str(self._img_path)) as ds:
                quicklook_paths = [subds for subds in ds.subdatasets if "QLK" in subds]

            if len(quicklook_paths) == 0:
                LOGGER.warning(f"No quicklook found in {self.condensed_name}")
            else:
                rasters.write(
                    rasters.read(quicklook_paths[0]),
                    qlk_path,
                    dtype=np.uint8,
                    nodata=255,
                )
                if len(quicklook_paths) > 1:
                    LOGGER.info(
                        "For now, only the quicklook of the first swath is taken into account."
                    )

        return str(qlk_path)

    @cache
    def get_orbit_direction(self) -> OrbitDirection:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_orbit_direction().value
            "DESCENDING"

        Returns:
            OrbitDirection: Orbit direction (ASCENDING/DESCENDING)
        """
        # Get MTD XML file
        if path.is_cloud_path(self.path):
            h5_xarr_path = BytesIO(self._img_path.read_bytes())
        else:
            h5_xarr_path = str(self._img_path)

        with xr.open_dataset(
            h5_xarr_path, phony_dims="access", engine="h5netcdf"
        ) as h5_xarr:
            # Get the orbit direction
            try:
                od = OrbitDirection.from_value(getattr(h5_xarr, "Orbit Direction"))

            except TypeError:
                raise InvalidProductError("Orbit Direction not found in metadata!")

        return od

    def _pre_process_sar(self, band, pixel_size: float = None, **kwargs) -> str:
        """
        Pre-process SAR data (geocoding...)

        Args:
            band (sbn): Band to preprocess
            pixel_size (float): Pixl size
            kwargs: Additional arguments

        Returns:
            str: Band path
        """
        with h5netcdf.File(self._img_path, phony_dims="access") as raw_h5:
            if self.nof_swaths == 1:
                return super()._pre_process_sar(band, pixel_size, **kwargs)
            else:
                LOGGER.warning(
                    "Currently, SNAP doesn't handle multiswath Cosmo-SkyMed products. This is a workaround. See https://github.com/sertit/eoreader/issues/78"
                )

                # For every swath, pre-process the swath array alone
                pp_swath_path = []
                for group in raw_h5.groups:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        LOGGER.debug(f"Processing {group}")

                        # Create a mock-up of a COSMO product with only one swath and handled by SNAP
                        prod_path = os.path.join(
                            tmp_dir, f"{path.get_filename(self._img_path)}.h5"
                        )
                        with h5netcdf.File(
                            prod_path, "w", phony_dims="access"
                        ) as group_h5:
                            # Basic layer
                            group_h5.attrs.update(raw_h5.attrs)

                            # Change the swath to S01 as it is the only one read by SNAP (and is mandatory for the file to be recognized)
                            new_group = "S01"
                            group_h5.create_group(new_group)
                            group_h5.groups[new_group].attrs.update(
                                raw_h5.groups[group].attrs
                            )

                            # Copy all variables
                            for var_name in raw_h5.groups[group].variables:
                                var = raw_h5.groups[group].variables[var_name]
                                group_h5.groups[new_group].create_variable(
                                    f"/{new_group}/{var_name}",
                                    dimensions=var.dimensions,
                                    dtype=var.dtype,
                                    data=var,
                                    chunks=var.chunks,
                                )
                                group_h5.groups[new_group].variables[
                                    var_name
                                ].attrs.update(var.attrs)

                            # Copy all groups
                            for grp_name in raw_h5.groups[group].groups:
                                grp = raw_h5.groups[group].groups[grp_name]
                                if grp_name not in group_h5.groups[new_group].groups:
                                    group_h5.groups[new_group].create_group(grp_name)
                                    group_h5.groups[new_group].groups[
                                        grp_name
                                    ].attrs.update(grp.attrs)

                        # Pre-process swath
                        pp_swath_path.append(
                            super()._pre_process_sar(
                                band,
                                pixel_size,
                                prod_path=prod_path,
                                suffix=group,
                                **kwargs,
                            )
                        )

                # Merge the swaths
                LOGGER.debug("Merging the swaths")
                pp_path = os.path.join(
                    self._get_band_folder(writable=True),
                    f"{self.condensed_name}_{band.value.upper()}.tif",
                )
                # Force GTiff to be used in SNAP
                # Don't use rasters.merge_gtiff because off the predictor and the nodata...
                try:
                    pp_ds = [rasterio.open(p) for p in pp_swath_path]
                    merged_array, merged_transform = merge.merge(pp_ds, **kwargs)
                    merged_meta = pp_ds[0].meta.copy()
                    merged_meta.update(
                        {
                            "driver": "GTiff",
                            "height": merged_array.shape[1],
                            "width": merged_array.shape[2],
                            "transform": merged_transform,
                        }
                    )
                finally:
                    for ds in pp_ds:
                        ds.close()

                # Write
                # WARNING: Set nodata to 0 here as it is the value wanted by SNAP !

                # SNAP fails with classic predictor !!! Set the predictor to the default value (1) !!!
                # Caused by: javax.imageio.IIOException: Illegal value for Predictor in TIFF file
                # https://forum.step.esa.int/t/exception-found-when-reading-compressed-tif/654/7
                rasters_rio.write(
                    merged_array,
                    merged_meta,
                    pp_path,
                    nodata=self._snap_no_data,
                    predictor=SAR_PREDICTOR,
                )

                return pp_path
