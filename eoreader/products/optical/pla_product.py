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
PlanetScope products.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf>`_
and `here <https://developers.planet.com/docs/data/planetscope/>`_
for more information.
"""
import logging
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import xarray
from lxml import etree
from rasterio.enums import Resampling

from eoreader.bands.alias import ALL_CLOUDS, CIRRUS, CLOUDS, RAW_CLOUDS, SHADOWS
from eoreader.bands.bands import BandNames
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products.optical.optical_product import OpticalProduct
from eoreader.utils import DATETIME_FMT, EOREADER_NAME
from sertit import files, rasters
from sertit.misc import ListEnum
from sertit.rasters import XDS_TYPE

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class PlaInstrument(ListEnum):
    """PlanetScope instrument
    See `here <https://developers.planet.com/docs/apis/data/sensors/>`_
    for more information.
    """

    PS2 = "Dove Classic (PS2)"
    """
    Dove Classic (PS2) Instrument: Four-band frame Image with a split-frame VIS+NIR filter
    """

    PS2_SD = "Dove-R (PS2.SD)"
    """
    Dove-R (PS2.SD) Instrument:
    Four-band frame imager with butcher-block filter providing blue, green, red,and NIR stripes
    """

    PSB_SD = "SuperDove (PSB.SD)"
    """
    SuperDove (PSB.SD) Instrument:
    Eight-band frame imager with butcher-block filter providing:

    - coastal blue,
    - blue,
    - green I,
    - green II,
    - yellow,
    - red,
    - red-edge,
    - NIR stripes
    """


@unique
class PlaProductType(ListEnum):
    """PlanetScope product types (processing levels)"""

    L1B = "Basic Scene Product"
    """
    **PlanetScope Basic Scene Product (Level 1B)**

    Scaled Top of Atmosphere Radiance(at sensor) and sensor corrected product.
    This product has scene based framing and is not projected to a cartographic projection.
    Radiometric and sensor corrections are applied to the data.
    """

    L3B = "Ortho Scene Product"
    """
    **PlanetScope Ortho Scene Product (Level 3B)**

    Orthorectified, scaled Top of Atmosphere Radiance (at sensor) or Surface Reflectance image product
    suitable for analytic and visual applications.
    This product has scene based framing and projected to a cartographic projection.

    **PSScene3Band**

    PlanetScope 3-band multispectral basic and orthorectified scenes.
    This data set includes imagery from PlanetScope-0 and PlanetScope-1 sensors
    as well as full-frame and split-frame PlanetScope-2 sensors.
    Newer PSScene3Band items have a corresponding PSScene4Band item.

    Resampled to 3.0m.

    **PSScene4Band**

    PlanetScope 4-band multispectral basic and orthorectified scenes.
    This data set includes imagery from all PlanetScope sensors.
    All PSScene4Band items have a corresponding PSScene3Band item.

    Resampled to 3.0m.
    """
    """
    **PSScene (Not found anywhere else)**

    PlanetScope 8-band multispectral basic and orthorectified scenes.
    This data set includes imagery from all PlanetScope sensors.

    Naming: <acq date>_<acq time>_<acq time seconds ms>_<satellite_id>_<productLevel>_<bandProduct>.<ext>

    Asset Types:
    ortho_analytic_4b       Radiometrically-calibrated analytic image stored as 16-bit scaled radiance.
    ortho_analytic_8b       Radiometrically-calibrated analytic image stored as 16-bit scaled radiance.
    ortho_analytic_8b_sr    PlanetScope atmospherically corrected surface reflectance product.
    ortho_analytic_8b_xml   Radiometrically-calibrated analytic image metadata.
    ortho_analytic_4b_sr    PlanetScope atmospherically corrected surface reflectance product.
    ortho_analytic_4b_xml   Radiometrically-calibrated analytic image metadata.
    basic_analytic_4b       Unorthorectified radiometrically-calibrated analytic image stored as 16-bit scaled radiance.
    basic_analytic_8b       Unorthorectified radiometrically-calibrated analytic image stored as 16-bit scaled radiance.
    basic_analytic_8b_xml   Unorthorectified radiometrically-calibrated analytic image metadata
    basic_analytic_4b_rpc   RPC for unorthorectified analytic image stored as 12-bit digital numbers.
    basic_analytic_4b_xml   Unorthorectified radiometrically-calibrated analytic image metadata.
    basic_udm2              Unorthorectified usable data mask (Cloud 2.0) Read more about this new asset here.
    ortho_udm2              Usable data mask (Cloud 2.0)
    ortho_visual            Visual image with color-correction
    """

    L3A = "Ortho Tile Product"
    """
    **PlanetScope Ortho Tile Product (Level 3A)**

    Radiometric and sensor corrections applied to the data.
    Imagery is orthorectified and projected to a UTM projection.

    **PSOrthoTile**

    PlanetScope Ortho Tiles as 25 km x 25 km UTM tiles. This data set includes imagery from all PlanetScope sensors.
    Resampled to 3.125m.

    Naming: <strip_id>_<tile_id>_<acquisition date>_<satellite_id>_<bandProduct>.<extension>

    Product band order:

    - Band 1 = Blue
    - Band 2 = Green
    - Band 3 = Red
    - Band 4 = Near-infrared (analytic products only)

    Analytic 5B Product band order:

    - Band 1 = Blue
    - Band 2 = Green
    - Band 3 = Red
    - Band 4 = Red-Edge
    - Band 5 = Near-infrared
    """


class PlaProduct(OpticalProduct):
    """
    Class of PlanetScope products.
    See `here <https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf>`_
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    # def __init__(
    #         self, product_path: str, archive_path: str = None, output_path=None
    # ) -> None:
    #     self.ortho_path = None
    #     """
    #     Orthorectified path.
    #     Can be set to use manually orthorectified data, especially useful for VHR data on steep terrain.
    #     """
    #
    #     # Initialization from the super class
    #     super().__init__(product_path, archive_path, output_path)

    def _post_init(self) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self.needs_extraction = False

        # Ortho Tiles
        if self.product_type == PlaProductType.L3A:
            self.tile_name = self.split_name[1]  # TODO: test that !

        # Post init done by the super class
        super()._post_init()

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # Ortho Tiles
        if self.product_type == PlaProductType.L3A:
            return 3.125
        # Ortho Scene
        else:
            return 3.0

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Manage product type
        prod_type = root.findtext(f".//{nsmap['eop']}productType")
        if not prod_type:
            raise InvalidProductError(
                "Cannot find the product type in the metadata file"
            )

        # Set correct product type
        self.product_type = getattr(PlaProductType, prod_type)
        if self.product_type == PlaProductType.L1B:
            raise NotImplementedError(
                f"Basic Scene Product are not managed for Planet products {self.path}"
            )
        elif self.product_type == PlaProductType.L3A:
            LOGGER.warning(
                f"Ortho Tile Product are not well tested for Planet products {self.path}."
                f"Use it at your own risk !"
            )

        # Manage platform
        instr_node = root.find(f".//{nsmap['eop']}Instrument")
        instrument = instr_node.findtext(f"{nsmap['eop']}shortName")

        if not instrument:
            raise InvalidProductError("Cannot find the platform in the metadata file")

        # Set correct platform
        self.instrument = getattr(PlaInstrument, instrument.replace(".", "_"))

        # Manage bands of the product
        nof_bands = len(
            [band for band in root.iterfind(f".//{nsmap['ps']}bandSpecificMetadata")]
        )
        if nof_bands == 3:
            self.band_names.map_bands({obn.BLUE: 1, obn.GREEN: 2, obn.RED: 3})
        elif nof_bands == 4:
            self.band_names.map_bands(
                {obn.BLUE: 1, obn.GREEN: 2, obn.RED: 3, obn.NIR: 4, obn.NARROW_NIR: 4}
            )
        elif nof_bands == 5:
            self.band_names.map_bands(
                {
                    obn.BLUE: 1,
                    obn.GREEN: 2,
                    obn.RED: 3,
                    obn.VRE_1: 4,
                    obn.NIR: 5,
                    obn.NARROW_NIR: 5,
                }
            )
        elif nof_bands == 8:
            raise NotImplementedError(
                f"8 Band Scenes are not yet implemented in EOReader: {self.path}"
            )
        else:
            raise InvalidProductError(
                f"Unusual number of bands ({nof_bands}) for {self.path}. "
                f"Please check the validity of your product"
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
        nodata = self._load_nodata()

        # Vectorize the nodata band (rasters_rio is faster)
        footprint = rasters.vectorize(
            nodata, values=1, keep_values=False, dissolve=True
        ).convex_hull

        return gpd.GeoDataFrame(geometry=footprint.geometry, crs=footprint.crs)

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
        # 20200624-105726-971
        split_name = self.split_name

        date = f"{split_name[0]}T{split_name[1]}"

        if as_datetime:
            date = datetime.strptime(date, DATETIME_FMT)

        return date

    def get_band_paths(
        self, band_list: list, resolution: float = None, size=None
    ) -> dict:
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
            size:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            band_paths[band] = self._get_path(
                "AnalyticMS", "tif", invalid_lookahead="_DN_"
            )

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
        # Nodata
        no_data_mask = self._load_nodata(resolution=resolution, size=size).data

        # Dubious pixels mapping
        dubious_bands = {
            key: val + 1 for key, val in self.band_names.items() if val is not None
        }
        udm = self.open_mask("UNUSABLE", resolution, size)
        dubious_mask = rasters.read_bit_array(udm, dubious_bands[band])

        # Combine masks
        mask = no_data_mask | dubious_mask

        # -- Merge masks
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
        Get PlanetScope products condensed name ({date}_PLA_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.platform.name}_{self.product_type.name}"

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
        root, nsmap = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            elev_angle = float(
                root.findtext(f".//{nsmap['opt']}illuminationElevationAngle")
            )
            azimuth_angle = float(
                root.findtext(f".//{nsmap['opt']}illuminationAzimuthAngle")
            )
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
        mtd_from_path = "metadata*.xml"
        mtd_archived = "metadata.*\.xml"

        return self._read_mtd(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this products has the specified cloud band ?
        """
        # NOTE: CIRRUS == HEAVY HAZE

        # FROM DOCUMENTATION: https://developers.planet.com/docs/data/udm-2/
        # Percent of heavy haze values in dataset.
        # Heavy haze values represent scene content areas (non-blackfilled) that contain thin low altitude clouds,
        # higher altitude cirrus clouds, soot and dust which allow fair recognition of land cover features,
        # but not having reliable interpretation of the radiometry or surface reflectance.
        return True

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
                if res_id == ALL_CLOUDS:
                    band_dict[res_id] = self._create_mask(
                        def_xarr.rename(ALL_CLOUDS.name),
                        (
                            self.open_mask("CLOUD", resolution, size).data
                            & self.open_mask("SHADOW", resolution, size).data
                            & self.open_mask("HEAVY_HAZE", resolution, size).data
                        ),
                        nodata,
                    )
                elif res_id == SHADOWS:
                    band_dict[res_id] = self._create_mask(
                        def_xarr.rename(SHADOWS.name),
                        self.open_mask("SHADOW", resolution, size).data,
                        nodata,
                    )
                elif res_id == CLOUDS:
                    band_dict[res_id] = self._create_mask(
                        def_xarr.rename(CLOUDS.name),
                        self.open_mask("CLOUD", resolution, size).data,
                        nodata,
                    )
                elif res_id == CIRRUS:
                    band_dict[res_id] = self._create_mask(
                        def_xarr.rename(CIRRUS.name),
                        self.open_mask("HEAVY_HAZE", resolution, size).data,
                        nodata,
                    )
                elif res_id == RAW_CLOUDS:
                    band_dict[res_id] = rasters.read(
                        self._get_path("udm2", "tif"), resolution, size
                    )
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Planet: {res_id}"
                    )

        return band_dict

    def open_mask(
        self,
        mask_id: str,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> Union[xarray.DataArray, None]:
        """
        Open a Planet UDM2 (Usable Data Mask) mask, band by band, as a xarray.
        Returns None if the mask is not available.

        Do not open cloud mask with this function. Use `load` instead.

        See `here <https://developers.planet.com/docs/data/udm-2/>`_ for more
        information.

        Accepted mask IDs:

        - `CLEAR`:      Band 1     Clear map        [0, 1]  0: not clear, 1: clear
        - `SNOW`:       Band 2     Snow map         [0, 1]  0: no snow or ice, 1: snow or ice
        - `SHADOW`:     Band 3     Shadow map       [0, 1]  0: no shadow, 1: shadow
        - `LIGHT_HAZE`: Band 4     Light haze map   [0, 1]  0: no light haze, 1: light haze
        - `HEAVY_HAZE`: Band 5     Heavy haze map   [0, 1]  0: no heavy haze, 1: heavy haze
        - `CLOUD`:      Band 6     Cloud map        [0, 1]  0: no cloud, 1: cloud
        - `CONFIDENCE`: Band 7     Confidence map   [0-100] %age value: per-pixel algorithmic confidence in classif
        - `UNUSABLE`:   Band 8     Unusable pixels  --      Equivalent to the UDM asset

        .. code-block:: python

            >>> from eoreader.bands.alias import *
            >>> from eoreader.reader import Reader
            >>> path = r"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip"
            >>> prod = Reader().open(path)
            >>> prod.open_mask("EDG", GREEN)
            array([[[0, ..., 0]]], dtype=uint8)

        Args:
            mask_id: Mask ID
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            Union[xarray.DataArray, None]: Mask array

        """
        band_mapping = {
            "CLEAR": 1,
            "SNOW": 2,
            "SHADOW": 3,
            "LIGHT_HAZE": 4,
            "HEAVY_HAZE": 5,
            "CLOUD": 6,
            "CONFIDENCE": 7,
            "UNUSABLE": 8,
        }

        assert mask_id in band_mapping
        mask_path = self._get_path("udm2", "tif")

        # Open mask band
        mask = rasters.read(
            mask_path,
            resolution=resolution,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            indexes=[band_mapping[mask_id]],
        )

        return mask.astype(np.uint8)

    def _load_nodata(
        self,
        resolution: float = None,
        size: Union[list, tuple] = None,
    ) -> Union[xarray.DataArray, None]:
        """
        Load nodata (unimaged pixels) as a numpy array.

        See
        `here <https://earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf>`_
        (unusable data mask) for more information.

        Args:
            resolution (float): Band resolution in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided.

        Returns:
            Union[xarray.DataArray, None]: Nodata array

        """
        udm = self.open_mask("UNUSABLE", resolution, size)
        nodata = udm.copy(data=rasters.read_bit_array(udm, 0))
        return nodata.rename("NODATA")

    def _get_path(self, filename: str, extension: str, invalid_lookahead=None) -> str:
        """
        Get either the archived path of the normal path of an asset

        Args:
            filename (str): Filename with wildcards
            extension (str): Extension

        Returns:
            str: Path

        """
        path = ""
        try:
            if self.is_archived:
                path = files.get_archived_rio_path(
                    self.path, f".*{filename}\w*[_]*\.{extension}"
                )
            else:
                paths = list(self.path.glob(f"**/*{filename}*.{extension}"))
                if invalid_lookahead:
                    paths = [
                        path for path in paths if invalid_lookahead not in str(path)
                    ]
                path = paths[0]
        except (FileNotFoundError, IndexError):
            LOGGER.warning(
                f"No file corresponding to *{filename}*.{extension} found in {self.path}"
            )

        return path
