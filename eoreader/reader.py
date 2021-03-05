""" Product Factory, class creating eoreader according to their names """

from __future__ import annotations
import importlib
import logging
import os
import re
from enum import unique
from typing import Union

from sertit import strings, files
from sertit.misc import ListEnum

from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Platform(ListEnum):
    """ Platforms supported by eoreader """
    S1 = "Sentinel-1"
    S2 = "Sentinel-2"
    S2_THEIA = "Sentinel-2 Theia"
    S3 = "Sentinel-3"
    L8 = "Landsat-8"
    L7 = "Landsat-7"
    L5 = "Landsat-5"
    L4 = "Landsat-4"
    L3 = "Landsat-3"
    L2 = "Landsat-2"
    L1 = "Landsat-1"
    CSK = "COSMO-SkyMed"
    TSX = "TerraSAR-X"
    RS2 = "RADARSAT-2"


PLATFORM_REGEX = {
    Platform.S1: r"S1[AB]_(IW|EW|SM|WV)_(RAW|SLC|GRD|OCN)[FHM_]_[0-2]S[SD][HV]_\d{8}T\d{6}_\d{8}T\d{6}_\d{6}_.{11}",
    Platform.S2: r"S2[AB]_MSIL(1C|2A)_\d{8}T\d{6}_N\d{4}_R\d{3}_T\d{2}\w{3}_\d{8}T\d{6}",
    Platform.S2_THEIA: r"SENTINEL2[AB]_\d{8}-\d{6}-\d{3}_L(2A|1C)_T\d{2}\w{3}_[CDH](_V\d-\d|)",
    Platform.S3: r"S3[AB]_[OS]L_[012]_\w{6}_\d{8}T\d{6}_\d{8}T\d{6}_\d{8}T\d{6}_\w{17}_\w{3}_[OFDR]_(NR|ST|NT)_\d{3}",
    Platform.L8: r"LC08_L1(GT|TP)_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Platform.L7: r"LE07_L1(GT|TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(RT|T1|T2)",
    Platform.L5: r"L[TM]05_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Platform.L4: r"L[TM]04_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2)",
    Platform.L3: r"LM03_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Platform.L2: r"LM02_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Platform.L1: r"LM01_L1(TP|GS)_\d{6}_\d{8}_\d{8}_\d{2}_T2",
    Platform.CSK: [r".+",
                   r"CSKS[1-4]_(RAW|SCS|DGM|GEC|GTC)_[UB]_(HI|PP|WR|HR|S2)_"
                   r"\w{2}_(HH|VV|VH|HV|CO|CH|CV)_[LR][AD]_[FS][NF]_\d{14}_\d{14}.h5"],
    Platform.TSX: r"T[SD]X1_SAR__(SSC|MGD|GEC|EEC)_[SR]E___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    # "tsx": "TX01_SAR_[SH][MCLS]_(SSC|MGD|GEC|EEC)_\d{8}T\d{6}_\d{8}T\d{6}_NSG_\d{6}_\d{4}",
    Platform.RS2: r"RS2_OK\d+_PK\d+_DK\d+_.{2,}_\d{8}_\d{6}(_(HH|VV|VH|HV)){1,4}_S(LC|GX|GF|CN|CW|CF|CS|SG|PG)"
}


class Reader:
    """ Factory class creating satellite products according to their names """

    def __init__(self):
        self._platform_regex = {}

        # Register satellites platforms
        for platform, regex in PLATFORM_REGEX.items():
            self.register_platforms(platform, regex)

    def register_platforms(self, platform: Platform, regex: Union[str, list]) -> None:
        """
        Register new platforms

        Args:
            platform (Platform): Platform
            regex (str): Regex of its file name
        """

        def compile_sat(regex_str: str):
            return re.compile(f"^{regex_str}$")  # Regex for the whole name: ^...$

        # Case folder is not enough to identify the products (ie. COSMO Skymed)
        if isinstance(regex, list):
            self._platform_regex[platform] = [compile_sat(regex) for regex in regex]
        else:
            self._platform_regex[platform] = compile_sat(regex)

    def open(self, product_path: str, archive_path: str = None) -> "Product":
        """
        Get the correct products

        Args:
            product_path (str): Product path
            archive_path (str): Archive path

        Returns:
            Product: Correct products

        """
        prod = None
        for platform, regex in self._platform_regex.items():
            if self.is_valid(product_path, regex):
                sat_class = platform.name.lower() + "_product"
                mod = importlib.import_module(f'eoreader.eoreader.{sat_class}')
                class_ = getattr(mod, strings.snake_to_camel_case(sat_class))
                prod = class_(product_path, archive_path)
                break

        if not prod:
            LOGGER.warning("There is no existing products in eoreader corresponding to %s", product_path)

        return prod

    def get_platform_name(self, product_path: str) -> str:
        """
        Get the correct platform short name (s1...)

        Args:
            product_path (str): Product path

        Returns:
            str: Product type

        """
        sat_name = ""
        for sat_prod, regex in self._platform_regex.items():
            if self.is_valid(product_path, regex):
                sat_name = sat_prod.name
                break

        if not sat_name:
            LOGGER.warning("Product not found for file %s", product_path)

        return sat_name

    def valid_name(self, product_path: str, satellite: str) -> bool:
        """
        Check if the products's name is valid for the given satellite

        Args:
            product_path (str): Product path
            satellite (str): Satellite's name

        Returns:
            bool: True if valid name

        """
        assert satellite in Platform.list_values()
        regex = self._platform_regex[Platform.from_value(satellite)]
        return self.is_valid(product_path, regex)

    @staticmethod
    def is_valid(product_path: str, regex: Union[list, re.Pattern]) -> bool:
        """
        Check if the filename corresponds to the given satellite regex
        Args:
            product_path (str): Product path
            regex (Union[list, re.Pattern]): Regex or list of regex

        Returns:
            bool: True if the filename corresponds to the given satellite regex
        """
        is_valid = False
        product_file_name = files.get_filename(product_path)

        # Case folder is not enough to identify the products (ie. COSMO Skymed)
        # Two level max for the moment
        if isinstance(regex, list):
            if regex[0].match(product_file_name) and os.path.isdir(product_path):
                file_list = os.listdir(product_path)
                for file in file_list:
                    if regex[1].match(file):
                        is_valid = True
                        break
        else:
            is_valid = bool(regex.match(product_file_name))

        return is_valid
