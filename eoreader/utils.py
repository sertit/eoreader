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
import glob
import logging
import os
import platform

EOREADER_NAME = "eoreader"
DATETIME_FMT = "%Y%m%dT%H%M%S"
LOGGER = logging.getLogger(EOREADER_NAME)


def get_src_dir() -> str:
    """
    Get src directory.

    Returns:
        str: Root directory
    """
    return os.path.abspath(os.path.dirname(__file__))


def get_root_dir() -> str:
    """
    Get root directory.

    Returns:
        str: Root directory
    """
    return os.path.abspath(os.path.join(get_src_dir(), ".."))


def get_data_dir() -> str:
    """
    Get data directory.

    Returns:
        str: Data directory
    """
    data_dir = os.path.abspath(os.path.join(get_src_dir(), "data"))
    if not os.path.isdir(data_dir) or not os.listdir(data_dir):
        data_dir = None
        # Last resort try
        if platform.system() == "Linux":
            data_dirs = glob.glob(
                os.path.join("/usr", "local", "lib", "**", "eoreader", "data"),
                recursive=True,
            )
        else:
            data_dirs = glob.glob(
                os.path.join("**", "eoreader", "data"), recursive=True
            )

        # Look for non empty directories
        for ddir in data_dirs:
            if len(os.listdir(ddir)) > 0:
                data_dir = ddir
                break

        if not data_dir:
            raise FileNotFoundError("Impossible to find the data directory.")

    return data_dir
