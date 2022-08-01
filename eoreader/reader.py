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
""" Product Factory, class creating products according to their names """

from __future__ import annotations

import importlib
import logging
import re
from enum import unique
from pathlib import Path
from typing import Union
from zipfile import BadZipFile

from cloudpathlib import AnyPath, CloudPath
from sertit import files, strings
from sertit.misc import ListEnum

from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class CheckMethod(ListEnum):
    """Methods to recognize a product"""

    MTD = "Metadata"
    """Check the metadata: faster method"""

    NAME = "Filename"
    """
    Check the filename:

    Safer method that allows modified product names as it recursively looks for the metadata name in the product files.
    For products that have generic metadata files (ie. RS2 that as mtd named :code:`product.xml`),
    it also checks the band name.
    """

    BOTH = "Both"
    """Check the metadata and the filename: Double check if you have a doubt."""


@unique
class Constellation(ListEnum):
    """Constellation supported by EOReader"""

    S1 = "Sentinel-1"
    """Sentinel-1"""

    S2 = "Sentinel-2"
    """Sentinel-2"""

    S2_THEIA = "Sentinel-2 Theia"
    """Sentinel-2 Theia"""

    S3_OLCI = "Sentinel-3 OLCI"
    """Sentinel-3 OLCI"""

    S3_SLSTR = "Sentinel-3 SLSTR"
    """Sentinel-3 SLSTR"""

    L9 = "Landsat-9"
    """Landsat-9"""

    L8 = "Landsat-8"
    """Landsat-8"""

    L7 = "Landsat-7"
    """Landsat-7"""

    L5 = "Landsat-5"
    """Landsat-5"""

    L4 = "Landsat-4"
    """Landsat-4"""

    L3 = "Landsat-3"
    """Landsat-3"""

    L2 = "Landsat-2"
    """Landsat-2"""

    L1 = "Landsat-1"
    """Landsat-1"""

    PLA = "PlanetScope"
    """PlanetScope"""

    # RPD = "RapidEye"
    # """RapidEye"""
    #
    SKY = "SkySat"
    """SkySat"""

    TSX = "TerraSAR-X"
    """TerraSAR-X"""

    TDX = "TanDEM-X"
    """TanDEM-X"""

    PAZ = "PAZ SAR"
    """SEOSAR/PAZ SAR"""

    RS2 = "RADARSAT-2"
    """RADARSAT-2"""

    PLD = "Pleiades"
    """Pléiades"""

    PNEO = "Pleiades-Neo"
    """Pleiades-Néo"""

    SPOT7 = "Spot-7"
    """SPOT-7"""

    SPOT6 = "Spot-6"
    """SPOT-6"""

    SPOT5 = "Spot-5"
    """SPOT-5"""

    SPOT4 = "Spot-4"
    """SPOT-4"""

    VIS1 = "Vision-1"
    """Vision-1"""

    RCM = "RADARSAT-Constellation Mission"
    """RADARSAT-Constellation Mission"""

    MAXAR = "Maxar"
    """Maxar (not a real constellation, but used as a template for every Maxar products)"""

    QB = "QuickBird"
    """QuickBird"""

    GE01 = "GeoEye-1"
    """GeoEye-1"""

    WV01 = "WorldView-1"
    """WorldView-1"""

    WV02 = "WorldView-2"
    """WorldView-2"""

    WV03 = "WorldView-3"
    """WorldView-3"""

    WV04 = "WorldView-4"
    """WorldView-4"""

    ICEYE = "ICEYE"
    """ICEYE"""

    SAOCOM = "SAOCOM-1"
    """SAOCOM-1"""

    SV1 = "SuperView-1"
    """SuperView-1"""

    CSK = "COSMO-SkyMed"
    """COSMO-SkyMed"""

    CSG = "COSMO-SkyMed 2nd Generation"
    """COSMO-SkyMed 2nd Generation"""

    SPOT45 = "Spot-4/5"
    """SPOT-4/5 (not a real constellation, but used as a template for SPOT4/5 products)"""

    CUSTOM = "CUSTOM"
    """Custom stack"""


CONSTELLATION_REGEX = {
    Constellation.S1: r"S1[AB]_(IW|EW|SM|WV)_(RAW|SLC|GRD|OCN)[FHM_]_[0-2]S[SD][HV]_\d{8}T\d{6}_\d{8}T\d{6}_\d{6}_.{11}",
    Constellation.S2: r"S2[AB]_MSIL(1C|2A)_\d{8}T\d{6}_N\d{4}_R\d{3}_T\d{2}\w{3}_\d{8}T\d{6}",
    Constellation.S2_THEIA: r"SENTINEL2[AB]_\d{8}-\d{6}-\d{3}_L(2A|1C)_T\d{2}\w{3}_[CDH](_V\d-\d|)",
    Constellation.S3_OLCI: r"S3[AB]_OL_[012]_\w{6}_\d{8}T\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_\w{17}_\w{3}_[OFDR]_(NR|ST|NT)_\d{3}",
    Constellation.S3_SLSTR: r"S3[AB]_SL_[012]_\w{6}_\d{8}T\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_\w{17}_\w{3}_[OFDR]_(NR|ST|NT)_\d{3}",
    Constellation.L9: r"L[OTC]09_L1(GT|TP)_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L8: r"L[OTC]08_L1(GT|TP)_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L7: r"LE07_L1(GT|TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L5: r"L[TM]05_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Constellation.L4: r"L[TM]04_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Constellation.L3: r"LM03_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.L2: r"LM02_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.L1: r"LM01_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.SKY: r"\d{8}_\d{6}_ssc\w{1,4}_\w{4,5}",
    Constellation.PLA: r"\d{8}_\d{6}_(\d{2}_|)\w{4}",
    Constellation.CSK: [
        r".+",  # Need to check inside as the folder does not have any recognizable name
        r"CSKS\d_(RAW|SCS|DGM|GEC|GTC)_[UB]_(HI|PP|WR|HR|S2)_"
        r"\w{2}_(HH|VV|VH|HV|CO|CH|CV)_[LR][AD]_[FS][NF]_\d{14}_\d{14}\.h5",
    ],
    Constellation.CSG: [
        r".+",  # Need to check inside as the folder does not have any recognizable name
        r"CSG_SSAR\d_(RAW|SCS|DGM|GEC|GTC)_([UBF]|FQLK_B)_\d{4}_(S2[ABC]|D2[RSJ]|OQ[RS]|STR|SC[12]|PPS|QPS)_\d{3}"
        r"_(HH|VV|VH|HV)_[LR][AD]_[DPFR]_\d{14}_\d{14}\_\d_[FC]_\d{2}[NS]_Z\d{2}_[NFB]\d{2}.h5",
    ],
    Constellation.TSX: r"TSX1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.TDX: r"TDX1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.PAZ: r"PAZ1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.RS2: r"RS2_(OK\d+_PK\d+_DK\d+_.{2,}_\d{8}_\d{6}|\d{8}_\d{6}_\d{4}_.{1,5})"
    r"(_(HH|VV|VH|HV)){1,4}_S(LC|GX|GF|CN|CW|CF|CS|SG|PG)(_\d{6}_\d{4}_\d{8}|)",
    Constellation.PLD: r"IMG_PHR1[AB]_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}",
    Constellation.PNEO: r"IMG_\d+_PNEO\d_(P|MS|PMS|MS-FS|PMS-FS)",
    Constellation.SPOT7: r"IMG_SPOT7_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
    Constellation.SPOT6: r"IMG_SPOT6_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
    Constellation.SPOT45: r"SPVIEW_.+",
    Constellation.SPOT4: r"SP04_HIR_(M_|I_|MI|X_|MX)___\d_\d{8}T\d{6}_\d{8}T\d{6}_.*",
    Constellation.SPOT5: r"SP05_HRG_(HM_|J__|T__|X__|TX__|HMX)__\d_\d{8}T\d{6}_\d{8}T\d{6}_.*",
    Constellation.VIS1: r"VIS1_(PAN|BUN|PSH|MS4)_.+_\d{2}-\d",
    Constellation.RCM: r"RCM\d_OK\d+_PK\d+_\d_.{4,}_\d{8}_\d{6}(_(HH|VV|VH|HV|RV|RH)){1,4}_(SLC|GRC|GRD|GCC|GCD)",
    Constellation.QB: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.GE01: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.WV01: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.WV02: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.WV03: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.WV04: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.MAXAR: r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)",
    Constellation.ICEYE: r"((SM|SL|SC|SLEA)[HW]*_\d{5,}|ICEYE_X\d_(SM|SL|SC|SLEA)H*_\d{5,}_\d{8}T\d{6})",
    Constellation.SAOCOM: r".+EOL1[ABCD]SARSAO1[AB]\d+(-product|)",
    Constellation.SV1: [
        r"\d{13}_\d{2}",
        r"SV1-0[1-4]_\d{8}_L(1B|2A)\d{10}_\d{13}_\d{2}-(MUX|PSH)\.xml",
    ],
}

MTD_REGEX = {
    Constellation.S1: {
        "nested": 1,
        # File that can be found at any level (product/**/file)
        "regex": r".*s1[ab]-(iw|ew|sm|wv)\d*-(raw|slc|grd|ocn)-[hv]{2}-\d{8}t\d{6}-\d{8}t\d{6}-\d{6}-\w{6}-\d{3}\.xml",
    },
    Constellation.S2: {"nested": 3, "regex": r"MTD_TL.xml"},
    Constellation.S2_THEIA: rf"{CONSTELLATION_REGEX[Constellation.S2_THEIA]}_MTD_ALL\.xml",
    Constellation.S3_OLCI: r"Oa\d{2}_radiance.nc",
    Constellation.S3_SLSTR: r"S\d_radiance_an.nc",
    Constellation.L9: rf"{CONSTELLATION_REGEX[Constellation.L9]}_MTL\.txt",
    Constellation.L8: rf"{CONSTELLATION_REGEX[Constellation.L8]}_MTL\.txt",
    Constellation.L7: rf"{CONSTELLATION_REGEX[Constellation.L7]}_MTL\.txt",
    Constellation.L5: rf"{CONSTELLATION_REGEX[Constellation.L5]}_MTL\.txt",
    Constellation.L4: rf"{CONSTELLATION_REGEX[Constellation.L4]}_MTL\.txt",
    Constellation.L3: rf"{CONSTELLATION_REGEX[Constellation.L3]}_MTL\.txt",
    Constellation.L2: rf"{CONSTELLATION_REGEX[Constellation.L2]}_MTL\.txt",
    Constellation.L1: rf"{CONSTELLATION_REGEX[Constellation.L1]}_MTL\.txt",
    Constellation.PLA: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": r"\d{8}_\d{6}_(\d{2}_|)\w{4}_[13][AB]_.*metadata.*\.xml",
    },
    Constellation.SKY: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": r"\d{8}_\d{6}_ssc\w{1,4}_\w{4,5}_.*metadata.*\.json",
    },
    Constellation.CSK: rf"{CONSTELLATION_REGEX[Constellation.CSK][1]}",
    Constellation.CSG: rf"{CONSTELLATION_REGEX[Constellation.CSG][1]}",
    Constellation.TSX: rf"{CONSTELLATION_REGEX[Constellation.TSX]}\.xml",
    Constellation.TDX: rf"{CONSTELLATION_REGEX[Constellation.TDX]}\.xml",
    Constellation.PAZ: rf"{CONSTELLATION_REGEX[Constellation.PAZ]}\.xml",
    Constellation.RS2: [
        r"product\.xml",  # Too generic name, check also a band
        r"imagery_[HV]{2}\.tif",
    ],
    Constellation.PLD: r"DIM_PHR1[AB]_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
    Constellation.PNEO: r"DIM_PNEO\d_\d{15}_(P|MS|PMS|MS-FS|PMS-FS)_(SEN|PRJ|ORT|MOS)_.{9,}_._._._.\.XML",
    Constellation.SPOT7: r"DIM_SPOT7_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
    Constellation.SPOT6: r"DIM_SPOT6_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
    Constellation.VIS1: r"DIM_VIS1_(PSH|MS4|PAN)_\d{14}_(PRJ|ORTP)_S\d{5,}_\d{4}_Meta\.xml",
    Constellation.RCM: {
        "nested": 1,  # File that can be found at 1st folder level (product/*/file)
        "regex": [
            r"product\.xml",  # Too generic name, check also a band
            r"\d+_[RHV]{2}\.tif",
        ],
    },
    Constellation.QB: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.GE01: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.WV01: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.WV02: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.WV03: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.WV04: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.MAXAR: r"\d{2}\w{3}\d{8}-.{4}(_R\dC\d|)-\d{12}_\d{2}_P\d{3}.TIL",
    Constellation.ICEYE: r"ICEYE_(X\d{1,}_|)(SLC|GRD)_((SM|SL|SC)H*|SLEA)_\d{5,}_\d{8}T\d{6}\.xml",
    Constellation.SAOCOM: r"S1[AB]_OPER_SAR_EOSSP__CORE_L1[A-D]_OL(F|VF)_\d{8}T\d{6}.xemt",
    Constellation.SV1: r"SV1-0[1-4]_\d{8}_L(1B|2A)\d{10}_\d{13}_\d{2}-(MUX|PSH)\.xml",
    Constellation.SPOT45: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": [
            r"METADATA\.DIM",  # Too generic name, check also a band
            r"IMAGERY\.TIF",
        ],
    },
    Constellation.SPOT4: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": [
            r"METADATA\.DIM",  # Too generic name, check also a band
            r"IMAGERY\.TIF",
        ],
    },
    Constellation.SPOT5: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": [
            r"METADATA\.DIM",  # Too generic name, check also a band
            r"IMAGERY\.TIF",
        ],
    },
}


class Reader:
    """
    Factory class creating satellite products according to their names.

    It creates a singleton that you can call only one time per file.
    """

    def __init__(self):
        self._constellation_regex = {}
        self._mtd_regex = {}
        self._mtd_nested = {}

        # Register constellations
        for constellation, regex in CONSTELLATION_REGEX.items():
            self._constellation_regex[constellation] = self._compile(
                regex, prefix="", suffix=""
            )

        # Register metadata
        for constellation, regex in MTD_REGEX.items():
            if isinstance(regex, dict):
                self._mtd_regex[constellation] = self._compile(
                    regex["regex"], prefix=".*", suffix=""
                )
                self._mtd_nested[constellation] = regex["nested"]
            else:
                self._mtd_regex[constellation] = self._compile(
                    regex, prefix=".*", suffix=""
                )
                self._mtd_nested[constellation] = 0

    @staticmethod
    def _compile(regex: Union[str, list], prefix="^", suffix="&") -> list:
        """
        Compile regex or list of regex

        Args:
            regex (Union[str, list]): Regex in :code:`re` sense
            prefix (str): Prefix of regex, ^ by default (means start of the string)
            suffix (str): Prefix of regex, & by default (means end of the string)

        Returns:
            list: List of compiled pattern
        """

        def _compile_(regex_str: str):
            return re.compile(f"{prefix}{regex_str}{suffix}")

        # Case folder is not enough to identify the products (ie. COSMO Skymed)
        if isinstance(regex, list):
            comp = [_compile_(regex) for regex in regex]
        else:
            comp = [_compile_(regex)]

        return comp

    def open(
        self,
        product_path: Union[str, CloudPath, Path],
        archive_path: Union[str, CloudPath, Path] = None,
        output_path: Union[str, CloudPath, Path] = None,
        method: CheckMethod = CheckMethod.MTD,
        remove_tmp: bool = False,
        custom: bool = False,
        constellation: Union[Constellation, str, list] = None,
        **kwargs,
    ) -> "Product":  # noqa: F821
        """
        Open the product.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2B_MSIL1C_20210517T103619_N7990_R008_T30QVE_20210929T075738.SAFE.zip"
            >>> Reader().open(path)
            eoreader.S2Product 'S2B_MSIL1C_20210517T103619_N7990_R008_T30QVE_20210929T075738'
            Attributes:
                condensed_name: 20210517T103619_S2_T30QVE_L1C_075738
                path: D:/S2B_MSIL1C_20210517T103619_N7990_R008_T30QVE_20210929T075738.SAFE.zip
                constellation: Sentinel-2
                sensor type: Optical
                product type: MSIL1C
                default resolution: 10.0
                acquisition datetime: 2021-05-17T10:36:19
                band mapping:
                    COASTAL_AEROSOL: 01
                    BLUE: 02
                    GREEN: 03
                    RED: 04
                    VEGETATION_RED_EDGE_1: 05
                    VEGETATION_RED_EDGE_2: 06
                    VEGETATION_RED_EDGE_3: 07
                    NIR: 8A
                    NARROW_NIR: 08
                    WATER_VAPOUR: 09
                    CIRRUS: 10
                    SWIR_1: 11
                    SWIR_2: 12
                needs extraction: False
                cloud cover: 0.155752635193646
                tile name: T30QVE

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            archive_path (Union[str, CloudPath, Path]): Archive path
            output_path (Union[str, CloudPath, Path]): Output Path
            method (CheckMethod): Checking method used to recognize the products
            remove_tmp (bool): Remove temp files (such as clean or orthorectified bands...) when the product is deleted
            custom (bool): True if we want to use a custom stack
            constellation (Union[Constellation, str, list]): One or several constellations to help the Reader to choose more rapidly the correct Product

        Returns:
            Product: Correct products

        """
        product_path = AnyPath(product_path)
        if not product_path.exists():
            FileNotFoundError(f"Non existing product: {product_path}")

        if custom:
            from eoreader.products import CustomProduct

            prod = CustomProduct(
                product_path=product_path,
                archive_path=archive_path,
                output_path=output_path,
                remove_tmp=remove_tmp,
                constellation=constellation,
                **kwargs,
            )
        else:
            prod = None
            if constellation is None:
                const_list = CONSTELLATION_REGEX.keys()
            else:
                const_list = Constellation.convert_from(constellation)

            for const in const_list:
                if method == CheckMethod.MTD:
                    is_valid = self.valid_mtd(product_path, const)
                elif method == CheckMethod.NAME:
                    is_valid = self.valid_name(product_path, const)
                else:
                    is_valid = self.valid_name(product_path, const) and self.valid_mtd(
                        product_path, const
                    )

                if is_valid:
                    sat_class = const.name.lower() + "_product"

                    # Channel correctly the constellations to their generic files (just in case)
                    # TerraSAR-like constellations
                    if const in [Constellation.TDX, Constellation.PAZ]:
                        sat_class = "tsx_product"
                        const = None  # All product names are the same, so assess it with MTD
                    # Maxar-like constellations
                    elif const in [
                        Constellation.QB,
                        Constellation.GE01,
                        Constellation.WV01,
                        Constellation.WV02,
                        Constellation.WV03,
                        Constellation.WV04,
                    ]:
                        sat_class = "maxar_product"
                        const = None  # All product names are the same, so assess it with MTD
                    # Lansat constellations
                    elif const in [
                        Constellation.L1,
                        Constellation.L2,
                        Constellation.L3,
                        Constellation.L4,
                        Constellation.L5,
                        Constellation.L7,
                        Constellation.L8,
                        Constellation.L9,
                    ]:
                        sat_class = "landsat_product"
                    # SPOT-6/7 constellations
                    elif const in [Constellation.SPOT6, Constellation.SPOT7]:
                        sat_class = "spot67_product"
                    # SPOT-4/5 constellations
                    elif const in [Constellation.SPOT4, Constellation.SPOT5]:
                        sat_class = "spot45_product"

                    # Manage both optical and SAR
                    try:
                        mod = importlib.import_module(
                            f"eoreader.products.sar.{sat_class}"
                        )
                    except ModuleNotFoundError:
                        mod = importlib.import_module(
                            f"eoreader.products.optical.{sat_class}"
                        )

                    class_ = getattr(mod, strings.snake_to_camel_case(sat_class))
                    prod = class_(
                        product_path=product_path,
                        archive_path=archive_path,
                        output_path=output_path,
                        remove_tmp=remove_tmp,
                        constellation=const,
                        **kwargs,
                    )
                    break

        if not prod:
            LOGGER.warning(
                "There is no existing products in EOReader corresponding to %s",
                product_path,
            )

        return prod

    def valid_name(
        self,
        product_path: Union[str, CloudPath, Path],
        constellation: Union[str, Constellation],
    ) -> bool:
        """
        Check if the product's name is valid for the given satellite


        .. code-block:: python

            >>> from eoreader.reader import Reader, Constellation
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> With IDs
            >>> Reader().valid_name(path, "S1")
            False
            >>> Reader().valid_name(path, "S2")
            True

            >>> # With names
            >>> Reader().valid_name(path, "Sentinel-1")
            False
            >>> Reader().valid_name(path, "Sentinel-2")
            True

            >>> # With Constellation
            >>> Reader().valid_name(path, Constellation.S1)
            False
            >>> Reader().valid_name(path, Constellation.S2)
            True

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            constellation (str): Constellation's name or ID

        Returns:
            bool: True if valid name

        """
        constellation = Constellation.convert_from(constellation)[0]
        regex = self._constellation_regex[constellation]
        return is_filename_valid(product_path, regex)

    def valid_mtd(
        self,
        product_path: Union[str, CloudPath, Path],
        constellation: Union[str, Constellation],
    ) -> bool:
        """
        Check if the product's mtd is in the product folder/archive

        .. code-block:: python

            >>> from eoreader.reader import Reader, Constellation
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> With IDs
            >>> Reader().valid_mtd(path, "S1")
            False
            >>> Reader().valid_mtd(path, "S2")
            True

            >>> # With names
            >>> Reader().valid_mtd(path, "Sentinel-1")
            False
            >>> Reader().valid_mtd(path, "Sentinel-2")
            True

            >>> # With Constellation
            >>> Reader().valid_mtd(path, Constellation.S1)
            False
            >>> Reader().valid_mtd(path, Constellation.S2)
            True

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            constellation (Union[str, Constellation]): Constellation's name or ID

        Returns:
            bool: True if valid name

        """
        # Convert constellation if needed
        constellation = Constellation.convert_from(constellation)[0]

        product_path = AnyPath(product_path)

        if not product_path.exists():
            return False

        # Here the list is a check of several files
        regex_list = self._mtd_regex[constellation]
        nested = self._mtd_nested[constellation]

        # False by default
        is_valid = [False for _ in regex_list]

        # Folder
        if product_path.is_dir():
            if nested < 0:
                prod_files = list(product_path.glob("**/*.*"))
            elif nested == 0:
                prod_files = list(
                    path for path in product_path.iterdir() if path.is_file()
                )
            else:
                nested_wildcard = "/".join(["*" for _ in range(nested)])
                prod_files = list(product_path.glob(f"*{nested_wildcard}/*.*"))

        # Archive
        else:
            try:
                prod_files = files.get_archived_file_list(product_path)
            except BadZipFile:
                raise BadZipFile(f"{product_path} is not a zip file")

        # Check
        for idx, regex in enumerate(regex_list):
            for prod_file in prod_files:
                if regex.match(str(prod_file)):
                    is_valid[idx] = True
                    break

        return all(is_valid)


def is_filename_valid(
    product_path: Union[str, CloudPath, Path], regex: Union[list, re.Pattern]
) -> bool:
    """
    Check if the filename corresponds to the given satellite regex.

    Checks also if a file inside the directory is correct.

    .. WARNING::
        Two level max for the moment

    Args:
        product_path (Union[str, CloudPath, Path]): Product path
        regex (Union[list, re.Pattern]): Regex or list of regex

    Returns:
        bool: True if the filename corresponds to the given satellite regex
    """
    product_path = AnyPath(product_path)
    product_file_name = files.get_filename(product_path)

    # Case folder is not enough to identify the products (ie. COSMO Skymed)
    # WARNING: Two level max for the moment
    is_valid = bool(regex[0].match(product_file_name))
    if is_valid and len(regex) > 1:
        is_valid = False  # Reset
        if product_path.is_dir():
            file_list = product_path.iterdir()
            for file in file_list:
                if regex[1].match(file.name):
                    is_valid = True
                    break
        else:
            try:
                file_list = files.get_archived_file_list(product_path)
                for file in file_list:
                    if regex[1].match(file):
                        is_valid = True
                        break
            except TypeError:
                LOGGER.debug(
                    f"The product {product_file_name} should be a folder or an archive (.tar or .zip)"
                )
            except BadZipFile:
                raise BadZipFile(f"{product_path} is not a zip file")

    return is_valid
