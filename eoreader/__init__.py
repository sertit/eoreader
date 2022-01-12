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
**EOReader** library
"""
from functools import wraps
from typing import Callable

try:
    from methodtools import lru_cache

    def cache(func: Callable) -> Callable:
        @lru_cache()
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    def cached_property(func: Callable) -> property:
        @lru_cache()
        @property
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


except ImportError:
    print(
        "WARNING!\n"
        "Without the methodtools library, caches are not limited to object instances!\n"
        "Caches may be shared between similar products!\n"
        "Please install methodtools through pip (pip install methodtools)"
    )
    from functools import lru_cache

    def cache(func: Callable) -> Callable:
        @lru_cache(maxsize=None)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    def cached_property(func: Callable) -> property:
        @property
        @lru_cache(maxsize=None)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


__all__ = ["bands", "products"]

from . import bands, products

__version__ = "0.10.1"
__title__ = "eoreader"
__description__ = (
    "Remote-sensing opensource python library reading optical and SAR sensors, "
    "loading and stacking bands, clouds, DEM and index in a sensor-agnostic way."
)
__author__ = "ICube-SERTIT"
__author_email__ = "dev-sertit@unistra.fr"
__url__ = "https://github.com/sertit/eoreader"
__license__ = "Apache 2.0"
__copyright__ = "Copyright 2022, SERTIT-ICube - France, https://sertit.unistra.fr/"
__documentation__ = "https://eoreader.readthedocs.io"
