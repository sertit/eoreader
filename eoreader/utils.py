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
""" Utils: mostly getting directories relative to the project """
import logging
import os
import platform
from pathlib import Path
from typing import Union

from cloudpathlib import AnyPath, CloudPath

EOREADER_NAME = "eoreader"
DATETIME_FMT = "%Y%m%dT%H%M%S"
LOGGER = logging.getLogger(EOREADER_NAME)


def get_src_dir() -> Union[CloudPath, Path]:
    """
    Get src directory.

    Returns:
        str: Root directory
    """
    return AnyPath(__file__).parent


def get_root_dir() -> Union[CloudPath, Path]:
    """
    Get root directory.

    Returns:
        str: Root directory
    """
    return get_src_dir().parent


def get_data_dir() -> Union[CloudPath, Path]:
    """
    Get data directory.

    Returns:
        str: Data directory
    """
    data_dir = get_src_dir().joinpath("data")
    if not data_dir.is_dir() or not list(data_dir.iterdir()):
        data_dir = None
        # Last resort try
        if platform.system() == "Linux":
            data_dirs = AnyPath("/usr", "local", "lib").glob("**/eoreader/data")
        else:
            data_dirs = AnyPath("/").glob("**/eoreader/data")

        # Look for non empty directories
        for ddir in data_dirs:
            if len(os.listdir(ddir)) > 0:
                data_dir = ddir
                break

        if not data_dir:
            raise FileNotFoundError("Impossible to find the data directory.")

    return data_dir
