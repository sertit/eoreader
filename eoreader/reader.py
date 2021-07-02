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
""" Product Factory, class creating products according to their names """

from __future__ import annotations

import importlib
import logging
import re
from enum import unique
from pathlib import Path
from typing import Union

from cloudpathlib import AnyPath, CloudPath

from eoreader.utils import EOREADER_NAME
from sertit import files, strings
from sertit.misc import ListEnum

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
    For products that have generic metadata files (ie. RS2 that as mtd named `product.xml`),
    it also checks the band name.
    """

    BOTH = "Both"
    """Check the metadata and the filename: Double check if you have a doubt."""


@unique
class Platform(ListEnum):
    """Platforms supported by EOReader"""

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

    PLA = "PlanetScope"
    """PlanetScope"""

    # RPD = "RapidEye"
    # """RapidEye"""
    #
    # SKY = "SkySat"
    # """SkySat"""

    CSK = "COSMO-SkyMed"
    """COSMO-SkyMed"""

    TSX = "TerraSAR-X"
    """TerraSAR-X"""

    RS2 = "RADARSAT-2"
    """RADARSAT-2"""

    PLD = "Pleiades"
    """Pléiades"""

    SPOT7 = "Spot-7"
    """SPOT-7"""

    SPOT6 = "Spot-6"
    """SPOT-6"""


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
    Platform.PLA: r"\d{8}_\d{6}_(\d{2}_|)\w{4}",
    Platform.CSK: [
        r".+",  # Need to check inside as the folder does not have any recognizable name
        r"CSKS[1-4]_(RAW|SCS|DGM|GEC|GTC)_[UB]_(HI|PP|WR|HR|S2)_"
        r"\w{2}_(HH|VV|VH|HV|CO|CH|CV)_[LR][AD]_[FS][NF]_\d{14}_\d{14}\.h5",
    ],
    Platform.TSX: r"T[SD]X1_SAR__(SSC|MGD|GEC|EEC)_[SR]E___[SH][MCLS]_[SDTQ]_[SD]RA_\d{8}T\d{6}_\d{8}T\d{6}",
    Platform.RS2: r"RS2_OK\d+_PK\d+_DK\d+_.{2,}_\d{8}_\d{6}(_(HH|VV|VH|HV)){1,4}_S(LC|GX|GF|CN|CW|CF|CS|SG|PG)",
    Platform.PLD: r"IMG_PHR1[AB]_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}",
    Platform.SPOT7: r"IMG_SPOT7_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
    Platform.SPOT6: r"IMG_SPOT6_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{3}_\w",
}

# Not used for now
MTD_REGEX = {
    Platform.S1: r".*s1[ab]-(iw|ew|sm|wv)\d*-(raw|slc|grd|ocn)-[hv]{2}-\d{8}t\d{6}-\d{8}t\d{6}-\d{6}-\w{6}-\d{3}\.xml",
    Platform.S2: [
        r"MTD_MSIL(1C|2A)\.xml",  # Too generic name, check also a band
        r"T\d{2}\w{3}_\d{8}T\d{6}_B\d{2}(_\d0m|).jp2",
    ],
    Platform.S2_THEIA: f"{PLATFORM_REGEX[Platform.S2_THEIA]}_MTD_ALL\.xml",
    Platform.S3: [
        r"xfdumanifest\.xml",  # Not the real metadata...
        r"(S\d|Oa\d{2})_radiance(_an|).nc",
    ],
    Platform.L8: f"{PLATFORM_REGEX[Platform.L8]}_MTL\.txt",
    Platform.L7: f"{PLATFORM_REGEX[Platform.L7]}_MTL\.txt",
    Platform.L5: f"{PLATFORM_REGEX[Platform.L5]}_MTL\.txt",
    Platform.L4: f"{PLATFORM_REGEX[Platform.L4]}_MTL\.txt",
    Platform.L3: f"{PLATFORM_REGEX[Platform.L3]}_MTL\.txt",
    Platform.L2: f"{PLATFORM_REGEX[Platform.L2]}_MTL\.txt",
    Platform.L1: f"{PLATFORM_REGEX[Platform.L1]}_MTL\.txt",
    Platform.PLA: r"\d{8}_\d{6}_(\d{2}_|)\w{4}_[13][AB]_.*metadata.*\.xml",
    Platform.CSK: f"{PLATFORM_REGEX[Platform.CSK][1]}\.xml",
    Platform.TSX: f"{PLATFORM_REGEX[Platform.TSX]}\.xml",
    Platform.RS2: [
        r"product\.xml",  # Too generic name, check also a band
        r"imagery_[HV]{2}\.tif",
    ],
    Platform.PLD: r"DIM_PHR1[AB]_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
    Platform.SPOT7: r"DIM_SPOT7_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
    Platform.SPOT6: r"DIM_SPOT6_(P|MS|PMS|MS-N|MS-X|PMS-N|PMS-X)_\d{15}_(SEN|PRJ|ORT|MOS)_.{10,}\.XML",
}


class Reader:
    """
    Factory class creating satellite products according to their names.

    It creates a singleton that you can call only on,e time per file.
    """

    def __init__(self):
        self._platform_regex = {}
        self._mtd_regex = {}

        # Register platforms
        for platform, regex in PLATFORM_REGEX.items():
            self._platform_regex[platform] = self._compile(regex, prefix="", suffix="")

        # Register metadata
        for platform, regex in MTD_REGEX.items():
            self._mtd_regex[platform] = self._compile(regex, prefix=".*", suffix="")

    @staticmethod
    def _compile(regex: Union[str, list], prefix="^", suffix="&") -> list:
        """
        Compile regex or list of regex

        Args:
            regex (Union[str, list]): Regex in `re` sense
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
    ) -> "Product":  # noqa: F821
        """
        Open the product.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> Reader().open(path)
            <eoreader.products.optical.s2_product.S2Product object at 0x000001984986FAC8>

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            archive_path (Union[str, CloudPath, Path]): Archive path
            output_path (Union[str, CloudPath, Path]): Output Path
            method (CheckMethod): Checking method used to recognize the products
            remove_tmp (bool): Remove temp files (such as clean or orthorectified bands...) when the product is deleted

        Returns:
            Product: Correct products

        """
        prod = None
        for platform in Platform.list_names():
            if method == CheckMethod.MTD:
                is_valid = self.valid_mtd(product_path, platform)
            elif method == CheckMethod.NAME:
                is_valid = self.valid_name(product_path, platform)
            else:
                is_valid = self.valid_name(product_path, platform) and self.valid_mtd(
                    product_path, platform
                )

            if is_valid:
                sat_class = platform.lower() + "_product"

                # Manage both optical and SAR
                try:
                    mod = importlib.import_module(f"eoreader.products.sar.{sat_class}")
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
                )
                break

        if not prod:
            LOGGER.warning(
                "There is no existing products in EOReader corresponding to %s",
                product_path,
            )

        return prod

    def valid_name(
        self, product_path: Union[str, CloudPath, Path], platform: Union[str, Platform]
    ) -> bool:
        """
        Check if the product's name is valid for the given satellite


        .. code-block:: python

            >>> from eoreader.reader import Reader, Platform
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

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            platform (str): Platform's name or ID

        Returns:
            bool: True if valid name

        """
        platform = Platform.convert_from(platform)[0]
        regex = self._platform_regex[platform]
        return self._is_filename_valid(product_path, regex)

    def valid_mtd(
        self, product_path: Union[str, CloudPath, Path], platform: Union[str, Platform]
    ) -> bool:
        """
        Check if the product's mtd is in the product folder/archive

        .. code-block:: python

            >>> from eoreader.reader import Reader, Platform
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

            >>> # With Platform
            >>> Reader().valid_mtd(path, Platform.S1)
            False
            >>> Reader().valid_mtd(path, Platform.S2)
            True

        Args:
            product_path (Union[str, CloudPath, Path]): Product path
            platform (Union[str, Platform]): Platform's name or ID

        Returns:
            bool: True if valid name

        """
        product_path = AnyPath(product_path)

        platform = Platform.convert_from(platform)[0]

        # Here the list is a check of several files
        regex_list = self._mtd_regex[platform]

        # False by default
        is_valid = [False for idx in regex_list]

        for idx, regex in enumerate(regex_list):
            # Folder
            if product_path.is_dir():
                for fle in product_path.glob("**/*.*"):
                    if regex.match(str(fle)):
                        is_valid[idx] = True
                        break

            # Archive
            else:
                if product_path.is_file():
                    fls = files.get_archived_file_list(product_path)
                    for fle in fls:
                        if regex.match(fle):
                            is_valid[idx] = True
                            break

        return all(is_valid)

    @staticmethod
    def _is_filename_valid(
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
                LOGGER.debug("The product should be a folder.")

        return is_valid
