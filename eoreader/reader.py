""" Product Factory, class creating products according to their names """

from __future__ import annotations
import importlib
import logging
import os
import re
from enum import unique
from typing import Union

from sertit import strings, files
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidTypeError
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Platform(ListEnum):
    """ Platforms supported by EOReader """
    S1 = "Sentinel-1"
    """Sentinel-1"""

    S2 = "Sentinel-2"
    """Sentinel-2"""

    S2_THEIA = "Sentinel-2 Theia"
    """Sentinel-2 Theia"""

    S3 = "Sentinel-3"
    """Sentinel-3"""

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

    CSK = "COSMO-SkyMed"
    """COSMO-SkyMed"""

    TSX = "TerraSAR-X"
    """TerraSAR-X"""

    RS2 = "RADARSAT-2"
    """RADARSAT-2"""


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
"""Platfomr regex, mapping every platform to a regex allowing the reader to recognize them."""


class Reader:
    """
    Factory class creating satellite products according to their names.

    It creates a singleton that you can call only on,e time per file.
    """

    def __init__(self):
        self._platform_regex = {}

        # Register satellites platforms
        for platform, regex in PLATFORM_REGEX.items():
            self._register_platforms(platform, regex)

    def _register_platforms(self, platform: Platform, regex: Union[str, list]) -> None:
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

    def open(self,
             product_path: str,
             archive_path: str = None,
             output_path: str = None) -> "Product":
        """
        Open the product.

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> Reader().open(path)
        <eoreader.products.optical.s2_product.S2Product object at 0x000001984986FAC8>
        ```

        Args:
            product_path (str): Product path
            archive_path (str): Archive path
            output_path (str): Output Path

        Returns:
            Product: Correct products

        """
        prod = None
        for platform, regex in self._platform_regex.items():
            if self._is_valid(product_path, regex):
                sat_class = platform.name.lower() + "_product"

                # Manage both optical and SAR
                try:
                    mod = importlib.import_module(f'eoreader.products.sar.{sat_class}')
                except ModuleNotFoundError:
                    mod = importlib.import_module(f'eoreader.products.optical.{sat_class}')

                class_ = getattr(mod, strings.snake_to_camel_case(sat_class))
                prod = class_(product_path, archive_path, output_path)
                break

        if not prod:
            LOGGER.warning("There is no existing products in EOReader corresponding to %s", product_path)

        return prod

    def get_platform_id(self, product_path: str) -> str:
        """
        Get the correct platform ID (S1, S2, TSX...)

        ```python
        >>> from eoreader.reader import Reader
        >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
        >>> Reader().get_platform_name(path)
        'S2'
        ```

        Args:
            product_path (str): Product path

        Returns:
            str: Product type

        """
        sat_name = ""
        for sat_prod, regex in self._platform_regex.items():
            if self._is_valid(product_path, regex):
                sat_name = sat_prod.name
                break

        if not sat_name:
            LOGGER.warning("Product not found for file %s", product_path)

        return sat_name

    def valid_name(self, product_path: str, platform: Union[str, Platform]) -> bool:
        """
        Check if the product's name is valid for the given satellite

        ```python
        >>> from eoreader.reader import Reader
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

        >>> # With Platform
        >>> Reader().valid_name(path, Platform.S1)
        False
        >>> Reader().valid_name(path, Platform.S2)
        True
        ```

        Args:
            product_path (str): Product path
            platform (str): Platform's name or ID

        Returns:
            bool: True if valid name

        """
        platform = Platform.convert_from(platform)[0]
        regex = self._platform_regex[platform]
        return self._is_valid(product_path, regex)

    @staticmethod
    def _is_valid(product_path: str, regex: Union[list, re.Pattern]) -> bool:
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
