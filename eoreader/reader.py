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
"""Product Factory, class creating products according to their names"""

from __future__ import annotations

import importlib
import logging
import re
from enum import unique
from typing import Union
from zipfile import BadZipFile

import validators
from sertit import AnyPath, path, strings, types
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType

from eoreader import EOREADER_NAME, utils
from eoreader.exceptions import InvalidProductError

try:
    import pystac
    from pystac import Item

    PYSTAC_INSTALLED = True
except ModuleNotFoundError:
    from typing import Any as Item

    PYSTAC_INSTALLED = False

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
    """
    Sentinel-2, reprocessed by Theia.

    Considered as a new constellation as the product is completely different different from Sentinel-2.
    """

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

    RE = "RapidEye"
    """RapidEye"""

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

    VENUS = "Venus"
    """Venus"""

    VIS1 = "Vision-1"
    """Vision-1"""

    GS2 = "GEOSAT-2"
    """GEOSAT-2 (ex. DEIMOS-2)"""

    HLS = "HLS"
    """
    Harmonized Landsat-Sentinel

    Considered as a new constellation as the products are completely different from Sentinel-2 and Landsat.
    """

    QB02 = "QuickBird"
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

    WVLG = "WorldView Legion"
    """WorldView Legion"""

    RCM = "RADARSAT-Constellation Mission"
    """RADARSAT-Constellation Mission"""

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

    CAPELLA = "Capella"
    """Capella"""

    UMBRA = "Umbra"
    """Umbra"""

    # Under here, not real constellations: either CUSTOM, templates or different flavors from the same constellation
    CUSTOM = "CUSTOM"
    """Custom stack"""

    S1_RTC_ASF = "Sentinel-1 RTC ASF"
    """
    Sentinel-1 RTC processed by ASF: https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/

    Not a real constellation, only used for regex.
    """

    S1_RTC_MPC = "Sentinel-1 RTC MPC"
    """
    Sentinel-1 RTC processed by MPC: https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc

    Not a real constellation, only used for regex.
    """

    S2_E84 = "Sentinel-2 stored on AWS and processed by Element84"
    """
    Sentinel-2 stored on AWS and processed by Element84:
    - Element84: arn:aws:s3:::sentinel-cogs - https://registry.opendata.aws/sentinel-2-l2a-cogs

    Not a real constellation, only used for regex.
    """

    S2_MPC = "Sentinel-2 stored on Azure and processed by Microsoft Planetary Computer"
    """
    Sentinel-2 stored on Azure and processed by Microsoft Planetary Computer:
    https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a

    Not a real constellation, only used for regex.
    """

    S2_SIN = "Sentinel-2 stored on AWS and processed by Sinergise"
    """
    Sentinel-2 stored on AWS and processed by Sinergise:
    arn:aws:s3:::sentinel-s2-l1c and arn:aws:s3:::sentinel-s2-l2a - https://registry.opendata.aws/sentinel-2/

    Not a real constellation, only used for regex.
    """

    SPOT45 = "Spot-4/5"
    """SPOT-4/5 (not a real constellation, but used as a template for SPOT4/5 products)"""

    MAXAR = "Maxar"
    """Maxar (not a real constellation, but used as a template for every Maxar products)"""

    @classmethod
    def get_real_constellations(cls):
        """
        Get only constellations of existing satellite (discard CUSTOM, templates, flavors etc.)
        """
        not_real = [
            cls.S2_E84,
            cls.S2_MPC,
            cls.S2_SIN,
            cls.S1_RTC_ASF,
            cls.S1_RTC_MPC,
            cls.MAXAR,
            cls.SPOT45,
            cls.CUSTOM,
        ]
        return {const for const in cls.__members__.values() if const not in not_real}

    @classmethod
    def is_real_constellation(cls, const: Constellation):
        """
        Is the given constellation a real one?

        Args:
            const (Constellation): Constellation to check

        Returns:

        """
        return cls.convert_from(const)[0] in cls.get_real_constellations()


_MAXAR_REGEX = r"\d{12}_\d{2}_P\d{3}_(MUL|PAN|PSH|MOS)"

CONSTELLATION_REGEX = {
    Constellation.VENUS: r"VENUS-XS_\d{8}-\d{6}-\d{3}_L2A_[A-Z0-9_-]+",
    Constellation.S1: r"S1[ABCD]_(IW|EW|SM|WV|S\d)_(RAW|SLC|GRD|OCN)[FHM_]_[0-2]S[SD][HV]_\d{8}T\d{6}_\d{8}T\d{6}_\d{6}_.{11}(_COG|)",
    Constellation.S2: r"S2[ABCD]_MSIL(1C|2A)_\d{8}T\d{6}_N\d{4}_R\d{3}_T\d{2}\w{3}_\d{8}T\d{6}",
    # Element84 : S2A_31UDQ_20230714_0_L2A, Sinergise: 0 or 1...
    Constellation.S2_E84: r"S2[ABCD]_\d{2}\w{3}_\d{8}_\d_L(1C|2A)",
    Constellation.S2_THEIA: r"SENTINEL2[ABCD]_\d{8}-\d{6}-\d{3}_L(2A|1C)_T\d{2}\w{3}_[CDH](_V\d-\d|)",
    Constellation.S3_OLCI: r"S3[ABCD]_OL_[012]_\w{6}_\d{8}T\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_\w{17}_\w{3}_[OFDR]_(NR|ST|NT)_\d{3}",
    Constellation.S3_SLSTR: r"S3[ABCD]_SL_[012]_\w{6}_\d{8}T\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_\w{17}_\w{3}_[OFDR]_(NR|ST|NT)_\d{3}",
    Constellation.L9: r"L[OTC]09_(L1(GT|TP)|L2(SP|SR))_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L8: r"L[OTC]08_(L1(GT|TP)|L2(SP|SR))_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L7: r"LE07_(L1(GT|TP|GS)|L2(SP|SR))_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Constellation.L5: r"L[TM]05_(L1(TP|GS)|L2(SP|SR))_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Constellation.L4: r"L[TM]04_(L1(TP|GS)|L2(SP|SR))_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Constellation.L3: r"LM03_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.L2: r"LM02_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.L1: r"LM01_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Constellation.SKY: r"\d{8}_\d{6}_ssc\w{1,4}_\w{4,5}",
    Constellation.PLA: r"\d{8}_\d{6}_(\d{2}_|)\w{4}",
    Constellation.RE: r"(\d{7}_\d{4}-\d{2}-\d{2}_RE\d_3A_\d{6}|\d{4}-\d{2}-\d{2}T\d{6}_RE\d_1B_.+|RE_.+_RE\d_(1B|3A)_.+)",
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
    Constellation.TSX: r"TSX1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLST]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.TDX: r"TDX1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.PAZ: r"PAZ1_SAR__(SSC|MGD|GEC|EEC)_([SR]E|__)___[SH][MCLST]_[SD]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Constellation.RS2: r"RS2_(OK\d+_PK\d+_DK\d+_.{2,}_\d{8}_\d{6}|\d{8}_\d{6}_\d{4}_.{1,5})"
    r"(_(HH|VV|VH|HV)){1,4}_S(LC|GX|GF|CN|CW|CF|CS|SG|PG)(_\d{6}_\d{4}_\d{8}|)",
    Constellation.PLD: r"IMG_PHR1[AB]_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}",
    Constellation.PNEO: r"IMG_\d+_PNEO\d_(PMS-FS|MS-FS|PMS|MS|P)",
    Constellation.SPOT7: r"IMG_SPOT7_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
    Constellation.SPOT6: r"IMG_SPOT6_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
    Constellation.SPOT45: r"SPVIEW_.+",
    Constellation.SPOT4: r"SP04_HIR_(M_|I_|MI|X_|MX)___\d_\d{8}T\d{6}_\d{8}T\d{6}_.*",
    Constellation.SPOT5: r"SP05_HRG_(HM_|J__|T__|X__|TX__|HMX)__\d_\d{8}T\d{6}_\d{8}T\d{6}_.*",
    Constellation.VIS1: r"VIS1_(PAN|BUN|PSH|MS4)_.+_\d{2}-\d",
    Constellation.RCM: r"RCM\d_OK\d+_PK\d+_\d_.{4,}_\d{8}_\d{6}(_(HH|VV|VH|HV|RV|RH)){1,4}_(SLC|GRC|GRD|GCC|GCD)",
    Constellation.QB02: _MAXAR_REGEX,
    Constellation.GE01: _MAXAR_REGEX,
    Constellation.WV01: _MAXAR_REGEX,
    Constellation.WV02: _MAXAR_REGEX,
    Constellation.WV03: _MAXAR_REGEX,
    Constellation.WV04: _MAXAR_REGEX,
    Constellation.WVLG: _MAXAR_REGEX,
    Constellation.MAXAR: _MAXAR_REGEX,
    Constellation.ICEYE: r"((SM|SL|SC|SLEA)[HW]*_\d{5,}|ICEYE_X\d_(SM|SL|SC|SLEA)H*_\d{5,}_\d{8}T\d{6})",
    Constellation.SAOCOM: r".+EOL1[ABCD]SARSAO1[AB]\d+(-product|)",
    Constellation.CAPELLA: r"CAPELLA_C\d{2}_S[PMS]_(GEO|GEC|SLC|SICD|SIDD)_(HH|VV)_\d{14}_\d{14}",
    Constellation.UMBRA: r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_UMBRA-\d{2}",
    Constellation.SV1: [
        r"\d{13}_\d{2}",
        r"SV1-0[1-4]_\d{8}_L(1B|2A)\d{10}_\d{13}_\d{2}-(MUX|PSH)\.xml",
    ],
    Constellation.HLS: r"HLS\.[LS]30\.T\d{2}\w{3}\.\d{7}T\d{6}\.v2\.0",
    Constellation.GS2: r"DE2_(PM4|PSH|PS3|PS4|MS4|PAN)_L1[A-D]_\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_DE2_\d{5}_.{4}",
    Constellation.S2_SIN: [r"\d", r"B12\.jp2"],
    Constellation.S1_RTC_ASF: r"S1[ABCD]_(IW|EW|SM|WV|S\d)_\d{8}T\d{6}_[DS][VH][PRO]_RTC\d{2}_.*",
}

_MAXAR_MTD_REGEX = r"\d{2}\w{3}\d{8}-.*.TIL"

MTD_REGEX = {
    Constellation.VENUS: r"VENUS-XS_\d{8}-\d{6}-\d{3}_L2A_[A-Z0-9_-]+_MTD_ALL\.xml",
    # Constellation.VENUS: r"VENUS-XS_\d{8}-\d{6}-\d{3}_L2A_[A-Z0-9-]+",
    # Constellation.VENUS: rf"{CONSTELLATION_REGEX[Constellation.VENUS]}_MTD_ALL\.xml",
    Constellation.S1: {
        "nested": 1,
        # File that can be found at any level (product/**/file)
        "regex": r".*s1[abcd]-(iw|ew|sm|wv|s\d)\d*-(raw|slc|grd|ocn)-[hv]{2}-\d{8}t\d{6}-\d{8}t\d{6}-\d{6}-\w{6}-\d{3}(-cog|)\.xml",
    },
    Constellation.S2: {"nested": 2, "regex": r"MTD_TL.xml"},
    Constellation.S2_E84: rf"{CONSTELLATION_REGEX[Constellation.S2_E84]}\.json",
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
        "regex": r"(\d{8}_\d{6}_(\d{2}_|)\w{4}_[13][AB]|\d{7}_\d{7}_\d{4}-\d{2}-\d{2})_.*metadata.*\.xml",
    },
    Constellation.RE: {
        "nested": -1,  # File that can be found at any level (product/**/file)
        "regex": r"(\d{7}_\d{4}-\d{2}-\d{2}_RE\d_3A_\d{7}|\d{4}-\d{2}-\d{2}T\d{6}_RE\d_1B.+)(_.*metadata|).*\.xml",
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
    Constellation.PNEO: r"DIM_PNEO\d_(\w+_|)\d{15}_(PMS-FS|MS-FS|PMS|MS|P)_(SEN|PRJ|ORT|MOS)_.{8,}(-.{4,}-.{4,}-.{4,}-.{12,}|_._._._.)\.XML",
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
    Constellation.QB02: _MAXAR_MTD_REGEX,
    Constellation.GE01: _MAXAR_MTD_REGEX,
    Constellation.WV01: _MAXAR_MTD_REGEX,
    Constellation.WV02: _MAXAR_MTD_REGEX,
    Constellation.WV03: _MAXAR_MTD_REGEX,
    Constellation.WV04: _MAXAR_MTD_REGEX,
    Constellation.WVLG: _MAXAR_MTD_REGEX,
    Constellation.MAXAR: _MAXAR_MTD_REGEX,
    Constellation.ICEYE: r"ICEYE_(X\d{1,}_|)(SLC|GRD)_((SM|SL|SC)H*|SLEA)_\d{5,}_\d{8}T\d{6}\.xml",
    Constellation.SAOCOM: r"S1[AB]_OPER_SAR_EOSSP__CORE_L1[A-D]_OL(F|VF)_\d{8}T\d{6}.xemt",
    Constellation.CAPELLA: rf"{CONSTELLATION_REGEX[Constellation.CAPELLA]}.*\.json",
    Constellation.UMBRA: rf"{CONSTELLATION_REGEX[Constellation.UMBRA]}.*\.tif",
    Constellation.SV1: r"SV1-0[1-4]_\d{8}_L(1B|2A)\d{10}_\d{13}_\d{2}-(MUX|PSH)\.xml",
    Constellation.HLS: rf"{CONSTELLATION_REGEX[Constellation.HLS]}\.Fmask\.tif",
    Constellation.GS2: rf"{CONSTELLATION_REGEX[Constellation.GS2]}\.dim",
    Constellation.SPOT45: [
        r"METADATA\.DIM",  # Too generic name, check also a band
        r"IMAGERY\.TIF",
    ],
    Constellation.SPOT4: [
        r"METADATA\.DIM",  # Too generic name, check also a band
        r"IMAGERY\.TIF",
    ],
    Constellation.SPOT5: [
        r"METADATA\.DIM",  # Too generic name, check also a band
        r"IMAGERY\.TIF",
    ],
    Constellation.S2_SIN: {
        "nested": 0,  # File that can be found at child directory
        "regex": [
            r"metadata\.xml",  # Too generic name, check also a band
            r"B12\.jp2",
        ],
    },
    Constellation.S1_RTC_ASF: rf"{CONSTELLATION_REGEX[Constellation.S1_RTC_ASF]}\.kmz",
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

        # Case folder is not enough to identify the products (i.e. COSMO Skymed)
        if types.is_iterable(regex):
            comp = [_compile_(regex) for regex in regex]
        else:
            comp = [_compile_(regex)]

        return comp

    def open(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        method: CheckMethod = CheckMethod.MTD,
        remove_tmp: bool = False,
        custom: bool = False,
        constellation: Union[Constellation, str, list] = None,
        **kwargs,
    ) -> Product:  # noqa: F821
        """
        Open a product from:
        - On disk path
        - Cloud URI (such as s3://)
        - STAC Item URL

        Handled STAC Items are:

        - MPC:
            - S2 L2A COGS
            - Landsat L2 and L1
            - S1 RTC
        - E84:
            - S2 L2A COGS
            - S2 L1C
            - Landsat L2

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
                default pixel size: 10.0
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
            product_path (AnyPathStrType): Product path. URL to a STAC Item is accepted. Cloud URIs (such as s3://...) or classic paths also.
            archive_path (AnyPathStrType): Archive path
            output_path (AnyPathStrType): Output Path
            method (CheckMethod): Checking method used to recognize the products
            remove_tmp (bool): Remove temp files (such as clean or orthorectified bands...) when the product is deleted
            custom (bool): True if we want to use a custom stack
            constellation (Union[Constellation, str, list]): One or several constellations to help the Reader to choose more rapidly the correct Product
            **kwargs: Other arguments
        Returns:
            Product: EOReader's product
        """
        prod = None

        # If a URL is given, it must point to a URL translatable to a STAC Item
        if validators.url(product_path):
            if PYSTAC_INSTALLED:
                try:
                    product_path = Item.from_file(product_path)
                    is_stac = True
                except Exception as exc:
                    raise InvalidProductError(
                        f"Cannot convert your URL ({product_path}) to a STAC Item."
                    ) from exc
            else:
                raise ModuleNotFoundError(
                    "You should install 'pystac' to use STAC Products."
                )
        # Check path (first check URL as they are also strings)
        elif path.is_path(product_path):
            is_stac = False
        else:
            # Check STAC Item
            if PYSTAC_INSTALLED:
                is_stac = isinstance(product_path, pystac.Item)
            else:
                is_stac = False

        if is_stac:
            prod = self._open_stac_item(product_path, output_path, remove_tmp, **kwargs)
        else:
            # If not an Item, it should be a path to somewhere
            prod = self._open_path(
                product_path,
                archive_path,
                output_path,
                method,
                remove_tmp,
                custom,
                constellation,
                **kwargs,
            )

        if not prod:
            LOGGER.warning(
                f"There is no existing products in EOReader corresponding to {product_path}."
            )
            LOGGER.info(
                "Your given path may not be a satellite image. If it is, maybe the product isn't handled by EOReader. "
                "If you are sure this product is handled, it is either corrupted or you may need to go deeper in the filetree to find the correct path to give."
            )
            LOGGER.debug(
                "Please look at what folder you should give to EOReader by accessing the documentation: "
                "https://eoreader.readthedocs.io/latest/main_features.html#recognized-paths"
            )
        return prod

    def _open_stac_item(
        self, item: Item, output_path: AnyPathStrType, remove_tmp: bool, **kwargs
    ):
        """
        Open a STAC Item in EOReader.

        Current STAC handled products: https://github.com/sertit/eoreader/issues/118

        - MPC:
            - S2 L2A COGS
            - Landsat L2 and L1
            - S1 RTC
        - E84:
            - S2 L2A COGS
            - S2 L1C
            - Landsat L2

        Args:
            item (Item): Stac Item
            output_path (AnyPathStrType): Output Path
            remove_tmp (bool): Remove temp files (such as clean or orthorectified bands...) when the product is deleted
            **kwargs: Other arguments

        Returns:
            Product: Product from the STAC Item
        """
        is_mpc = "planetarycomputer" in item.self_href
        is_e84 = "earth-search.aws.element84.com" in item.self_href

        if "rtc" in item.collection_id:
            const = Constellation.S1_RTC_MPC
        else:
            try:
                const = Constellation.from_value(
                    item.properties["constellation"].capitalize().replace(" ", "-")
                )
            except Exception:
                try:
                    const = Constellation.from_value(
                        item.common_metadata.platform.capitalize().replace(" ", "-")
                    )
                except Exception:
                    const = None
                    for const in CONSTELLATION_REGEX:
                        is_valid = self.valid_name(item.id, const)
                        if is_valid:
                            break

        if is_e84 and const == Constellation.S2:
            const = Constellation.S2_E84
        elif is_mpc and const == Constellation.S2:
            const = Constellation.S2_MPC

        if const is not None:
            prod = create_stac_product(
                item=item,
                output_path=output_path,
                remove_tmp=remove_tmp,
                constellation=const,
                is_e84=is_e84,
                is_mpc=is_mpc,
            )
        else:
            prod = None

        return prod

    def _open_path(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        method: CheckMethod = CheckMethod.MTD,
        remove_tmp: bool = False,
        custom: bool = False,
        constellation: Union[Constellation, str, list] = None,
        **kwargs,
    ):
        """
        Open a path or a cloud URI as an EOReader's product

        Args:
            product_path (AnyPathStrType): Product path. URL to a STAC Item is accepted. Cloud URIs (such as s3://...) or classic paths also.
            archive_path (AnyPathStrType): Archive path
            output_path (AnyPathStrType): Output Path
            method (CheckMethod): Checking method used to recognize the products
            remove_tmp (bool): Remove temp files (such as clean or orthorectified bands...) when the product is deleted
            custom (bool): True if we want to use a custom stack
            constellation (Union[Constellation, str, list]): One or several constellations to help the Reader to choose more rapidly the correct Product
            **kwargs: Other arguments
        Returns:
            Product: EOReader's product
        """

        product_path = AnyPath(product_path)

        if not product_path.exists():
            raise FileNotFoundError(f"Non existing product: {product_path}")

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
                # Manage other products which have the same constellation in them
                if constellation == Constellation.S2:
                    constellation = [
                        Constellation.S2,
                        Constellation.S2_SIN,
                        Constellation.S2_E84,
                        Constellation.S2_MPC,
                    ]
                elif constellation == Constellation.S1:
                    constellation = [
                        Constellation.S1,
                        Constellation.S1_RTC_ASF,
                        Constellation.S1_RTC_MPC,
                    ]

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
                    prod = create_product(
                        product_path=product_path,
                        archive_path=archive_path,
                        output_path=output_path,
                        remove_tmp=remove_tmp,
                        constellation=const,
                        **kwargs,
                    )
                    break

        return prod

    def valid_name(
        self,
        product_path: AnyPathStrType,
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
            product_path (AnyPathStrType): Product path
            constellation (str): Constellation's name or ID

        Returns:
            bool: True if valid name

        """
        constellation = Constellation.convert_from(constellation)[0]
        regex = self._constellation_regex[constellation]
        return is_filename_valid(product_path, regex)

    def valid_mtd(
        self,
        product_path: AnyPathStrType,
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
            product_path (AnyPathStrType): Product path
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
                    prod_path
                    for prod_path in product_path.iterdir()
                    if prod_path.is_file()
                )
            else:
                nested_wildcard = "/".join(["*" for _ in range(nested)])
                prod_files = list(product_path.glob(f"{nested_wildcard}/*.*"))

        # Archive
        else:
            try:
                prod_files = utils.get_archived_file_list(product_path)
            except BadZipFile as exc:
                raise BadZipFile(f"{product_path} is not a zip file") from exc

        # Check
        for idx, regex in enumerate(regex_list):
            for prod_file in prod_files:
                if regex.match(str(prod_file)):
                    is_valid[idx] = True
                    break

        return all(is_valid)


def is_filename_valid(
    product_path: AnyPathStrType, regex: Union[list, re.Pattern]
) -> bool:
    """
    Check if the filename corresponds to the given satellite regex.

    Checks also if a file inside the directory is correct.

    .. WARNING::
        Two levels maximum for the moment

    Args:
        product_path (AnyPathStrType): Product path
        regex (Union[list, re.Pattern]): Regex or list of regex

    Returns:
        bool: True if the filename corresponds to the given satellite regex
    """
    product_path = AnyPath(product_path)
    # Handle HLS folders...
    if product_path.is_dir() and product_path.suffix in [".0"]:
        product_file_name = product_path.name
    else:
        product_file_name = path.get_filename(product_path)

    # Case folder is not enough to identify the products (i.e. COSMO Skymed)
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
                file_list = utils.get_archived_file_list(product_path)
                for file in file_list:
                    if regex[1].match(file):
                        is_valid = True
                        break
            except TypeError:
                LOGGER.debug(
                    f"The product {product_file_name} should be a folder or an archive (.tar or .zip)"
                )
            except BadZipFile as exc:
                raise BadZipFile(f"{product_path} is not a zip file") from exc

            except FileNotFoundError:
                pass

    return is_valid


def create_product(
    product_path: AnyPathStrType,
    archive_path: AnyPathStrType,
    output_path: AnyPathStrType,
    remove_tmp: bool,
    constellation: Constellation,
    **kwargs,
):
    """
    Create Product

    Args:
        product_path (AnyPathStrType): Product path
        archive_path (AnyPathStrType): Archive path
        output_path (AnyPathStrType): Output path
        remove_tmp (bool): Remove tmp files
        constellation (Constellation): COnstellation
        **kwargs: Other arguments

    Returns:
        Product: EOReader product
    """
    sat_class = constellation.name.lower() + "_product"

    # Channel correctly the constellations to their generic files (just in case)
    # Maxar-like constellations
    if constellation in [
        Constellation.QB02,
        Constellation.GE01,
        Constellation.WV01,
        Constellation.WV02,
        Constellation.WV03,
        Constellation.WV04,
        Constellation.WVLG,
    ]:
        sat_class = "maxar_product"
        constellation = None  # All product names are the same, so assess it with MTD
    # Lansat constellations
    elif constellation in [
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
    elif constellation in [Constellation.SPOT6, Constellation.SPOT7]:
        sat_class = "spot67_product"
    # SPOT-4/5 constellations
    elif constellation in [Constellation.SPOT4, Constellation.SPOT5]:
        sat_class = "spot45_product"
    elif constellation in [Constellation.S2_SIN]:
        sat_class = "s2_product"
        kwargs["is_sinergise"] = True

    # Manage both optical and SAR
    try:
        mod = importlib.import_module(f"eoreader.products.sar.{sat_class}")
    except ModuleNotFoundError:
        mod = importlib.import_module(f"eoreader.products.optical.{sat_class}")

    # Get class
    class_ = getattr(mod, strings.snake_to_camel_case(sat_class))

    # Create product
    prod = class_(
        product_path=product_path,
        archive_path=archive_path,
        output_path=output_path,
        remove_tmp=remove_tmp,
        **kwargs,
    )
    return prod


def create_stac_product(
    item: Item,
    output_path: AnyPathStrType,
    remove_tmp: bool,
    constellation: Constellation,
    **kwargs,
):
    """
    Create STAC Product

    Args:
        item (Item): Product path
        output_path (AnyPathStrType): Output path
        remove_tmp (bool): Remove tmp files
        constellation (Constellation): COnstellation
        **kwargs: Other arguments

    Returns:
        Product: EOReader product
    """
    if constellation in [
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
    else:
        sat_class = constellation.name.lower() + "_product"

    # Manage both optical and SAR
    try:
        mod = importlib.import_module(f"eoreader.products.sar.{sat_class}")
    except ModuleNotFoundError:
        mod = importlib.import_module(f"eoreader.products.optical.{sat_class}")

    # Get class
    if kwargs.get("is_mpc", False) and "mpc" not in sat_class:
        replacement = "MpcStacProduct"
    else:
        replacement = "StacProduct"

    class_name = strings.snake_to_camel_case(sat_class).replace("Product", replacement)
    class_ = getattr(mod, class_name)

    # Create product
    prod = class_(
        item=item,
        remove_tmp=remove_tmp,
        **kwargs,
    )
    return prod
