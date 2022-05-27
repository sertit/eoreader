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
PlanetScope products.
See
`Earth Online <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`_
and `Planet documentation <https://developers.planet.com/docs/data/planetscope/>`_
for more information.
"""
import logging
from datetime import datetime
from enum import unique
from pathlib import Path
from typing import Union

import xarray as xr
from cloudpathlib import CloudPath
from lxml import etree
from sertit.misc import ListEnum

from eoreader import cache
from eoreader.bands import BandNames, SpectralBand
from eoreader.bands import spectral_bands as spb
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.planet_product import PlanetProduct
from eoreader.products.product import OrbitDirection
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import DATETIME_FMT, EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class PlaInstrument(ListEnum):
    """PlanetScope instrument
    See `here <https://developers.planet.com/docs/apis/data/sensors/>`__
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


class PlaProduct(PlanetProduct):
    """
    Class of PlanetScope products.
    See `here <https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf>`__
    for more information.

    The scaling factor to retrieve the calibrated radiance is 0.01.
    """

    def _post_init(self, **kwargs) -> None:
        """
        Function used to post_init the products
        (setting sensor type, band names and so on)
        """
        self._has_cloud_cover = True

        # Ortho Tiles
        if self.product_type == PlaProductType.L3A:
            self.tile_name = self.split_name[1]

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _get_resolution(self) -> float:
        """
        Get product default resolution (in meters)
        """
        # Ortho Tiles
        if self.product_type == PlaProductType.L3A:
            return 3.125
        # Ortho Scene
        else:
            return 3.0

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
        See <here `https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf`_> for more information.

        Returns:
            dict: PlanetScope spectral bands
        """
        gsd = 3.7

        blue = SpectralBand(
            eoreader_name=spb.BLUE,
            **{NAME: "Blue", ID: 2, GSD: gsd, WV_MIN: 465, WV_MAX: 515},
        )

        green = SpectralBand(
            eoreader_name=spb.GREEN,
            **{NAME: "Green", ID: 4, GSD: gsd, WV_MIN: 547, WV_MAX: 583},
        )

        red = SpectralBand(
            eoreader_name=spb.RED,
            **{NAME: "Red", ID: 6, GSD: gsd, WV_MIN: 650, WV_MAX: 680},
        )

        nir = SpectralBand(
            eoreader_name=spb.NIR,
            **{NAME: "NIR", ID: 8, GSD: gsd, WV_MIN: 845, WV_MAX: 885},
        )

        # Create spectral bands
        if self.instrument == PlaInstrument.PSB_SD:
            spectral_bands = {
                "ca": SpectralBand(
                    eoreader_name=spb.CA,
                    **{NAME: "Coastal Blue", ID: 1, GSD: gsd, WV_MIN: 431, WV_MAX: 452},
                ),
                "blue": blue,
                "green1": SpectralBand(
                    eoreader_name=spb.GREEN,
                    **{NAME: "Green I", ID: 3, GSD: gsd, WV_MIN: 513, WV_MAX: 549},
                ),
                "green": green.update(name="Green II"),
                "yellow": SpectralBand(
                    eoreader_name=spb.YELLOW,
                    **{NAME: "Yellow", ID: 5, GSD: gsd, WV_MIN: 600, WV_MAX: 620},
                ),
                "red": red,
                "vre": SpectralBand(
                    eoreader_name=spb.VRE_1,
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
                spb.BLUE: blue.update(id=1),
                spb.GREEN: green.update(id=2),
                spb.RED: red.update(id=3),
            }
        elif nof_bands == 4:
            band_map = {
                spb.BLUE: blue.update(id=1),
                spb.GREEN: green.update(id=2),
                spb.RED: red.update(id=3),
                spb.NIR: nir.update(id=4),
                spb.NARROW_NIR: nir.update(id=4),
            }
        elif nof_bands == 5:
            band_map = {
                spb.BLUE: blue.update(id=1),
                spb.GREEN: green.update(id=2),
                spb.RED: red.update(id=3),
                spb.VRE_1: vre.update(id=4),
                spb.VRE_2: vre.update(id=4),
                spb.VRE_3: vre.update(id=4),
                spb.NIR: nir.update(id=5),
                spb.NARROW_NIR: nir.update(id=5),
            }
        elif nof_bands == 8:
            band_map = {
                spb.CA: ca,
                spb.BLUE: blue,
                spb.GREEN1: green1,
                spb.GREEN: green,
                spb.RED: red,
                spb.YELLOW: yellow,
                spb.VRE_1: vre,
                spb.NIR: nir,
                spb.NARROW_NIR: nir,
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
        nof_bands = int(root.findtext(f".//{nsmap['ps']}numBands"))

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
        elif self.product_type == PlaProductType.L3A:
            LOGGER.warning(
                f"Ortho Tile Product are not well tested for Planet products {self.path}."
                f"Use it at your own risk !"
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
                    "Cannot find EARLIESTACQTIME in the metadata file."
                )

            # Convert to datetime
            datetime_str = datetime.strptime(
                datetime_str.split("+")[0], "%Y-%m-%dT%H:%M:%S"
            )

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
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Open identifier
        name = root.findtext(f".//{nsmap['eop']}identifier")
        if not name:
            raise InvalidProductError(
                f"{nsmap['eop']}identifier not found in metadata!"
            )

        return name

    def get_band_paths(
        self, band_list: list, resolution: float = None, **kwargs
    ) -> dict:
        """
        Return the paths of required bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2"
            >>> prod = Reader().open(path)
            >>> prod.get_band_paths([GREEN, RED])
            {
                <SpectralBandNames.GREEN: 'GREEN'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',
                <SpectralBandNames.RED: 'RED'>:
                'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2/SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif'
            }

        Args:
            band_list (list): List of the wanted bands
            resolution (float): Band resolution
            kwargs: Other arguments used to load bands

        Returns:
            dict: Dictionary containing the path of each queried band
        """
        band_paths = {}
        for band in band_list:
            band_paths[band] = self._get_path(
                "AnalyticMS", "tif", invalid_lookahead="_DN_"
            )

        return band_paths

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        path: Union[Path, CloudPath],
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            path (Union[CloudPath, Path]): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Open identifier
        refl_coef = None
        for band_mtd in root.iterfind(f".//{nsmap['ps']}bandSpecificMetadata"):
            if (
                int(band_mtd.findtext(f".//{nsmap['ps']}bandNumber"))
                == self.bands[band].id
            ):
                refl_coef = float(
                    band_mtd.findtext(f".//{nsmap['ps']}reflectanceCoefficient")
                )
                break

        if refl_coef is None:
            raise InvalidProductError(
                "Couldn't find any reflectanceCoefficient in the product metadata!"
            )

        # To reflectance
        return band_arr * refl_coef

    @cache
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
            raise InvalidProductError("Azimuth or Zenith angles not found in metadata!")

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
        root, nsmap = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            az = float(root.findtext(f".//{nsmap['ps']}azimuthAngle"))
            off_nadir = float(root.findtext(f".//{nsmap['ps']}spaceCraftViewAngle"))
            incidence_angle = float(root.findtext(f".//{nsmap['eop']}incidenceAngle"))
        except TypeError:
            raise InvalidProductError(
                "azimuthAngle, spaceCraftViewAngle or incidenceAngle not found in metadata!"
            )

        return az, off_nadir, incidence_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
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
        mtd_archived = r"metadata.*\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

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
        root, nsmap = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(f".//{nsmap['opt']}cloudCoverPercentage"))

        except TypeError:
            raise InvalidProductError("opt:cloudCoverPercentage not found in metadata!")

        return cc

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
        root, nsmap = self.read_mtd()

        # Get the orbit direction
        try:
            od = OrbitDirection.from_value(
                root.findtext(f".//{nsmap['eop']}orbitDirection")
            )

        except TypeError:
            raise InvalidProductError("eop:orbitDirection not found in metadata!")

        return od

    def _get_condensed_name(self) -> str:
        """
        Get Planet products condensed name ({date}_{constellation}_{product_type}).

        Returns:
            str: Condensed name
        """
        return (
            f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}"
        )
