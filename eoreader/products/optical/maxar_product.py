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
"""
Maxar satellites (GeoEye, WorldViews...) class.
See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
for more information.
"""

import logging
import os
from abc import abstractmethod
from collections import namedtuple
from datetime import datetime
from enum import unique
from typing import Union

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio import crs as riocrs
from sertit import geometry, path, rasters, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType
from sertit.vectors import EPSG_4326
from shapely.geometry import Polygon

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    BLUE,
    CA,
    GREEN,
    NARROW_NIR,
    NIR,
    PAN,
    RED,
    VRE_1,
    VRE_2,
    VRE_3,
    WV,
    YELLOW,
    BandNames,
    SpectralBand,
)
from eoreader.bands.band_names import DEEP_BLUE
from eoreader.env_vars import FIX_MAXAR
from eoreader.exceptions import InvalidProductError
from eoreader.products import VhrProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.reader import Constellation
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)

_MAXAR_BAND_MTD = {
    NIR: "N",
    NARROW_NIR: "N",
    RED: "R",
    GREEN: "G",
    BLUE: "B",
    WV: "N2",
    VRE_1: "RE",
    VRE_2: "RE",
    VRE_3: "RE",
    YELLOW: "Y",
    CA: "C",
    PAN: "P",
}


@unique
class LegionPlatform(ListEnum):
    """
    Worldview Legion platform.

    Resources:

    - https://resources.maxar.com/data-sheets/worldview-legion-2
    - https://resources.maxar.com/white-papers/radiometric-use-of-worldview-legion-1-and-worldview-legion-2-imagery
    """

    LG01 = "LG01"
    """
    Worldview Legion platform number 1
    """

    LG02 = "LG02"
    """
    Worldview Legion platform number 2
    """

    LG03 = "LG03"
    """
    Worldview Legion platform number 3
    """

    LG04 = "LG04"
    """
    Worldview Legion platform number 4
    """

    LG05 = "LG05"
    """
    Worldview Legion platform number 5
    """

    LG06 = "LG06"
    """
    Worldview Legion platform number 6
    """

    LG07 = "LG07"
    """
    Worldview Legion platform number 7
    """

    LG08 = "LG08"
    """
    Worldview Legion platform number 8
    """


GainOffset = namedtuple("GainOffset", ["gain", "offset"], defaults=[1.0, 0.0])
LegionPlatformTuple = namedtuple(
    "LegionPlatform",
    ["LG01", "LG02", "LG03", "LG04", "LG05", "LG06", "LG07", "LG08"],
    defaults=[np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
)
_MAXAR_GAIN_OFFSET = {
    Constellation.WVLG: {
        PAN: GainOffset(gain=1.0, offset=0.0),
        CA: GainOffset(gain=1.0, offset=0.0),
        BLUE: GainOffset(gain=1.0, offset=0.0),
        GREEN: GainOffset(gain=1.0, offset=0.0),
        YELLOW: GainOffset(gain=1.0, offset=0.0),
        RED: GainOffset(gain=1.0, offset=0.0),
        VRE_1: GainOffset(gain=1.0, offset=0.0),
        VRE_2: GainOffset(gain=1.0, offset=0.0),
        VRE_3: GainOffset(gain=1.0, offset=0.0),
        NIR: GainOffset(gain=1.0, offset=0.0),
        NARROW_NIR: GainOffset(gain=1.0, offset=0.0),
        WV: GainOffset(gain=1.0, offset=0.0),
    },  # https://resources.maxar.com/white-papers/radiometric-use-of-worldview-legion-1-and-worldview-legion-2-imagery
    Constellation.GE01: {
        PAN: GainOffset(gain=1.001, offset=0.0),
        BLUE: GainOffset(gain=1.041, offset=0.0),
        GREEN: GainOffset(gain=0.972, offset=0.0),
        RED: GainOffset(gain=0.979, offset=0.0),
        NIR: GainOffset(gain=0.951, offset=0.0),
        NARROW_NIR: GainOffset(gain=0.951, offset=0.0),
    },  # 2018v0
    Constellation.WV02: {
        PAN: GainOffset(gain=0.949, offset=-5.523),
        CA: GainOffset(gain=1.203, offset=-11.839),
        BLUE: GainOffset(gain=1.002, offset=-9.835),
        GREEN: GainOffset(gain=0.953, offset=-7.218),
        YELLOW: GainOffset(gain=0.946, offset=-5.675),
        RED: GainOffset(gain=0.955, offset=-5.046),
        VRE_1: GainOffset(gain=0.980, offset=-6.114),
        VRE_2: GainOffset(gain=0.980, offset=-6.114),
        VRE_3: GainOffset(gain=0.980, offset=-6.114),
        NIR: GainOffset(gain=0.966, offset=-5.096),
        NARROW_NIR: GainOffset(gain=0.966, offset=-5.096),
        WV: GainOffset(gain=1.01, offset=-4.059),
    },  # 2018v0
    Constellation.WV03: {
        PAN: GainOffset(gain=0.955, offset=-5.505),
        CA: GainOffset(gain=0.938, offset=-13.099),
        BLUE: GainOffset(gain=0.946, offset=-9.409),
        GREEN: GainOffset(gain=0.958, offset=-7.771),
        YELLOW: GainOffset(gain=0.979, offset=-5.489),
        RED: GainOffset(gain=0.969, offset=-4.579),
        VRE_1: GainOffset(gain=1.027, offset=-5.552),
        VRE_2: GainOffset(gain=1.027, offset=-5.552),
        VRE_3: GainOffset(gain=1.027, offset=-5.552),
        NIR: GainOffset(gain=0.977, offset=-6.508),
        NARROW_NIR: GainOffset(gain=0.977, offset=-6.508),
        WV: GainOffset(gain=1.007, offset=-3.699),
    },  # 2018v0
    Constellation.WV04: {
        PAN: GainOffset(gain=1.0, offset=0.0),
        BLUE: GainOffset(gain=1.0, offset=0.0),
        GREEN: GainOffset(gain=1.0, offset=0.0),
        RED: GainOffset(gain=1.0, offset=0.0),
        NIR: GainOffset(gain=1.0, offset=0.0),
        NARROW_NIR: GainOffset(gain=1.0, offset=0.0),
    },  # 2017v0
    Constellation.QB02: {
        PAN: GainOffset(gain=0.870, offset=-1.491),
        BLUE: GainOffset(gain=1.105, offset=-2.820),
        GREEN: GainOffset(gain=1.071, offset=-3.338),
        RED: GainOffset(gain=1.060, offset=-2.954),
        NIR: GainOffset(gain=1.020, offset=-4.722),
        NARROW_NIR: GainOffset(gain=1.020, offset=-4.722),
    },  # 2016v0.Int
    Constellation.WV01: {
        PAN: GainOffset(gain=1.016, offset=-1.824),
    },  # 2016v0.Int
}
"""
The TDI specific abscalfactor and effectiveBandwidth are delivered with the imagery in the metadata file. The
digital number, DN, is the pixel value found in the imagery. The Gain and Offset are the absolute radiometric
calibration band dependent adjustment factors that are given in Table 1. Note that these are not necessarily
stagnant values and they are revisited annually.

Only using last calibration as the Maxar sensors have been found to be very stable throughout their lifetime.

See `here <https://resources.maxar.com/white-papers/absolute-radiometric-calibration-white-paper>`_ for the values.
"""

_MAXAR_E0 = {
    Constellation.WVLG: {
        PAN: LegionPlatformTuple(LG01=1627.669, LG02=1630.911),
        CA: LegionPlatformTuple(LG01=1756.808, LG02=1748.182),
        BLUE: LegionPlatformTuple(LG01=2020.761, LG02=2021.502),
        GREEN: LegionPlatformTuple(LG01=1877.814, LG02=1878.494),
        YELLOW: LegionPlatformTuple(LG01=1750.532, LG02=1745.874),
        RED: LegionPlatformTuple(LG01=1551.612, LG02=1552.111),
        VRE_1: LegionPlatformTuple(LG01=1413.868, LG02=1411.140),
        VRE_2: LegionPlatformTuple(LG01=1298.429, LG02=1292.678),
        VRE_3: LegionPlatformTuple(LG01=1298.429, LG02=1292.678),
        NIR: LegionPlatformTuple(LG01=1047.560, LG02=1049.999),
        NARROW_NIR: LegionPlatformTuple(LG01=1047.560, LG02=1049.999),
    },  # https://resources.maxar.com/white-papers/radiometric-use-of-worldview-legion-1-and-worldview-legion-2-imagery
    Constellation.GE01: {
        PAN: 1610.73,
        BLUE: 1993.18,
        GREEN: 1828.83,
        RED: 1491.49,
        NIR: 1022.58,
        NARROW_NIR: 1022.58,
    },
    Constellation.WV02: {
        PAN: 1571.36,
        CA: 1773.81,
        BLUE: 2007.27,
        GREEN: 1829.62,
        YELLOW: 1701.85,
        RED: 1538.85,
        VRE_1: 1346.09,
        VRE_2: 1346.09,
        VRE_3: 1346.09,
        NIR: 1053.21,
        NARROW_NIR: 1053.21,
        WV: 856.599,
    },
    Constellation.WV03: {
        PAN: 1574.41,
        CA: 1757.89,
        BLUE: 2004.61,
        GREEN: 1830.18,
        YELLOW: 1712.07,
        RED: 1535.33,
        VRE_1: 1348.08,
        VRE_2: 1348.08,
        VRE_3: 1348.08,
        NIR: 1055.94,
        NARROW_NIR: 1055.94,
        WV: 858.77,
    },
    Constellation.WV04: {
        PAN: 1608.01,
        BLUE: 2009.45,
        GREEN: 1831.88,
        RED: 1492.12,
        NIR: 937.8,
        NARROW_NIR: 937.8,
    },
    Constellation.QB02: {
        PAN: 1370.92,
        BLUE: 1949.59,
        GREEN: 1823.64,
        RED: 1553.78,
        NIR: 1102.85,
        NARROW_NIR: 1102.85,
    },
    Constellation.WV01: {
        PAN: 1478.62,
    },
}
"""
Esun is the band-averaged Solar exoatmospheric irradiance @1AU (see Slide 7&8). DG calibration team uses the Thuillier 2003 solar curve for their calculations.
See `here <https://resources.maxar.com/white-papers/absolute-radiometric-calibration-white-paper>`_ for the values.
"""


@unique
class MaxarProductType(ListEnum):
    """
    Maxar product types.

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 26)
    """

    Basic = "System Ready"
    """
    Basic Imagery, also known as System-Ready data.
    Corresponds to a Level 1B.

    Not handled by EOReader.
    """

    Standard = "View Ready"
    """
    Standard Imagery, also known as View-Ready data (previously Ortho-Ready Standard).
    Corresponds to a Level 2A (Standard2A or ORStandard2A)
    """

    Ortho = "Map Ready"
    """
    Orthorectified Standard Imagery, also known as Map-Ready data (previously Standard Imagery).
    Corresponds to a Level 3

    NMAS mapping scale of the Orthorectified Product:

    - Level 3A: “1:50,000”
    - Level 3D: “1:12,000”
    - Level 3E: “1:10,000”
    - Level 3F: “1:5,000”
    - Level 3G: “1:4,800”
    - Level 3X: “Custom”
    """

    DEM = "DEM"
    """
    DEM product type.

    Not handled by EOReader.
    """

    Stereo = "Stereo"
    """
    Stereo product type.

    Not handled by EOReader.
    """


@unique
class MaxarBandId(ListEnum):
    """
    Maxar products band ID

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 24)
    """

    P = "Panchromatic"
    """
    Panchromatic
    """

    Multi = "Multi Spectral"
    """
    All VNIR Multi-spectral bands (4 for QB02,GE01 and 8 for WV02, WV03)
    """

    N = "NIR"
    """
    Near-InfraRed
    """

    R = "RED"
    """
    Red
    """

    G = "GREEN"
    """
    Green
    """

    B = "BLUE"
    """
    Blue
    """

    RGB = "RGB"
    """
    Red + Green + Blue
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    NRG = "NRG"
    """
    Near-IR + Red + Green
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    BGRN = "BGRN Pan-Sharpened"
    """
    Blue + Green + Red + Near-IR
    Pan-sharpened color images, stored at the panchromatic spatial resolution.
    """

    # Only for WorldView-2 and WorldView-3
    N2 = "NIR2"
    """
    NIR2
    """

    RE = "Red-Edge"
    """
    NIR2
    """

    Y = "Yellow"
    """
    Yellow
    """

    C = "Coastal"
    """
    Coastal
    """

    MS1 = "Multi Spectral 1"
    """
    First 4 bands (N,R,G,B)
    """

    MS2 = "Multi Spectral 2"
    """
    Second 4 bands (N2,RE,Y,C)
    """


@unique
class MaxarSatId(ListEnum):
    """
    Maxar products satellite IDs

    See `here <https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/106/ISD_External.pdf>`_ (p. 29)
    """

    QB02 = "Quickbird"
    """
    Quickbird
    """

    GE01 = "GeoEye-1"
    """
    GeoEye-1
    """

    WV01 = "WorldView-1"
    """
    WorldView-1
    """

    WV02 = "WorldView-2"
    """
    WorldView-2
    """

    WV03 = "WorldView-3"
    """
    WorldView-3
    """

    WV04 = "WorldView-4"
    """
    WorldView-4
    """

    WVLG = "WorldView Legion"
    """
    WorldView Legion
    """


class MaxarProduct(VhrProduct):
    """
    Super Class of Maxar products.
    See `here <https://earth.esa.int/eogateway/documents/20142/37627/DigitalGlobe-Standard-Imagery.pdf>`_
    for more information.
    """

    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        self._version = None
        self._platform = None

        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.DN
        self._has_cloud_cover = True
        self.needs_extraction = False
        self._proj_prod_type = [MaxarProductType.Standard]

        # Not exact resolutions for this specific product, but the usual ones for CEMS, set by default
        # This is only used for GSD in band mapping
        # TODO: -> maybe update Maxar default resolutions to real values for each constellation? Or best available?
        self._pan_res = 0.5
        self._ms_res = 2.0

        # Exact best resolutions, but the data are resampled on delivery
        # WV LG: PAN = 0.29 m, MS = 1.16 m
        # WV4: PAN = 0.31 m, MS = 1.24 m
        # WV3: PAN = 0.34 m, MS = 1.24 m, SWIR = 3.70 m
        # WV2: PAN = 0.46 m, MS = 1.8 m
        # WV1: PAN = 0.50 m
        # GE01: PAN = 0.41 m, MS = 1.64 m
        # QB02: PAN = 0.61 m, MS = 2.4 m

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _set_instrument(self) -> None:
        """
        Set instrument

        WV01: https://earth.esa.int/eogateway/missions/worldview-1
        WV02: https://earth.esa.int/eogateway/missions/worldview-2
        WV03: https://earth.esa.int/eogateway/missions/worldview-3
        WV04: https://space.oscar.wmo.int/satellites/view/worldview_4
        Quickbird: https://earth.esa.int/eogateway/missions/quickbird-2
        GeoEye: https://earth.esa.int/eogateway/missions/geoeye-1
        WV Legion: https://database.eohandbook.com/database/missionsummary.aspx?missionID=1011
        """
        if self.constellation == Constellation.WV01:
            # WorldView-60 camera (WV60)
            self.instrument = "WV60"
        elif self.constellation in [Constellation.WV02, Constellation.WV03]:
            # WorldView-110 camera (WV110)
            self.instrument = "WV110"
        elif self.constellation == Constellation.WV04:
            self.instrument = "SpaceView-110 camera"
        elif self.constellation == Constellation.QB02:
            # Ball Global Imaging System 2000
            self.instrument = "BGIS-2000"
        elif self.constellation == Constellation.GE01:
            # GeoEye Imaging System (GIS)
            self.instrument = "GIS"
        elif self.constellation == Constellation.WVLG:
            self.instrument = "WorldView Legion Camera"

    def _get_constellation(self) -> Constellation:
        """Getter of the constellation"""
        # Maxar products are all similar, we must check into the metadata to know the constellation
        root, _ = self.read_mtd()
        constellation_id = root.findtext(".//IMAGE/SATID")
        if not constellation_id:
            raise InvalidProductError("Cannot find SATID in the metadata file")
        if "LG" in constellation_id:
            self._platform = LegionPlatform(constellation_id)
            constellation_id = MaxarSatId.WVLG.name
        else:
            constellation_id = getattr(MaxarSatId, constellation_id).name
        return getattr(Constellation, constellation_id)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        # Band combination
        root, _ = self.read_mtd()
        band_combi = root.findtext(".//IMD/BANDID")
        if not band_combi:
            raise InvalidProductError("Cannot find BANDID in the metadata file")
        self.band_combi = getattr(MaxarBandId, band_combi)

        # Fix shapes
        self._fix_shapes(root)

        # Platform
        if self.constellation == Constellation.WVLG:
            if "LG01" in self.name:
                self._platform = LegionPlatform.LG01
            elif "LG02" in self.name:
                self._platform = LegionPlatform.LG02
            # TODO
        else:
            self._platform = self.constellation

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _fix_shapes(self, root):
        """"""

        # BUGGED TIL with GDAL
        # Sometimes, TIL driver fails to open correctly the different tiles
        # See https://github.com/sertit/eoreader/issues/242

        # To check that, it can be useful to ensure that the default width and height corresponds to the tiles aggregated width and height
        # Shape from IMD
        imd_rows = int(root.findtext(".//IMD/NUMROWS"))
        imd_cols = int(root.findtext(".//IMD/NUMCOLUMNS"))

        # Shape from TIL
        til_rows = max(
            [
                int(row_offset.text)
                for row_offset in root.iterfind(".//TIL/TILE/LLROWOFFSET")
            ]
        )
        til_cols = max(
            [
                int(col_offset.text)
                for col_offset in root.iterfind(".//TIL/TILE/URCOLOFFSET")
            ]
        )

        # Sometimes it's LLROWOFFSET and URCOLOFFSET, sometimes it's LLROWOFFSET + 1 and URCOLOFFSET + 1...
        if abs(imd_rows - til_rows) > 1 or abs(imd_cols - til_cols) > 1:
            if os.environ.get(FIX_MAXAR, "1") != "0":
                LOGGER.warning(
                    f"Your Maxar product is probably corrupted. "
                    f"Shapes retrieved from metadata are incoherent: {imd_rows}x{imd_cols} in .IMD vs {til_rows}x{til_cols} in .TIL. (see https://github.com/sertit/eoreader/issues/242) "
                    "WORKAROUND: The IMD file of this product will be fixed inside the raw product and the old one copied into the working directory. "
                    "Please double-check the outputs for this product."
                )
                # Copy .IMD file
                if self.is_archived:
                    imd_fn = f"{self.name}.IMD"
                    imd_file = self._read_archived_file(".*IMD")
                else:
                    imd_fn = next(self.path.glob("*.IMD"))
                    with open(imd_fn) as f:
                        imd_file = f.read()

                # Copy old file
                imd_copy, _ = self._get_out_path(f"{self.name}.IMD")
                with open(str(imd_copy), "w") as f:
                    f.write(imd_file)

                # Update to create new IMD file
                imd_file = imd_file.replace(
                    f"numRows = {imd_rows};", f"numRows = {til_rows};"
                ).replace(f"numColumns = {imd_cols};", f"numColumns = {til_cols};")

                # Don't try to fix it if cloud-based or archived
                if self.is_archived:
                    raise NotImplementedError(
                        f"For now, the workaround is to manually copy the corrected IMD file ({imd_copy}) "
                        f"into your archived product ({self.path}) and re-run the job. "
                        f"(there is currently no optimized way for overwriting zip files in Python)"
                    )
                elif path.is_path(path):
                    raise NotImplementedError(
                        f"For now, the workaround is to manually copy the corrected IMD file ({imd_copy}) "
                        f"into your cloud-stored product ({self.path}) and re-run the job."
                    )

                # Replace file
                with open(str(imd_fn), "w") as f:
                    f.write(imd_file)
            else:
                raise InvalidProductError(
                    f"This product ({self.name}) is corrupted."
                    "\nThe shapes from the metadata are incoherent between .TIL and .IMD files. "
                    "The best thing to do is to manually create a mosaic from all embedded .TIF files and pass it as a CustomStack to EOReader. "
                    "\nIf you want to have a stack in reflectance, remember to apply the corrections on each subproduct separately before creating the mosaic."
                )

    @abstractmethod
    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """

        # Band combination
        root, _ = self.read_mtd()
        gsd = root.findtext(".//MAP_PROJECTED_PRODUCT/PRODUCTGSD")
        if not gsd:
            raise InvalidProductError(
                "Cannot find PRODUCTGSD type in the metadata file"
            )
        self.pixel_size = float(gsd)

    def _get_spectral_bands(self) -> dict:
        """
        https://docs.sentinel-hub.com/api/latest/static/files/data/maxar/world-view/resources/brochures/EUSI_Satellite_Booklet_digital.pdf
        https://resources.maxar.com/optical-imagery/multispectral-reference-guide

        Returns:
            dict: Maxar spectral bands
        """
        # Create spectral bands
        if self.constellation == Constellation.WVLG:
            spectral_bands = {
                "pan": SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self._pan_res,
                        WV_MIN: 450,
                        WV_MAX: 800,
                    },
                ),
                "ca": SpectralBand(
                    eoreader_name=CA,
                    **{
                        NAME: "COASTAL BLUE",
                        ID: 1,
                        GSD: self._ms_res,
                        WV_MIN: 400,
                        WV_MAX: 450,
                    },
                ),
                "blue": SpectralBand(
                    eoreader_name=BLUE,
                    **{
                        NAME: "BLUE",
                        ID: 2,
                        GSD: self._ms_res,
                        WV_MIN: 450,
                        WV_MAX: 510,
                    },
                ),
                "green": SpectralBand(
                    eoreader_name=GREEN,
                    **{
                        NAME: "GREEN",
                        ID: 3,
                        GSD: self._ms_res,
                        WV_MIN: 510,
                        WV_MAX: 580,
                    },
                ),
                "yellow": SpectralBand(
                    eoreader_name=YELLOW,
                    **{
                        NAME: "YELLOW",
                        ID: 7,
                        GSD: self._ms_res,
                        WV_MIN: 585,
                        WV_MAX: 625,
                    },
                ),
                "red": SpectralBand(
                    eoreader_name=RED,
                    **{NAME: "RED", ID: 5, GSD: self._ms_res, WV_MIN: 630, WV_MAX: 690},
                ),
                "vre1": SpectralBand(
                    eoreader_name=VRE_1,
                    **{
                        NAME: "RED EDGE 1",
                        ID: 6,
                        GSD: self._ms_res,
                        WV_MIN: 695,
                        WV_MAX: 715,
                    },
                ),
                "vre2": SpectralBand(
                    eoreader_name=VRE_2,
                    **{
                        NAME: "RED EDGE 2",
                        ID: 7,
                        GSD: self._ms_res,
                        WV_MIN: 730,
                        WV_MAX: 750,
                    },
                ),
                "nir": SpectralBand(
                    eoreader_name=NIR,
                    **{
                        NAME: "NIR1",
                        ID: 8,
                        GSD: self._ms_res,
                        WV_MIN: 770,
                        WV_MAX: 895,
                    },
                ),
            }
        elif self.constellation in [Constellation.WV02, Constellation.WV03]:
            spectral_bands = {
                "pan": SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self._pan_res,
                        WV_MIN: 450,
                        WV_MAX: 800,
                    },
                ),
                "ca": SpectralBand(
                    eoreader_name=CA,
                    **{
                        NAME: "COASTAL BLUE",
                        ID: 1,
                        GSD: self._ms_res,
                        WV_MIN: 400,
                        WV_MAX: 450,
                    },
                ),
                "deep_blue": SpectralBand(
                    eoreader_name=DEEP_BLUE,
                    **{
                        NAME: "DEEP BLUE",
                        ID: 1,
                        GSD: self._ms_res,
                        WV_MIN: 400,
                        WV_MAX: 450,
                    },
                ),
                "blue": SpectralBand(
                    eoreader_name=BLUE,
                    **{
                        NAME: "BLUE",
                        ID: 2,
                        GSD: self._ms_res,
                        WV_MIN: 450,
                        WV_MAX: 510,
                    },
                ),
                "green": SpectralBand(
                    eoreader_name=GREEN,
                    **{
                        NAME: "GREEN",
                        ID: 3,
                        GSD: self._ms_res,
                        WV_MIN: 510,
                        WV_MAX: 580,
                    },
                ),
                "yellow": SpectralBand(
                    eoreader_name=YELLOW,
                    **{
                        NAME: "YELLOW",
                        ID: 7,
                        GSD: self._ms_res,
                        WV_MIN: 585,
                        WV_MAX: 625,
                    },
                ),
                "red": SpectralBand(
                    eoreader_name=RED,
                    **{NAME: "RED", ID: 5, GSD: self._ms_res, WV_MIN: 630, WV_MAX: 690},
                ),
                "vre": SpectralBand(
                    eoreader_name=VRE_1,
                    **{
                        NAME: "RED EDGE",
                        ID: 6,
                        GSD: self._ms_res,
                        WV_MIN: 705,
                        WV_MAX: 745,
                    },
                ),
                "nir": SpectralBand(
                    eoreader_name=NIR,
                    **{
                        NAME: "NIR1",
                        ID: 7,
                        GSD: self._ms_res,
                        WV_MIN: 770,
                        WV_MAX: 895,
                    },
                ),
                "wv": SpectralBand(
                    eoreader_name=WV,
                    **{
                        NAME: "NIR2",
                        ID: 8,
                        GSD: self._ms_res,
                        WV_MIN: 860,
                        WV_MAX: 1040,
                    },
                ),
            }
        elif self.constellation == Constellation.QB02:
            spectral_bands = {
                "pan": SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self._pan_res,
                        WV_MIN: 405,
                        WV_MAX: 1053,
                    },
                ),
                "blue": SpectralBand(
                    eoreader_name=BLUE,
                    **{
                        NAME: "BLUE",
                        ID: 1,
                        GSD: self._ms_res,
                        WV_MIN: 430,
                        WV_MAX: 545,
                    },
                ),
                "green": SpectralBand(
                    eoreader_name=GREEN,
                    **{
                        NAME: "GREEN",
                        ID: 2,
                        GSD: self._ms_res,
                        WV_MIN: 466,
                        WV_MAX: 620,
                    },
                ),
                "red": SpectralBand(
                    eoreader_name=RED,
                    **{NAME: "RED", ID: 3, GSD: self._ms_res, WV_MIN: 590, WV_MAX: 710},
                ),
                "nir": SpectralBand(
                    eoreader_name=NIR,
                    **{
                        NAME: "NIR1",
                        ID: 4,
                        GSD: self._ms_res,
                        WV_MIN: 715,
                        WV_MAX: 918,
                    },
                ),
            }
        elif self.constellation == Constellation.WV01:
            spectral_bands = {
                "pan": SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self._pan_res,
                        WV_MIN: 400,
                        WV_MAX: 900,
                    },
                )
            }
        elif self.constellation in [Constellation.GE01, Constellation.WV04]:
            spectral_bands = {
                "pan": SpectralBand(
                    eoreader_name=PAN,
                    **{
                        NAME: "PAN",
                        ID: 1,
                        GSD: self._pan_res,
                        WV_MIN: 450,
                        WV_MAX: 800,
                    },
                ),
                "blue": SpectralBand(
                    eoreader_name=BLUE,
                    **{
                        NAME: "BLUE",
                        ID: 1 if self.constellation == Constellation.GE01 else 3,
                        GSD: self._ms_res,
                        WV_MIN: 450,
                        WV_MAX: 510,
                    },
                ),
                "green": SpectralBand(
                    eoreader_name=GREEN,
                    **{
                        NAME: "GREEN",
                        ID: 2,
                        GSD: self._ms_res,
                        WV_MIN: 510,
                        WV_MAX: 580,
                    },
                ),
                "red": SpectralBand(
                    eoreader_name=RED,
                    **{
                        NAME: "RED",
                        ID: 3 if self.constellation == Constellation.GE01 else 1,
                        GSD: self._ms_res,
                        WV_MIN: 655,
                        WV_MAX: 690,
                    },
                ),
                "nir": SpectralBand(
                    eoreader_name=NIR,
                    **{
                        NAME: "NIR1",
                        ID: 4,
                        GSD: self._ms_res,
                        WV_MIN: 780,
                        WV_MAX: 920,
                    },
                ),
            }
        else:
            raise InvalidProductError(f"Unknown platform: {self.constellation}")

        return spectral_bands

    def _get_band_map(self, **kwargs) -> dict:
        """Get band map"""
        # Open spectral bands
        pan = kwargs.get("pan")
        blue = kwargs.get("blue")
        green = kwargs.get("green")
        red = kwargs.get("red")
        nir = kwargs.get("nir")
        ca = kwargs.get("ca")
        vre = kwargs.get("vre")
        vre1 = kwargs.get("vre1")
        vre2 = kwargs.get("vre2")
        yellow = kwargs.get("yellow")
        wv = kwargs.get("wv")

        # Manage bands of the product
        if self.band_combi == MaxarBandId.P:
            band_map = {PAN: pan.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi == MaxarBandId.N:
            band_map = {
                NIR: nir.update(id=1, gsd=self.pixel_size),
                NARROW_NIR: nir.update(id=1, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.R:
            band_map = {RED: red.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi == MaxarBandId.G:
            band_map = {GREEN: green.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi == MaxarBandId.B:
            band_map = {BLUE: blue.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi in [MaxarBandId.N2, MaxarBandId.RE]:
            if self.constellation_id == MaxarSatId.WVLG.name:
                band_map = {
                    VRE_1: vre1.update(id=1, gsd=self.pixel_size),
                    VRE_2: vre2.update(id=2, gsd=self.pixel_size),
                    VRE_3: vre2.update(id=2, gsd=self.pixel_size),
                }
            else:
                band_map = {
                    VRE_1: vre.update(id=1, gsd=self.pixel_size),
                    VRE_2: vre.update(id=1, gsd=self.pixel_size),
                    VRE_3: vre.update(id=1, gsd=self.pixel_size),
                }
        elif self.band_combi == MaxarBandId.Y:
            band_map = {YELLOW: yellow.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi == MaxarBandId.C:
            band_map = {CA: ca.update(id=1, gsd=self.pixel_size)}
        elif self.band_combi == MaxarBandId.RGB:
            band_map = {
                RED: red.update(id=1, gsd=self.pixel_size),
                GREEN: green.update(id=2, gsd=self.pixel_size),
                BLUE: blue.update(id=3, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.NRG:
            band_map = {
                NIR: nir.update(id=1, gsd=self.pixel_size),
                NARROW_NIR: nir.update(id=1, gsd=self.pixel_size),
                RED: red.update(id=2, gsd=self.pixel_size),
                GREEN: green.update(id=3, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.BGRN:
            band_map = {
                BLUE: blue.update(id=1, gsd=self.pixel_size),
                GREEN: green.update(id=2, gsd=self.pixel_size),
                RED: red.update(id=3, gsd=self.pixel_size),
                NIR: nir.update(id=4, gsd=self.pixel_size),
                NARROW_NIR: nir.update(id=4, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.MS1:
            band_map = {
                NIR: nir.update(id=1, gsd=self.pixel_size),
                NARROW_NIR: nir.update(id=1, gsd=self.pixel_size),
                RED: red.update(id=2, gsd=self.pixel_size),
                GREEN: green.update(id=3, gsd=self.pixel_size),
                BLUE: blue.update(id=4, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.MS2:
            band_map = {
                WV: wv.update(id=1, gsd=self.pixel_size),
                VRE_1: vre.update(id=2, gsd=self.pixel_size),
                VRE_2: vre.update(id=2, gsd=self.pixel_size),
                VRE_3: vre.update(id=2, gsd=self.pixel_size),
                YELLOW: yellow.update(id=3, gsd=self.pixel_size),
                CA: ca.update(id=4, gsd=self.pixel_size),
            }
        elif self.band_combi == MaxarBandId.Multi:
            if self.constellation_id in (MaxarSatId.WV02.name, MaxarSatId.WV03.name):
                band_map = {
                    CA: ca.update(id=1, gsd=self.pixel_size),
                    BLUE: blue.update(id=2, gsd=self.pixel_size),
                    GREEN: green.update(id=3, gsd=self.pixel_size),
                    YELLOW: yellow.update(id=4, gsd=self.pixel_size),
                    RED: red.update(id=5, gsd=self.pixel_size),
                    VRE_1: vre.update(id=6, gsd=self.pixel_size),
                    VRE_2: vre.update(id=6, gsd=self.pixel_size),
                    VRE_3: vre.update(id=6, gsd=self.pixel_size),
                    NIR: nir.update(id=7, gsd=self.pixel_size),
                    NARROW_NIR: nir.update(id=7, gsd=self.pixel_size),
                    WV: wv.update(id=8, gsd=self.pixel_size),
                }
            elif self.constellation_id == MaxarSatId.WVLG.name:
                band_map = {
                    CA: ca.update(id=1, gsd=self.pixel_size),
                    BLUE: blue.update(id=2, gsd=self.pixel_size),
                    GREEN: green.update(id=3, gsd=self.pixel_size),
                    YELLOW: yellow.update(id=4, gsd=self.pixel_size),
                    RED: red.update(id=5, gsd=self.pixel_size),
                    VRE_1: vre1.update(id=6, gsd=self.pixel_size),
                    VRE_2: vre2.update(id=7, gsd=self.pixel_size),
                    VRE_3: vre2.update(id=7, gsd=self.pixel_size),
                    NIR: nir.update(id=8, gsd=self.pixel_size),
                    NARROW_NIR: nir.update(id=8, gsd=self.pixel_size),
                }
            else:
                band_map = {
                    NIR: nir.update(id=1, gsd=self.pixel_size),
                    NARROW_NIR: nir.update(id=1, gsd=self.pixel_size),
                    RED: red.update(id=2, gsd=self.pixel_size),
                    GREEN: green.update(id=3, gsd=self.pixel_size),
                    BLUE: blue.update(id=4, gsd=self.pixel_size),
                }
        else:
            raise InvalidProductError(
                f"Unusual band combination: {self.band_combi.name}"
            )

        return band_map

    def _map_bands(self):
        """
        Map bands
        """
        self.bands.map_bands(self._get_band_map(**self._get_spectral_bands()))

    def _set_product_type(self) -> None:
        """Set products type"""
        # Get MTD XML file
        root, _ = self.read_mtd()
        prod_type = root.findtext(".//IMD/PRODUCTTYPE")
        if not prod_type:
            raise InvalidProductError(
                "Cannot find the PRODUCTTYPE in the metadata file"
            )
        self.product_type = getattr(MaxarProductType, prod_type)
        if self.product_type not in (MaxarProductType.Ortho, MaxarProductType.Standard):
            raise NotImplementedError(
                f"For now, "
                f"only {MaxarProductType.Ortho.value, MaxarProductType.Standard.value} "
                f"product types are supported for Maxar products."
            )

        if self.product_type == MaxarProductType.Standard:
            self.is_ortho = False

    def _get_raw_crs(self) -> riocrs.CRS:
        """
        Get raw CRS of the tile

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Open metadata
        root, _ = self.read_mtd()

        # Get CRS
        map_proj_name = root.findtext(".//MAPPROJNAME")
        if not map_proj_name:
            raise InvalidProductError("Cannot find MAPPROJNAME in the metadata file")
        if map_proj_name == "Geographic (Lat/Long)":
            crs = EPSG_4326
        elif map_proj_name == "UTM":
            map_hemi = root.findtext(".//MAPHEMI")
            map_zone = root.findtext(".//MAPZONE")
            if not map_hemi or not map_zone:
                raise InvalidProductError(
                    "Cannot find MAPHEMI or MAPZONE type in the metadata file"
                )
            crs = riocrs.CRS.from_string(
                f"EPSG:32{6 if map_hemi == 'N' else 7}{map_zone}"
            )
        else:
            raise NotImplementedError(
                "Only Geographic or UTM map projections are supported yet"
            )

        return crs

    @cache
    def crs(self) -> riocrs.CRS:
        """
        Get UTM projection of the tile

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.crs()
            CRS.from_epsg(32618)

        Returns:
            rasterio.crs.CRS: CRS object
        """
        # Get Raw CRS
        raw_crs = self._get_raw_crs()

        # Get CRS
        if raw_crs.is_geographic:
            # Open metadata
            root, _ = self.read_mtd()

            # Get the origin lon lat
            lon = float(root.findtext(".//ORIGINX"))
            lat = float(root.findtext(".//ORIGINY"))

            # Compute UTM crs from center long/lat
            utm = vectors.to_utm_crs(lon, lat)
        else:
            utm = raw_crs

        return utm

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1B_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.footprint()
                                                         gml_id  ...                                           geometry
            0  source_image_footprint-DS_PHR1A_20200511023124...  ...  POLYGON ((707025.261 9688613.833, 707043.276 9...
            [1 rows x 3 columns]

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        # If ortho -> nodata is not set!
        if self.is_ortho:
            # Get footprint of the first band of the stack
            footprint_dezoom = 10
            arr = utils.read(
                self.get_default_band_path(),
                resolution=self.pixel_size * footprint_dezoom,
                indexes=[1],
            )

            # Vectorize the nodata band
            footprint = rasters.vectorize(
                arr, values=0, keep_values=False, dissolve=True
            )
            footprint = geometry.get_wider_exterior(footprint.convex_hull)
        else:
            # If not ortho -> default band has been orthorectified and nodata will be set
            footprint = rasters.get_footprint(self.get_default_band_path())

        return footprint.to_crs(self.crs())

    @cache
    def extent(self, **kwargs) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile.

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Compute extent corners
        default_extent = root.find(".//MAP_PROJECTED_PRODUCT")
        ul_corner = (
            float(default_extent.findtext("ULX")),
            float(default_extent.findtext("ULY")),
        )
        ur_corner = (
            float(default_extent.findtext("URX")),
            float(default_extent.findtext("URY")),
        )
        lr_corner = (
            float(default_extent.findtext("LRX")),
            float(default_extent.findtext("LRY")),
        )
        ll_corner = (
            float(default_extent.findtext("LLX")),
            float(default_extent.findtext("LLY")),
        )
        corners = [ul_corner, ur_corner, lr_corner, ll_corner]

        raw_extent = gpd.GeoDataFrame(
            geometry=[Polygon(corners)],
            crs=self._get_raw_crs(),
        )

        return raw_extent.to_crs(self.crs())

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format  :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
            datetime_str = root.findtext(".//EARLIESTACQTIME")
            if not datetime_str:
                datetime_str = root.findtext(".//FIRSTLINETIME")
                if not datetime_str:
                    raise InvalidProductError(
                        "Cannot find EARLIESTACQTIME or FIRSTLINETIME in the metadata file."
                    )

            # Convert to datetime
            datetime_str = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")

            if not as_datetime:
                datetime_str = datetime_str.strftime(DATETIME_FMT)

        else:
            datetime_str = self.datetime
            if not as_datetime:
                datetime_str = datetime_str.strftime(DATETIME_FMT)

        return datetime_str

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        return path.get_filename(self._get_tile_path())

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
            elev_angle = float(root.findtext(".//MEANSUNEL"))
            azimuth_angle = float(root.findtext(".//MEANSUNAZ"))
        except TypeError as exc:
            raise InvalidProductError(
                "Azimuth or Zenith angles not found in metadata!"
            ) from exc

        # From elevation to zenith
        zenith_angle = 90.0 - elev_angle

        return azimuth_angle, zenith_angle

    @cache
    def get_mean_viewing_angles(self) -> (float, float, float):
        """
        Get Mean Viewing angles (azimuth, off-nadir and incidence angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_viewing_angles()

        Returns:
            (float, float, float): Mean azimuth, off-nadir and incidence angles
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            az = float(root.findtext(".//MEANSATAZ"))
            incidence_angle = 90 - float(root.findtext(".//MEANSATEL"))
            off_nadir = float(root.findtext(".//MEANOFFNADIRVIEWANGLE"))
        except TypeError as exc:
            raise InvalidProductError(
                "MEANSATAZ, MEANSATEL or MEANOFFNADIRVIEWANGLE angles not found in metadata!"
            ) from exc

        return az, off_nadir, incidence_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces as a dict
        """
        mtd_from_path = f"{self.name}.XML"
        mtd_archived = rf"{self.name}\.XML"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # Convert DN into radiance
        band_arr = self._dn_to_toa_rad(band_arr, band)

        # Convert radiance into reflectance
        band_arr = self._toa_rad_to_toa_refl(band_arr, band)

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band?
        """
        return False

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: Union[list, tuple] = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        if bands:
            LOGGER.warning("Maxar products do not provide any cloud file")

        return {}

    def _get_tile_path(self) -> AnyPathType:
        """
        Get the DIMAP filepath

        Returns:
            AnyPathType: DIMAP filepath
        """
        return self._get_path(extension="TIL")

    def _dn_to_toa_rad(self, dn_arr: xr.DataArray, band: BandNames) -> xr.DataArray:
        """
        Compute DN to TOA radiance

        See
        `here <https://apollomapping.com/image_downloads/Maxar_AbsRadCalDataSheet2018v0.pdf>`_
        for more information.

        Args:
            dn_arr (xr.DataArray): DN array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Radiance array
        """
        band_mtd_str = f"BAND_{_MAXAR_BAND_MTD[band]}"

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open absolute calibration factor and the effective bandwidth
        try:
            band_mtd = root.find(f".//{band_mtd_str}")
            abs_factor = float(band_mtd.findtext(".//ABSCALFACTOR"))
            effective_bandwidth = float(band_mtd.findtext(".//EFFECTIVEBANDWIDTH"))
        except TypeError as exc:
            raise InvalidProductError(
                "ABSCALFACTOR or EFFECTIVEBANDWIDTH not found in metadata!"
            ) from exc

        # Get constellation-specific gain and offset (latest)
        gain, offset = _MAXAR_GAIN_OFFSET[self.constellation][band]

        # Compute the coefficient converting DN in TOA radiance
        coeff = gain * abs_factor / effective_bandwidth

        # LOGGER.debug(f"DN to rad coeff = {coeff}")
        return dn_arr.copy(data=coeff * dn_arr.data + offset)

    def _toa_rad_to_toa_refl(
        self, rad_arr: xr.DataArray, band: BandNames
    ) -> xr.DataArray:
        """
        Compute TOA reflectance from TOA radiance

        Args:
            rad_arr (xr.DataArray): TOA Radiance array
            band (BandNames): Band

        Returns:
            xr.DataArray: TOA Reflectance array
        """
        # Compute the coefficient converting TOA radiance in TOA reflectance
        e0 = _MAXAR_E0[self.constellation][band]

        if self.constellation == Constellation.WVLG:
            e0_lg = getattr(e0, self._platform.name)

            # If for a reason or another e0 is not filled, use the mean of the other existing values
            if np.isnan(e0_lg):
                LOGGER.warning(
                    f"Solar irradiance not filled for {self._platform.name}. "
                    f"Please report this on GitHub! (https://github.com/sertit/eoreader/issues)"
                    f"In the meantime, values will be averaged from other Legion platforms."
                )
                e0 = np.nanmean(e0)
                LOGGER.warning(f"Solar irradiance used for {band.name} is: {e0}")
            else:
                e0 = e0_lg

        return self._toa_rad_to_toa_refl_formula(rad_arr, e0)

    @cache
    def get_cloud_cover(self) -> float:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_cloud_cover()
            55.5

        Returns:
            float: Cloud cover as given in the metadata
        """

        # Get MTD XML file
        root, _ = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(".//CLOUDCOVER"))

        except TypeError:
            LOGGER.warning("'CLOUDCOVER' not found in metadata!")
            cc = 0.0

        # Manage the case with cloud_cover == -999.0
        # i.e. 17APR05171409-M1BS_R1C1-000000010003_01_P001 (WV04)
        if cc < 0.0:
            cc = 0.0

        return cc

    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(
                    regex=r".*BROWSE\.JPG"
                )
            else:
                quicklook_path = next(self.path.glob("*BROWSE.JPG"))
            quicklook_path = str(quicklook_path)
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[0].split("-")[-1]

    # TODO: Uncomment this if the legion platform becomes important one day
    # def _get_condensed_name(self) -> str:
    #     """
    #     Get products condensed name ({acq_datetime}_{constellation}_{polarization}_{sensor_mode}_{product_type}).
    #
    #     Returns:
    #         str: Condensed Maxar name
    #     """
    #     # Get back the correct sensor mode name
    #     if self.constellation == Constellation.WVLG:
    #         return f"{self.get_datetime()}_{self.constellation.name}_{self._platform.name}_{self.product_type.name}_{self.band_combi.name}_{self._job_id}"
    #     else:
    #         return super()._get_condensed_name()
