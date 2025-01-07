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
PlanetScope products.
See
`Product specs <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
and `Planet documentation <https://developers.planet.com/docs/data/planetscope/>`_
for more information.
"""

import contextlib
import logging
from collections import defaultdict
from datetime import datetime
from enum import unique
from typing import Union

import numpy as np
import rasterio
import xarray as xr
from lxml import etree
from sertit import path, rasters, xml
from sertit.misc import ListEnum
from sertit.types import AnyPathType
from sertit.vectors import WGS84

from eoreader import DATETIME_FMT, EOREADER_NAME
from eoreader.bands import (
    BLUE,
    CA,
    GREEN,
    GREEN_1,
    NARROW_NIR,
    NIR,
    RED,
    VRE_1,
    VRE_2,
    VRE_3,
    YELLOW,
    BandNames,
    SpectralBand,
)
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.planet_product import PlanetProduct
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class PlaInstrument(ListEnum):
    """PlanetScope instrument
    See `Planet documentation <https://developers.planet.com/docs/apis/data/sensors/>`__
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
    basic_udm2              Unorthorectified usable data mask (Cloud 2.0)
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


class PlaProduct(PlanetProduct):
    """
    Class of PlanetScope products.
    See `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`__
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self.constellation = self._get_constellation()
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self._has_cloud_cover = True

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Ortho Tiles
        if self.product_type == PlaProductType.L3A:
            self.pixel_size = 3.125
        # Ortho Scene
        else:
            self.pixel_size = 3.0

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Manage constellation
        instr_node = root.find(f".//{nsmap['eop']}Instrument")
        instrument = instr_node.findtext(f"{nsmap['eop']}shortName")

        if not instrument:
            raise InvalidProductError("Cannot find the Instrument in the metadata file")

        # Set correct constellation
        self.instrument = getattr(PlaInstrument, instrument.replace(".", "_"))

    def _get_spectral_bands(self) -> dict:
        """
        See `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_ for more information.

        Returns:
            dict: PlanetScope spectral bands
        """
        gsd = 3.7

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "Blue", ID: 2, GSD: gsd, WV_MIN: 465, WV_MAX: 515},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "Green", ID: 4, GSD: gsd, WV_MIN: 547, WV_MAX: 583},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "Red", ID: 6, GSD: gsd, WV_MIN: 650, WV_MAX: 680},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 8, GSD: gsd, WV_MIN: 845, WV_MAX: 885},
        )

        # Create spectral bands
        if self.instrument == PlaInstrument.PSB_SD:
            spectral_bands = {
                "ca": SpectralBand(
                    eoreader_name=CA,
                    **{NAME: "Coastal Blue", ID: 1, GSD: gsd, WV_MIN: 431, WV_MAX: 452},
                ),
                "blue": blue,
                "green1": SpectralBand(
                    eoreader_name=GREEN_1,
                    **{NAME: "Green I", ID: 3, GSD: gsd, WV_MIN: 513, WV_MAX: 549},
                ),
                "green": green.update(name="Green II"),
                "yellow": SpectralBand(
                    eoreader_name=YELLOW,
                    **{NAME: "Yellow", ID: 5, GSD: gsd, WV_MIN: 600, WV_MAX: 620},
                ),
                "red": red,
                "vre": SpectralBand(
                    eoreader_name=VRE_1,
                    **{NAME: "Red-Edge", ID: 7, GSD: gsd, WV_MIN: 697, WV_MAX: 713},
                ),
                "nir": nir,
            }
        elif self.instrument == PlaInstrument.PS2_SD:
            spectral_bands = {
                "blue": blue.update(**{ID: 1, WV_MIN: 464, WV_MAX: 517}),
                "green": green.update(**{ID: 2, WV_MIN: 547, WV_MAX: 585}),
                "red": red.update(**{ID: 3, WV_MIN: 650, WV_MAX: 682}),
                "nir": nir.update(**{ID: 4, WV_MIN: 846, WV_MAX: 888}),
            }
        elif self.instrument == PlaInstrument.PS2:
            spectral_bands = {
                "blue": blue.update(**{ID: 1, WV_MIN: 455, WV_MAX: 515}),
                "green": green.update(**{ID: 2, WV_MIN: 500, WV_MAX: 590}),
                "red": red.update(**{ID: 3, WV_MIN: 590, WV_MAX: 670}),
                "nir": nir.update(**{ID: 4, WV_MIN: 780, WV_MAX: 860}),
            }
        else:
            raise InvalidProductError(
                f"Non recognized PlanetScope Instrument: {self.instrument}"
            )

        return spectral_bands

    def _get_band_map(self, nof_bands, **kwargs) -> dict:
        """
        Get band map
        """
        # Open spectral bands
        ca = kwargs.get("ca")
        blue = kwargs.get("blue")
        green = kwargs.get("green")
        green1 = kwargs.get("green1")
        red = kwargs.get("red")
        nir = kwargs.get("nir")
        vre = kwargs.get("vre")
        yellow = kwargs.get("yellow")

        if nof_bands == 3:
            band_map = {
                BLUE: blue.update(id=1),
                GREEN: green.update(id=2),
                RED: red.update(id=3),
            }
        elif nof_bands == 4:
            band_map = {
                BLUE: blue.update(id=1),
                GREEN: green.update(id=2),
                RED: red.update(id=3),
                NIR: nir.update(id=4),
                NARROW_NIR: nir.update(id=4),
            }
        elif nof_bands == 5:
            band_map = {
                BLUE: blue.update(id=1),
                GREEN: green.update(id=2),
                RED: red.update(id=3),
                VRE_1: vre.update(id=4),
                VRE_2: vre.update(id=4),
                VRE_3: vre.update(id=4),
                NIR: nir.update(id=5),
                NARROW_NIR: nir.update(id=5),
            }
        elif nof_bands == 8:
            band_map = {
                CA: ca,
                BLUE: blue,
                GREEN_1: green1,
                GREEN: green,
                RED: red,
                YELLOW: yellow,
                VRE_1: vre,
                NIR: nir,
                NARROW_NIR: nir,
            }
        else:
            raise InvalidProductError(
                f"Unusual number of bands ({nof_bands}) for {self.path}. "
                f"Please check the validity of your product"
            )

        return band_map

    def _map_bands(self):
        """
        Map bands
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Manage bands of the product
        nof_bands = int(root.findtext(f".//{nsmap[self._nsmap_key]}numBands"))

        # Set the band map
        self.bands.map_bands(
            self._get_band_map(nof_bands, **self._get_spectral_bands())
        )

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

    def get_datetime(self, as_datetime: bool = False) -> Union[str, datetime]:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

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
        if self.datetime is None:
            # Get MTD XML file
            root, nsmap = self.read_mtd()
            datetime_str = root.findtext(f".//{nsmap['eop']}acquisitionDate")
            if not datetime_str:
                raise InvalidProductError(
                    "Cannot find acquisitionDate in the metadata file."
                )

            # Convert to datetime
            datetime_str = datetime_str.split("+")[0]
            try:
                datetime_str = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                datetime_str = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f")

        else:
            datetime_str = self.datetime

        if not as_datetime:
            datetime_str = datetime_str.strftime(DATETIME_FMT)

        return datetime_str

    def _get_stack_path(self, as_list: bool = False) -> Union[str, list]:
        """
        Get Planet stack path(s)

        Args:
            as_list (bool): Get stack path as a list (useful if several subdatasets are present)

        Returns:
            Union[str, list]: Stack path(s)
        """
        if self._merged:
            stack_path, _ = self._get_out_path(f"{self.condensed_name}_analytic.vrt")
            if as_list:
                stack_path = [stack_path]
        else:
            stack_path = self._get_path(
                "Analytic", "tif", invalid_lookahead="udm", as_list=as_list
            )

        if as_list and len(stack_path) < 1:
            raise InvalidProductError("This is not a Planet Product.")

        return stack_path

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
        if self._merged:
            return band_arr
        else:
            # Get MTD XML file
            root, nsmap = self.read_mtd()

            # Open identifier
            refl_coef = None

            for band_mtd in root.iterfind(
                f".//{nsmap[self._nsmap_key]}bandSpecificMetadata"
            ):
                if (
                    int(band_mtd.findtext(f".//{nsmap[self._nsmap_key]}bandNumber"))
                    == self.bands[band].id
                ):
                    refl_coef = float(
                        band_mtd.findtext(
                            f".//{nsmap[self._nsmap_key]}reflectanceCoefficient"
                        )
                    )
                    break

            if refl_coef is None:
                raise InvalidProductError(
                    "Couldn't find any reflectanceCoefficient in the product metadata!"
                )

            # To reflectance
            return band_arr * refl_coef

    def _merge_subdatasets_mtd(self):
        """
        Merge subdataset, when several Planet products avec been ordered together
        Will create a reflectance (if possible) VRT, a UDM/UDM2 VRT and a merged metadata XML file.
        """

        def update_corner_dict(key, lon, lat):
            with contextlib.suppress(Exception):
                lon = lon.iat[0]
            with contextlib.suppress(Exception):
                lat = lat.iat[0]

            xml.update_txt(
                mtd,
                f"{nsmap[self._nsmap_key]}{key}/{nsmap[self._nsmap_key]}longitude",
                lon,
            )
            xml.update_txt(
                mtd,
                f"{nsmap[self._nsmap_key]}{key}/{nsmap[self._nsmap_key]}latitude",
                lat,
            )

        # Merge datasets
        analytic_vrt_path, analytic_vrt_exists = self._merge_subdatasets()

        # Check if mtd needs an update
        mtd_file, mtd_exists = self._get_out_path(f"{self.condensed_name}_metadata.xml")

        # -- Update VRT
        scales = defaultdict(dict)
        cloud_cover = []
        udp = []
        if not mtd_exists or not analytic_vrt_exists:
            # Get all scales, cloud cloudCoverPercentage, unusableDataPercentage
            for mtd_f in self._get_path("metadata", "xml", as_list=True):
                mtd_filename = path.get_filename(mtd_f)
                subprod_name = mtd_filename.split("_Analytic")[0]
                mtd, nsmap = self._read_mtd_xml(
                    f"{subprod_name}*metadata*xml", f"{subprod_name}.*metadata.*xml"
                )

                # reflectanceCoefficient
                for band_mtd in mtd.iterfind(
                    f".//{nsmap[self._nsmap_key]}bandSpecificMetadata"
                ):
                    band_nb = band_mtd.findtext(f"{nsmap[self._nsmap_key]}bandNumber")
                    refl_coef = band_mtd.findtext(
                        f"{nsmap[self._nsmap_key]}reflectanceCoefficient"
                    )
                    scales[subprod_name][band_nb] = refl_coef

                # cloudCoverPercentage
                cloud_cover.append(
                    float(mtd.findtext(f".//{nsmap['opt']}cloudCoverPercentage"))
                )

                # unusableDataPercentage
                udp.append(
                    float(
                        mtd.findtext(
                            f".//{nsmap[self._nsmap_key]}unusableDataPercentage"
                        )
                    )
                )

        if not analytic_vrt_exists:
            LOGGER.debug("Update raster VRT")
            vrt = etree.parse(analytic_vrt_path).getroot()

            # Remove stats and histograms
            xml.remove(vrt, "Metadata")
            xml.remove(vrt, "Histograms")

            # Convert to Float32
            xml.update_attrib(
                vrt, "VRTRasterBand[@dataType='UInt16']", "dataType", "Float32"
            )  # datatype with d!
            xml.update_attrib(
                vrt, "SourceProperties[@DataType='UInt16']", "DataType", "Float32"
            )  # datatype with D!

            # Scale the VRT
            for el in vrt.iterfind(".//ComplexSource"):
                band_name = path.get_filename(el.findtext("SourceFilename")).split(
                    "_Analytic"
                )[0]
                band_number = el.findtext("SourceBand")

                # Set scaleRatio in VRT
                xml.add(el, "ScaleRatio", scales[band_name][band_number])

            # Write VRT on disk
            xml.write(vrt, analytic_vrt_path)

        # -- Update MTD
        if not mtd_exists:
            LOGGER.debug("Merge metadata")
            mtd, nsmap = self.read_mtd()

            # Remove all reflectance scaling
            xml.remove(mtd, f"{nsmap[self._nsmap_key]}reflectanceCoefficient")

            # Get new size from VRT
            with rasterio.open(str(analytic_vrt_path)) as ds:
                xml.update_txt(mtd, f"{nsmap[self._nsmap_key]}numRows", ds.height)
                xml.update_txt(mtd, f"{nsmap[self._nsmap_key]}numColumns", ds.width)

            # Get new extent from VRT
            extent = rasters.get_extent(analytic_vrt_path)
            extent_wgs84 = extent.to_crs(WGS84)

            # Compute centroid and reproject to WGS84 after
            pos = extent.centroid.to_crs(WGS84).iat[0]
            xml.update_txt(mtd, f"{nsmap['gml']}pos", f"{pos.x} {pos.y}")

            # Get extent coordinates (should be footprint but too long to compute IMHO)
            coordinates_str = " ".join(
                f"{coord[0]},{coord[1]}"
                for coord in extent_wgs84.boundary.iat[0].coords
            )
            xml.update_txt(mtd, f"{nsmap['gml']}coordinates", coordinates_str)

            # Get corners
            bounds_wgs84 = extent_wgs84.bounds
            update_corner_dict("topLeft", bounds_wgs84.maxx, bounds_wgs84.miny)
            update_corner_dict("topRight", bounds_wgs84.maxx, bounds_wgs84.maxy)
            update_corner_dict("bottomRight", bounds_wgs84.minx, bounds_wgs84.maxy)
            update_corner_dict("bottomLeft", bounds_wgs84.minx, bounds_wgs84.miny)

            # Manage cloudCoverPercentage, unusableDataPercentage
            xml.update_txt(
                mtd, f"{nsmap['opt']}cloudCoverPercentage", np.mean(cloud_cover)
            )
            xml.update_txt(
                mtd, f"{nsmap[self._nsmap_key]}unusableDataPercentage", np.mean(udp)
            )

            if self.product_type == PlaProductType.L3A:
                # -- PSOrthoTile

                # identifier: keep the one opened

                # Remove tileId
                xml.remove(mtd, f"{nsmap[self._nsmap_key]}tileId")

                # Round incidenceAngle
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap['eop']}incidenceAngle",
                    lambda x: np.round(float(x), decimals=1),
                )

            elif self.product_type == PlaProductType.L3B:
                # -- PSOrthoScene
                # identifier: replace satellite ID by XX: 20210902_093940_06_245d_3B_AnalyticMS_8b -> 20210902_093940_XX_245d_3B_AnalyticMS_8b
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap['eop']}identifier",
                    lambda x: "_".join(
                        "XX" if i == 2 else z for i, z in enumerate(x.split("_"))
                    ),
                )

                # Remove filename
                xml.remove(mtd, f"{nsmap['eop']}fileName")

                # Round incidenceAngle, illuminationAzimuthAngle, illuminationElevationAngle, azimuthAngle, spaceCraftViewAngle
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap['eop']}incidenceAngle",
                    lambda x: np.round(float(x), decimals=1),
                )
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap['opt']}illuminationAzimuthAngle",
                    lambda x: np.round(float(x), decimals=1),
                )
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap['opt']}illuminationElevationAngle",
                    lambda x: np.round(float(x), decimals=1),
                )
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap[self._nsmap_key]}azimuthAngle",
                    lambda x: np.round(float(x), decimals=1),
                )
                xml.update_txt_fct(
                    mtd,
                    f"{nsmap[self._nsmap_key]}spaceCraftViewAngle",
                    lambda x: np.round(float(x), decimals=1),
                )

            else:
                raise NotImplementedError

            # Write XML on disk
            xml.write(mtd, mtd_file)
